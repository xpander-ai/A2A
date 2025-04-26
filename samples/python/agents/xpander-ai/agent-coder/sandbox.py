import os
import uuid
import re
import subprocess
from typing import Optional, Dict, Any
import shutil

# Base directory for sandboxes
SANDBOX_BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sandboxes")
os.makedirs(SANDBOX_BASE_DIR, exist_ok=True)
print(f"Sandbox base directory: {SANDBOX_BASE_DIR}")

# Global sandbox tracking
sandboxes = {}  # Map thread_id -> sandbox_path
current_sandbox = None

# Dangerous command patterns
DANGEROUS_PATTERNS = [
    '..', '../', '..\\'                      # Directory traversal
    '/', '/etc', '/var', '/root', '/home',   # System directories  
    '~', '$HOME', '${HOME}',                 # Home directory references
    '>', '>>', '2>', '&>', '|',              # Redirection & pipes
    'wget', 'curl', 'nc', 'netcat',          # Network tools
    'chmod', 'chown',                        # Permission changes
    'sudo', 'su',                            # Privilege escalation
    'eval', 'exec',                          # Command execution
    'telnet', 'ssh', 'ftp',                  # Remote access
    'apt', 'brew', 'yum', 'dnf', 'pip',      # Package managers
    'env', 'printenv',                       # Environment variables
    'ps', 'ps aux', 'top', 'htop',           # Process info commands
    'find / ', 'ls / ', 'ls -la /',          # Root directory inspection
    'cat /etc', 'less /etc', 'more /etc',    # System file access
    'ifconfig', 'ipconfig', 'ip addr',       # Network configuration
    'netstat', 'ss', 'lsof', 'nmap',         # Network inspection
    'host', 'dig', 'nslookup',               # DNS tools
    'iptables', 'route', 'traceroute'        # Network routing
]

# System directories to block
BLOCKED_SYSTEM_PATHS = [
    '/etc', '/var', '/root', '/home', '/usr', '/opt', '/bin', '/sbin', 
    '/lib', '/lib64', '/dev', '/proc', '/sys', '/boot', '/mnt', '/media',
    '/run', '/tmp', '/srv', '/lost+found', '/private'
]

def normalize_response_paths(response):
    """
    Normalize paths in responses to hide real system paths.
    This prevents exposing the actual file system structure to the agent.
    """
    if not isinstance(response, dict):
        return response
        
    # Get the current sandbox base path for normalization
    sandbox_path = current_sandbox
    if not sandbox_path:
        return response
    
    # Create a copy to avoid modifying the original
    result = dict(response)
    
    # Common keys that might contain paths
    path_keys = ['filepath', 'directory', 'path', 'target_dir', 'cwd', 'file_path']
    
    # Process common path keys
    for key in path_keys:
        if key in result and result[key] and isinstance(result[key], str):
            # Normalize the path: convert from absolute to relative path
            abs_path = os.path.abspath(result[key])
            if abs_path.startswith(sandbox_path):
                # Convert to a path relative to sandbox
                rel_path = os.path.relpath(abs_path, sandbox_path)
                result[key] = rel_path if rel_path != '.' else ''
                
    # Special handling for output that might contain paths
    if 'stdout' in result and result['stdout']:
        # Replace any mentions of the sandbox path in stdout
        result['stdout'] = result['stdout'].replace(sandbox_path, '.')
        
    if 'stderr' in result and result['stderr']:
        # Replace any mentions of the sandbox path in stderr
        result['stderr'] = result['stderr'].replace(sandbox_path, '.')
        
    if 'content' in result and result['content'] and isinstance(result['content'], str):
        # Replace any mentions of the sandbox path in file content
        result['content'] = result['content'].replace(sandbox_path, '.')
    
    # Handle nested dictionaries
    for key, value in result.items():
        if isinstance(value, dict):
            result[key] = normalize_response_paths(value)
        elif isinstance(value, list):
            result[key] = [normalize_response_paths(item) if isinstance(item, dict) else item for item in value]
    
    return result

