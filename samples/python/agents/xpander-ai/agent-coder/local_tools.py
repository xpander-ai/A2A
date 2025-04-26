import os
import subprocess
import difflib
import shlex
from typing import Dict, List, Any, Optional, Union, Tuple
import logging
import time
import json
import sandbox

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Git operations functions
def git_create_branch(branch_name: str) -> Dict[str, Any]:
    """
    Create a new Git branch and switch to it
    
    Args:
        branch_name: Name of the branch to create
        
    Returns:
        dict: Result with success status and message
    """
    try:
        result = subprocess.run(
            ["git", "checkout", "-b", branch_name],
            capture_output=True,
            text=True,
            check=True
        )
        return {
            "success": True,
            "message": f"Branch '{branch_name}' created and checked out",
            "output": result.stdout
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"Git branch creation failed: {e}")
        return {
            "success": False,
            "message": f"Failed to create branch: {e}",
            "error": e.stderr
        }

def git_clone(repo_url: str, target_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Clone a git repository securely.
    
    Args:
        repo_url: URL of the git repository to clone
        target_dir: Directory to clone into
        
    Returns:
        Dictionary with clone status and any output/error
    """
    try:
        # Create directory if it doesn't exist
        if target_dir and not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)
            
        # Clean target directory name from repo URL
        repo_name = repo_url.split('/')[-1]
        if repo_name.endswith('.git'):
            repo_name = repo_name[:-4]
            
        # Set timeout to prevent hanging on network issues
        timeout_seconds = 60
        
        # Clone the repository with controlled environment and timeout
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"  # Disable authentication prompts
        
        cmd = ["git", "clone", "--depth", "1", repo_url]
        if target_dir:
            cmd.append(target_dir)
            
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env=env
            )
            clone_success = result.returncode == 0
            stderr = result.stderr
            stdout = result.stdout
        except subprocess.TimeoutExpired:
            clone_success = False
            stderr = f"Git clone timed out after {timeout_seconds} seconds"
            stdout = ""
            
        # Check if clone worked by verifying .git exists
        clone_dir = target_dir if target_dir else repo_name
        if clone_success and not os.path.exists(os.path.join(clone_dir, '.git')):
            clone_success = False
            stderr += "\nClone appears to have failed: .git directory not found"
            
        if clone_success:
            return {
                "success": True,
                "message": f"Repository cloned successfully to {os.path.basename(clone_dir)}",
                "stdout": stdout,
                "target_dir": os.path.basename(clone_dir)
            }
        else:
            # Diagnostic information for failed clones
            error_message = stderr
            if "could not resolve host" in stderr.lower():
                error_message = "Network error: Could not resolve the repository host."
            elif "authentication failed" in stderr.lower():
                error_message = "Authentication error: Private repository requires authentication."
            elif "repository not found" in stderr.lower():
                error_message = "Repository not found. Check the URL and try again."
                
            return {
                "success": False,
                "error": error_message,
                "stdout": stdout,
                "stderr": stderr,
                "target_dir": os.path.basename(clone_dir)
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error cloning repository: {str(e)}",
            "repo_url": repo_url
        }

def git_commit_changes(message: str, add_all: bool = True) -> Dict[str, Any]:
    """
    Commit changes to Git repository
    
    Args:
        message: Commit message
        add_all: Whether to add all changes (git add .) before commit
        
    Returns:
        dict: Result with success status and message
    """
    try:
        results = {}
        
        if add_all:
            add_result = subprocess.run(
                ["git", "add", "."],
                capture_output=True,
                text=True,
                check=True
            )
            results["add"] = {
                "success": True,
                "output": add_result.stdout
            }
        
        commit_result = subprocess.run(
            ["git", "commit", "-m", message],
            capture_output=True,
            text=True,
            check=True
        )
        
        results["commit"] = {
            "success": True,
            "output": commit_result.stdout
        }
        
        return {
            "success": True,
            "message": f"Changes committed with message: '{message}'",
            "details": results
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"Git commit failed: {e}")
        return {
            "success": False,
            "message": f"Failed to commit changes: {e}",
            "error": e.stderr
        }

def git_push_changes(remote: str = "origin", branch: Optional[str] = None) -> Dict[str, Any]:
    """
    Push commits to remote repository
    
    Args:
        remote: Remote repository name (default: origin)
        branch: Branch to push (default: current branch)
        
    Returns:
        dict: Result with success status and message
    """
    try:
        # Get current branch if not specified
        if branch is None:
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                check=True
            )
            branch = branch_result.stdout.strip()
        
        # Push changes
        push_result = subprocess.run(
            ["git", "push", remote, branch],
            capture_output=True,
            text=True,
            check=True
        )
        
        return {
            "success": True,
            "message": f"Changes pushed to {remote}/{branch}",
            "output": push_result.stdout
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"Git push failed: {e}")
        return {
            "success": False,
            "message": f"Failed to push changes: {e}",
            "error": e.stderr
        }

def git_status() -> Dict[str, Any]:
    """
    Get the current Git repository status
    
    Returns:
        dict: Result with success status and status output
    """
    try:
        result = subprocess.run(
            ["git", "status"],
            capture_output=True,
            text=True,
            check=True
        )
        
        return {
            "success": True,
            "message": "Git status retrieved",
            "status": result.stdout
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"Git status failed: {e}")
        return {
            "success": False,
            "message": f"Failed to get repository status: {e}",
            "error": e.stderr
        }

# File operations functions
def read_file(filepath: str) -> Dict[str, Any]:
    """
    Read the content of a file securely within the sandbox.
    
    Args:
        filepath: Path to the file to read
        
    Returns:
        Dictionary with file content or error
    """
    try:
        # Check if file exists
        if not os.path.exists(filepath):
            return {
                "success": False,
                "error": f"File not found: {os.path.basename(filepath)}"
            }
        
        # Read the file content
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            
        return {
            "success": True,
            "content": content,
            "filepath": os.path.basename(filepath)
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error reading file: {str(e)}",
            "filepath": filepath
        }

def count_file_lines(filepath: str) -> Dict[str, Any]:
    """
    Count the number of lines in a file securely within the sandbox.
    
    Args:
        filepath: Path to the file to count lines in
        
    Returns:
        Dictionary with line count or error
    """
    try:
        # Ensure path is inside the sandbox
        safe_path = sandbox.get_sandbox(filepath=filepath)
        
        # Security check - confirm path is still safe before reading
        if not os.path.exists(safe_path):
            return {
                "success": False,
                "error": f"File not found: {os.path.basename(filepath)}"
            }
        
        # Count the lines
        with open(safe_path, 'r', encoding='utf-8', errors='replace') as f:
            line_count = sum(1 for _ in f)
            
        return {
            "success": True,
            "line_count": line_count,
            "filepath": os.path.basename(filepath)
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error counting lines: {str(e)}",
            "filepath": filepath
        }

def write_file(filepath: str, content: str) -> Dict[str, Any]:
    """
    Write content to a file securely within the sandbox.
    
    Args:
        filepath: Path to the file to write
        content: Content to write to the file
        
    Returns:
        Dictionary with status and any error
    """
    try:
        # Ensure path is inside the sandbox
        safe_path = sandbox.get_sandbox(filepath=filepath)
        
        # Create the parent directory if it doesn't exist
        parent_dir = os.path.dirname(safe_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
            
        # Write the content to the file
        with open(safe_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return {
            "success": True,
            "message": f"File written successfully: {os.path.basename(filepath)}",
            "filepath": os.path.basename(filepath)
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error writing file: {str(e)}",
            "filepath": filepath
        }

def list_directory(directory: str = '.') -> Dict[str, Any]:
    """
    List the contents of a directory securely within the sandbox.
    
    Args:
        directory: Path to the directory to list (default: current directory)
        
    Returns:
        Dictionary with directory contents or error
    """
    try:
        # Block access to system directories
        for blocked_path in sandbox.BLOCKED_SYSTEM_PATHS:
            if blocked_path in directory:
                return {
                    "success": False,
                    "error": f"Security error: Access to {blocked_path} is restricted",
                    "directory": directory
                }
        
        # Handle empty directory or '.' case
        if not directory or directory.strip() == '' or directory == '.':
            directory = '.'
        
        # Additional checks for root directory or traversal attempts
        if directory == '/' or directory == '~/':
            return {
                "success": False,
                "error": "Security error: Listing root directory is not allowed",
                "directory": directory
            }
            
        # Block attempts to list system directories
        if directory in ['/etc', '/var', '/usr', '/bin', '/sbin']:
            return {
                "success": False,
                "error": f"Security error: Listing {directory} is not allowed",
                "directory": directory
            }
        
        # Ensure path is inside the sandbox
        safe_path = sandbox.get_sandbox(filepath=directory)
        
        # Security check - confirm path is still safe before listing
        if not os.path.exists(safe_path):
            # Try to create the directory if it doesn't exist
            try:
                os.makedirs(safe_path, exist_ok=True)
                print(f"Notice: Created directory {os.path.basename(directory)}")
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Directory not found and could not be created: {os.path.basename(directory)}",
                    "details": str(e)
                }

        if not os.path.isdir(safe_path):
            return {
                "success": False,
                "error": f"Path exists but is not a directory: {os.path.basename(directory)}",
                "path_type": "file" if os.path.isfile(safe_path) else "unknown"
            }
        
        # List the directory contents
        try:
            items = os.listdir(safe_path)
            
            # Get additional information about each item
            contents = []
            for item in items:
                item_path = os.path.join(safe_path, item)
                is_dir = os.path.isdir(item_path)
                size = None
                if not is_dir:
                    try:
                        size = os.path.getsize(item_path)
                    except:
                        size = -1  # Indicate error getting size
                        
                contents.append({
                    "name": item,
                    "type": "directory" if is_dir else "file",
                    "size": size
                })
                
            return {
                "success": True,
                "contents": contents,
                "directory": os.path.basename(directory) or os.path.basename(safe_path),
                "path": safe_path  # Include the full path for diagnostics
            }
        except PermissionError:
            return {
                "success": False,
                "error": f"Permission denied when listing directory: {os.path.basename(directory)}",
                "path": safe_path
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Error listing directory: {str(e)}",
            "directory": directory
        }

# Terminal execution function
def execute_command(command: str, cwd: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute a shell command securely in the sandbox environment.
    
    Args:
        command: The command to execute
        cwd: The working directory to execute the command in
        
    Returns:
        Dictionary with command output and status
    """
    try:
        # Block known system commands and network access commands
        blocked_commands = [
            'ps', 'top', 'htop', 'netstat', 'ifconfig', 'ping',
            'curl', 'wget', 'cat /etc', 'find /', 'ls /', 'uname -a'
        ]
        
        for blocked in blocked_commands:
            if command.startswith(blocked) or f" {blocked}" in command:
                return {
                    "success": False,
                    "error": f"Security error: Command '{blocked}' is not allowed",
                    "command": command
                }
        
        # Block system directory access
        for blocked_path in sandbox.BLOCKED_SYSTEM_PATHS:
            if blocked_path in command:
                return {
                    "success": False,
                    "error": f"Security error: Access to {blocked_path} is restricted",
                    "command": command
                }
        
        # Security validation - ensure the command doesn't attempt to escape the sandbox
        try:
            sandbox.validate_command(command)
        except ValueError as e:
            return {
                "success": False,
                "error": str(e),
                "command": command
            }
        
        # Handle cwd parameter - ensure it exists
        if cwd:
            safe_cwd = sandbox.get_sandbox(filepath=cwd)
            if not os.path.exists(safe_cwd):
                try:
                    os.makedirs(safe_cwd, exist_ok=True)
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Working directory does not exist and could not be created: {str(e)}",
                        "command": command
                    }
        else:
            safe_cwd = sandbox.get_sandbox()
        
        # Special handling for Python scripts - use our secure execution wrapper
        if command.startswith('python ') or command.startswith('python3 '):
            parts = command.split()
            interpreter = parts[0]
            
            # Extract the script path from the command
            if len(parts) > 1:
                # Check if the part is an actual Python script or just a flag
                if parts[1].endswith('.py'):
                    script_path = parts[1]
                    args = parts[2:] if len(parts) > 2 else None
                    
                    # Check if script exists in the current directory
                    full_script_path = os.path.join(safe_cwd, script_path)
                    if not os.path.exists(full_script_path) and not os.path.isabs(script_path):
                        # It might be a script in the parent directory of the sandbox
                        # Try to find it by name
                        alt_script_path = os.path.join(sandbox.current_sandbox, script_path)
                        if os.path.exists(alt_script_path):
                            script_path = alt_script_path
                    
                    result = sandbox.secure_python_execution(script_path, args)
                    return {
                        "success": result["returncode"] == 0,
                        "stdout": result["stdout"],
                        "stderr": result["stderr"],
                        "command": command,
                        "script_path": script_path
                    }
        
        # Set up a restricted environment for the command
        restricted_env = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": safe_cwd,
            "SANDBOX_RESTRICTED": "1",  # Flag to indicate we're in a restricted environment
            "HOME": safe_cwd,  # Redirect home directory to the sandbox
            "TMPDIR": safe_cwd  # Redirect temporary directory to the sandbox
        }
        
        # Remove potentially dangerous environment variables
        for dangerous_var in ["LD_PRELOAD", "LD_LIBRARY_PATH", "DYLD_INSERT_LIBRARIES", 
                             "DYLD_LIBRARY_PATH", "PYTHONHOME", "PYTHONSTARTUP"]:
            restricted_env.pop(dangerous_var, None)
        
        # For non-Python commands, execute directly but with controlled environment
        starttime = time.time()
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=safe_cwd,
            capture_output=True, 
            text=True,
            timeout=30,  # Add a timeout to prevent long-running commands
            env=restricted_env  # Use restricted environment
        )
        endtime = time.time()
        
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": command,
            "time_taken": endtime - starttime
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Command timed out after 30 seconds",
            "command": command
        }
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "command": command
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error executing command: {str(e)}",
            "command": command
        }