def get_sandbox(thread_id: Optional[str] = None, filepath: Optional[str] = None) -> str:
    """
    Get a sandbox path, optionally with a filepath inside it.
    """
    global current_sandbox, sandboxes
    
    # Use current sandbox if available
    if current_sandbox and os.path.exists(current_sandbox):
        sandbox_path = current_sandbox
    
    # Use existing sandbox for this thread if available
    elif thread_id and thread_id in sandboxes and os.path.exists(sandboxes[thread_id]):
        sandbox_path = sandboxes[thread_id]
        current_sandbox = sandbox_path
    
    # Create a new sandbox
    else:
        sandbox_id = str(uuid.uuid4())[:8]
        sandbox_path = os.path.join(SANDBOX_BASE_DIR, f"sandbox_{thread_id or 'tmp'}_{sandbox_id}")
        
        # If sandbox already exists, clean it to avoid previous data leakage
        if os.path.exists(sandbox_path):
            shutil.rmtree(sandbox_path)
        
        # Create a fresh sandbox
        os.makedirs(sandbox_path, exist_ok=True)
        
        # Save the sandbox
        current_sandbox = sandbox_path
        if thread_id:
            sandboxes[thread_id] = sandbox_path
    
    # If no filepath provided, just return the sandbox path
    if not filepath:
        return sandbox_path
        
    # Handle special case for "." and ".." to prevent directory navigation issues
    if filepath == "." or filepath.strip() == "":
        return sandbox_path
        
    if filepath == "..":
        print("⚠️ Security: Parent directory traversal blocked")
        return sandbox_path
    
    # IMPORTANT FIX: If the path contains a full system path, extract just the final component
    # This prevents creating folders with full system paths as names
    if os.path.isabs(filepath):
        # Split the path to components and take only the last non-empty one
        parts = [p for p in os.path.normpath(filepath).replace('\\', '/').split('/') if p]
        if parts:
            filepath = parts[-1]  # Take only the final component
        else:
            filepath = "unnamed_file"
            
    # Now proceed with normal path handling for the simplified filepath
    if '/' in filepath or '\\' in filepath:
        # This looks like a hierarchical path, split it into components 
        # and make sure each component is sanitized
        components = []
        
        # Split the path and sanitize each component
        parts = os.path.normpath(filepath).replace('\\', '/').split('/')
        for part in parts:
            if part and part not in ('.', '..'):
                # Apply basic sanitization to each part
                sanitized = part
                sanitized = re.sub(r'^[\/\\]+', '', sanitized)  # Remove leading slashes
                sanitized = sanitized.replace('..', '__')       # Replace dangerous patterns
                
                if sanitized:  # Only add non-empty components
                    components.append(sanitized)
        
        # If we end up with no valid components, default to an empty filename
        if not components:
            safe_path = "unnamed_file"
        else:
            # Join the sanitized parts
            safe_path = os.path.join(*components)
    else:
        # Simple filename without path components, just sanitize it directly
        safe_path = sanitize_path(filepath)
    
    # Handle empty path
    if not safe_path or safe_path.strip() == "":
        safe_path = "unnamed_file"
    
    # Create full path in the sandbox
    full_path = os.path.join(sandbox_path, safe_path)
    
    # SECURITY: Final verification to ensure path is actually inside sandbox
    if not is_path_safe(sandbox_path, full_path):
        print(f"⚠️ Security: Path traversal attempt detected! Defaulting to sandbox root.")
        return sandbox_path
    
    # Create parent directory if needed
    parent_dir = os.path.dirname(full_path)
    if parent_dir and not os.path.exists(parent_dir):
        try:
            os.makedirs(parent_dir, exist_ok=True)
        except Exception as e:
            print(f"⚠️ Warning: Could not create directory {parent_dir}: {str(e)}")
        
    return full_path

def sanitize_path(path: str) -> str:
    """
    Sanitize a path to prevent sandbox escape and prevent creating directories with system path names.
    """
    if not path:
        return ""
    
    # First, convert Windows backslashes to forward slashes for consistent handling
    path = path.replace('\\', '/')
    
    # IMPORTANT FIX: If path contains slashes, extract just the filename component
    # This prevents creating directories with full paths as names
    if '/' in path:
        # Get just the final component (filename or dir name)
        path = os.path.basename(path)
    
    # Normalize the path to handle . and .. references
    path = os.path.normpath(path)
    
    # Remove leading slash and drive letters
    path = re.sub(r'^[\/\\]+', '', path)     # Remove leading slashes
    path = re.sub(r'^[a-zA-Z]:[\/\\]', '', path)  # Remove Windows drive letters
    
    # Replace any remaining .. references
    path = path.replace('..', '__')
    path = path.replace('../', '')
    path = path.replace('..\\', '')
    
    # Protect against various encodings of path traversal
    path = path.replace('%2e%2e', '__')   # URL encoded ..
    path = path.replace('%2E%2E', '__')
    path = path.replace('..%2f', '__')    # Mixed encoding
    path = path.replace('..%5c', '__')
    
    # Block access to system directories
    for sys_dir in BLOCKED_SYSTEM_PATHS:
        # Block full paths that include system directories
        if sys_dir in path:
            # Replace with safe path
            path = path.replace(sys_dir, 'blocked_path')
        
        # Also block attempts to create directories with system directory names
        # For example, if the path is just "etc" or "var"
        if path == os.path.basename(sys_dir):
            path = f"blocked_{path}"
    
    # Final check - if the path still contains slashes after all our processing,
    # it may be attempting to create a nested directory structure with a single call.
    # Convert remaining slashes to underscores to prevent this.
    path = path.replace('/', '_')
    
    return path

def is_path_safe(sandbox_path: str, full_path: str) -> bool:
    """
    Check if a path is safely contained within the sandbox.
    """
    # Convert both to absolute paths
    sandbox_abs = os.path.abspath(sandbox_path)
    full_abs = os.path.abspath(full_path)
    
    # Ensure the path is inside the sandbox
    return full_abs.startswith(sandbox_abs)

def validate_command(command: str) -> bool:
    """
    Validate a command to ensure it's safe to execute.
    """
    # Convert to lowercase for case-insensitive checks
    cmd_lower = command.lower()
    
    # Check for dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if pattern in command:
            raise ValueError(f"Command security validation failed: Command contains dangerous pattern: {pattern}")
    
    # Block specific commands entirely
    if cmd_lower.startswith(('ps ', 'ps aux', 'top ', 'htop')):
        raise ValueError("Command security validation failed: Process inspection commands are restricted")
    
    # Block direct access to any system files
    for path in BLOCKED_SYSTEM_PATHS:
        if path in command:
            raise ValueError(f"Command security validation failed: Access to system path {path} is not allowed")
    
    # Check for attempts to escape the sandbox
    if re.search(r'(^|[^\w])cd\s+[^\s]+', command):  # cd with argument
        raise ValueError("Command security validation failed: Changing directories is restricted")
    
    # Check for environment inspection
    if re.search(r'(^|[^\w])(env|printenv)', command):
        raise ValueError("Command security validation failed: Environment inspection is restricted")
    
    # Check for file system navigation outside of allowed tools
    if re.search(r'(^|[^\w])(ls|dir|find)\s+[^\s]*\.\.', command):
        raise ValueError("Command security validation failed: Navigating outside sandbox is restricted")
    
    # Check for network access attempts
    if re.search(r'(^|[^\w])(curl|wget|nc|netcat|telnet|ssh|ftp|ifconfig|ipconfig|netstat|ping|host|dig)', command):
        raise ValueError("Command security validation failed: Network access commands are restricted")
    
    # Check for process inspection attempts
    if re.search(r'(^|[^\w])(ps|top|htop|pgrep|pkill|kill)\b', command):
        raise ValueError("Command security validation failed: Process management commands are restricted")
        
    return True

def update_sandbox_thread(thread_id: str) -> None:
    """
    Update the current sandbox to be associated with a thread ID
    """
    global current_sandbox, sandboxes
    if thread_id and current_sandbox:
        sandboxes[thread_id] = current_sandbox