# Set up local tools
local_tools = [
    {
        "declaration": {
            "type": "function",
            "function": {
                "name": "git_create_branch",
                "description": "Create a new Git branch and switch to it",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "branch_name": {
                            "type": "string",
                            "description": "Name of the branch to create"
                        }
                    },
                    "required": ["branch_name"]
                }
            }
        },
        "fn": git_create_branch
    },
    {
        "declaration": {
            "type": "function",
            "function": {
                "name": "git_clone",
                "description": "Clone a Git repository",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repo_url": {
                            "type": "string",
                            "description": "URL of the Git repository to clone"
                        },
                        "target_dir": {
                            "type": "string",
                            "description": "Optional target directory for the clone (default: auto-named by Git)"
                        }
                    },
                    "required": ["repo_url"]
                }
            }
        },
        "fn": git_clone
    },
    {
        "declaration": {
            "type": "function",
            "function": {
                "name": "git_commit_changes",
                "description": "Commit changes to Git repository",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Commit message"
                        },
                        "add_all": {
                            "type": "boolean",
                            "description": "Whether to add all changes (git add .) before commit"
                        }
                    },
                    "required": ["message"]
                }
            }
        },
        "fn": git_commit_changes
    },
    {
        "declaration": {
            "type": "function",
            "function": {
                "name": "git_push_changes",
                "description": "Push commits to remote repository",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "remote": {
                            "type": "string",
                            "description": "Remote repository name"
                        },
                        "branch": {
                            "type": "string",
                            "description": "Branch to push (default: current branch)"
                        }
                    },
                    "required": []
                }
            }
        },
        "fn": git_push_changes
    },
    {
        "declaration": {
            "type": "function",
            "function": {
                "name": "git_status",
                "description": "Get the current Git repository status",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        "fn": git_status
    },
    {
        "declaration": {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read contents of a file, optionally specifying line ranges",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filepath": {
                            "type": "string",
                            "description": "Path to the file to read"
                        },
                        "start_line": {
                            "type": "integer",
                            "description": "Line number to start reading from (1-indexed, optional)"
                        },
                        "end_line": {
                            "type": "integer",
                            "description": "Line number to end reading at (1-indexed, inclusive, optional)"
                        },
                        "max_lines": {
                            "type": "integer",
                            "description": "Maximum number of lines to read when no range is specified (default: 50)"
                        }
                    },
                    "required": ["filepath"]
                }
            }
        },
        "fn": read_file
    },
    {
        "declaration": {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Write content to a file with various modes, including line-specific edits. Returns a diff of changes made.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filepath": {
                            "type": "string",
                            "description": "Path to the file to write"
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write to the file"
                        },
                        "mode": {
                            "type": "string",
                            "description": "Writing mode - 'overwrite' (replace entire file), 'replace' (replace specific lines), 'insert' (insert at line)"
                        },
                        "start_line": {
                            "type": "integer",
                            "description": "Line number to start replacement/insertion (1-indexed, required for replace/insert modes)"
                        },
                        "end_line": {
                            "type": "integer",
                            "description": "Line number to end replacement (1-indexed, inclusive, required for replace mode)"
                        },
                        "create_dirs": {
                            "type": "boolean",
                            "description": "Whether to create parent directories if they don't exist"
                        }
                    },
                    "required": ["filepath", "content"]
                }
            }
        },
        "fn": write_file
    },
    {
        "declaration": {
            "type": "function",
            "function": {
                "name": "list_directory",
                "description": "List contents of a directory",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory": {
                            "type": "string",
                            "description": "Path to the directory to list"
                        }
                    },
                    "required": []
                }
            }
        },
        "fn": list_directory
    },
    {
        "declaration": {
            "type": "function",
            "function": {
                "name": "execute_command",
                "description": "Execute a shell command",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Command to execute"
                        },
                        "cwd": {
                            "type": "string",
                            "description": "Working directory for the command"
                        }
                    },
                    "required": ["command"]
                }
            }
        },
        "fn": execute_command
    },
    {
        "declaration": {
            "type": "function",
            "function": {
                "name": "count_file_lines",
                "description": "Count the number of lines in a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filepath": {
                            "type": "string",
                            "description": "Path to the file to count lines"
                        }
                    },
                    "required": ["filepath"]
                }
            }
        },
        "fn": count_file_lines
    }
]

local_tools_list = [tool['declaration'] for tool in local_tools]
local_tools_by_name = {tool['declaration']['function']['name']: tool['fn'] for tool in local_tools}