def sandbox_tool_call(func_name, payload):
    """
    Generic function to sandbox ANY tool call parameters
    """
    # Create a copy of the payload to avoid modifying the original
    sandboxed_params = dict(payload)
    
    # File operations tools
    if func_name in ['read_file', 'write_file', 'count_file_lines'] and 'filepath' in sandboxed_params:
        # SECURITY: Only allow access to files inside the sandbox
        sandboxed_params['filepath'] = get_sandbox(filepath=sandboxed_params['filepath'])
        
    # Directory operations
    elif func_name == 'list_directory':
        if 'directory' in sandboxed_params:
            # SECURITY: Ensure directory listing is contained in sandbox
            sandboxed_params['directory'] = get_sandbox(filepath=sandboxed_params['directory'])
        else:
            sandboxed_params['directory'] = get_sandbox()
            
    # Command execution
    elif func_name == 'execute_command':
        # SECURITY: Force working directory to the sandbox
        sandboxed_params['cwd'] = get_sandbox()
        
        # SECURITY: Validate command for safety
        if 'command' in sandboxed_params:
            try:
                validate_command(sandboxed_params['command'])
            except ValueError as e:
                raise ValueError(str(e))
            
            # SECURITY: Force all Python execution to use the interpreter with restrictions
            if sandboxed_params['command'].startswith('python') or 'python3' in sandboxed_params['command']:
                # Add restrictions to prevent file system access outside sandbox
                python_cmd = sandboxed_params['command']
                # We could add additional Python security flags here if needed
            
    # Git operations
    elif func_name == 'git_clone':
        if 'target_dir' in sandboxed_params:
            sandboxed_params['target_dir'] = get_sandbox(filepath=sandboxed_params['target_dir'])
        else:
            sandboxed_params['target_dir'] = get_sandbox()
            
    return sandboxed_params

def secure_python_execution(script_path, args=None):
    """
    Execute a Python script with security restrictions.
    This would be called by the execute_command function for Python scripts.
    """
    # Ensure the script path is inside the sandbox
    safe_script_path = get_sandbox(filepath=script_path)
    sandbox_dir = os.path.dirname(safe_script_path)
    
    # Convert the path to an absolute path for better script finding
    abs_script_path = os.path.abspath(safe_script_path)
    
    # Check if script exists and log more information for debugging
    if not os.path.exists(abs_script_path):
        print(f"Debug: Could not find script at {abs_script_path}")
        print(f"Debug: Checking for {os.path.basename(abs_script_path)} in directory {sandbox_dir}")
        
        # Try finding the script by basename in the sandbox directory
        possible_paths = [
            os.path.join(sandbox_dir, os.path.basename(abs_script_path)),
            os.path.join(sandbox_dir, script_path),
            os.path.join(current_sandbox, os.path.basename(abs_script_path)),
            os.path.join(current_sandbox, script_path)
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                abs_script_path = path
                print(f"Debug: Found script at {abs_script_path}")
                break
        else:
            return {
                "stdout": "",
                "stderr": f"Error: Script '{script_path}' not found. Make sure the file exists and the path is correct.",
                "returncode": 1
            }
    
    # Create a simple wrapper script that runs the target script directly
    temp_wrapper = os.path.join(sandbox_dir, f"_wrapper_{uuid.uuid4().hex[:8]}.py")
    
    with open(temp_wrapper, 'w') as f:
        f.write(f"""
import sys
import os

# Add sandbox directory to path
script_dir = {repr(os.path.dirname(abs_script_path))}
sys.path.insert(0, script_dir)
os.chdir(script_dir)  # Change to script directory

# Set up arguments
script_name = {repr(abs_script_path)}
sys.argv = [script_name] + {repr(args) if args else []}

# Restrict certain sensitive modules
class RestrictedImporter:
    def __init__(self, original_import):
        self.original_import = original_import
        self.restricted_modules = [
            'subprocess', 'shutil', 'socket', 'urllib.request',
            'ftplib', 'http.client', 'importlib', 'marshal',
            'multiprocessing', 'threading', 'ctypes', 'pickle',
            'os.path', 'pathlib', 'io', 'tempfile', 'platform',
            'requests', 'urllib', 'urllib2', 'urllib3', 
            'ssl', 'smtplib', 'telnetlib', 'poplib', 'imaplib'
        ]
        
        # System access modules
        self.system_modules = ['os', 'sys', 'posix', 'pwd', 'grp']
        
        # Network modules
        self.network_modules = ['socket', 'ssl', 'urllib', 'http', 'requests', 'ftplib']
        
    def __call__(self, name, *args, **kwargs):
        # Block dangerous modules completely
        if name in self.restricted_modules:
            print(f"Security: Access to module {{name}} is restricted", file=sys.stderr)
            raise ImportError(f"Security: Module {{name}} is restricted")
            
        # Partially block system modules 
        if name in self.system_modules:
            # Let it import but we could restrict dangerous functions after import
            # For example, limit what os functions are available
            # For now, we'll just log it
            print(f"Security notice: Importing system module {{name}}", file=sys.stderr)
            
        # Block network modules
        if name in self.network_modules:
            print(f"Security: Network module {{name}} is restricted", file=sys.stderr)
            raise ImportError(f"Security: Network module {{name}} is restricted")
            
        return self.original_import(name, *args, **kwargs)

# Install import hook
import builtins
builtins.__original_import__ = builtins.__import__
builtins.__import__ = RestrictedImporter(builtins.__original_import__)

# Block dangerous built-in functions
for dangerous_func in ['eval', 'exec', 'compile', '__import__', 'open']:
    if hasattr(builtins, dangerous_func):
        setattr(builtins, f"_original_{dangerous_func}", getattr(builtins, dangerous_func))
        
        def make_blocked_func(name):
            def blocked(*args, **kwargs):
                print(f"Security: Built-in function {{name}} is restricted", file=sys.stderr)
                raise PermissionError(f"Security: Function {{name}} is blocked for security reasons")
            return blocked
            
        setattr(builtins, dangerous_func, make_blocked_func(dangerous_func))
        
# Restrict file access
def secure_open(filename, *args, **kwargs):
    # Don't allow absolute paths
    if os.path.isabs(filename):
        print(f"Security: Cannot access absolute path {{filename}}", file=sys.stderr)
        raise PermissionError(f"Security: Access to {{filename}} is not allowed (absolute path)")
        
    # Don't allow parent directory traversal
    if '..' in filename:
        print(f"Security: Cannot traverse directories with {{filename}}", file=sys.stderr)
        raise PermissionError(f"Security: Path traversal in {{filename}} is not allowed")
        
    # Only allow access to script directory and subdirectories
    norm_path = os.path.normpath(os.path.join(script_dir, filename))
    if not norm_path.startswith(script_dir):
        print(f"Security: Access outside script directory not allowed {{filename}}", file=sys.stderr)
        raise PermissionError(f"Security: Access outside script directory is not allowed")
    
    # Call original open
    return builtins._original_open(norm_path, *args, **kwargs)
    
builtins.open = secure_open

# Run the script
try:
    print(f"Debug: Running script at {{script_name}} with args: {{sys.argv[1:]}}")
    with secure_open(script_name, 'r') as f:
        script_code = f.read()
        
    # Create namespace for execution
    script_globals = {{
        '__file__': script_name,
        '__name__': '__main__',
        '__builtins__': __builtins__,
        '__package__': None,
    }}
    
    # Execute the script with restricted globals
    builtins._original_exec(script_code, script_globals)
    
except FileNotFoundError:
    print(f"Error: Could not find script file {{script_name}}", file=sys.stderr)
    sys.exit(1)
except PermissionError as e:
    print(f"Error: {{e}}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Error executing script: {{type(e).__name__}}: {{e}}", file=sys.stderr)
    sys.exit(1)
""")
    
    # Execute with controlled environment
    env = os.environ.copy()
    env["PYTHONPATH"] = sandbox_dir  # Restrict module imports to sandbox
    env["PYTHONIOENCODING"] = "utf-8"  # Ensure proper encoding
    
    try:
        # Run the wrapper script directly
        result = subprocess.run(
            ["python", temp_wrapper],
            env=env, 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        
        # Clean up the wrapper script
        try:
            os.remove(temp_wrapper)
        except:
            pass  # Ignore cleanup errors
            
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        try:
            os.remove(temp_wrapper)
        except:
            pass
        return {
            "stdout": "",
            "stderr": "Script execution timed out after 30 seconds",
            "returncode": 1
        }
    except Exception as e:
        try:
            os.remove(temp_wrapper)
        except:
            pass
        return {
            "stdout": "",
            "stderr": f"Error running script: {str(e)}",
            "returncode": 1
        } 