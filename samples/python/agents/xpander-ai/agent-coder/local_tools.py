import os
import subprocess
from typing import Dict, List, Any, Optional, Union
import logging

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
    Clone a Git repository
    
    Args:
        repo_url: URL of the Git repository to clone
        target_dir: Optional target directory for the clone (default: auto-named by Git)
        
    Returns:
        dict: Result with success status and message
    """
    try:
        # Build the command
        command = ["git", "clone", repo_url]
        if target_dir:
            command.append(target_dir)
            
        # Execute the clone
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Determine the directory name that was created
        if target_dir:
            clone_dir = target_dir
        else:
            # Extract repository name from URL
            # For URLs like https://github.com/user/repo.git or git@github.com:user/repo.git
            # This extracts 'repo'
            repo_name = repo_url.split('/')[-1]
            if repo_name.endswith('.git'):
                repo_name = repo_name[:-4]
            clone_dir = repo_name
        
        return {
            "success": True,
            "message": f"Repository cloned successfully to '{clone_dir}'",
            "output": result.stdout,
            "clone_dir": clone_dir
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"Git clone failed: {e}")
        return {
            "success": False,
            "message": f"Failed to clone repository: {e}",
            "error": e.stderr
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
def read_file(filepath: str, start_line: Optional[int] = None, end_line: Optional[int] = None, max_lines: int = 50) -> Dict[str, Any]:
    """
    Read contents of a file, optionally specifying line ranges
    
    Args:
        filepath: Path to the file to read
        start_line: Line number to start reading from (1-indexed, optional)
        end_line: Line number to end reading at (1-indexed, inclusive, optional)
        max_lines: Maximum number of lines to read when no range is specified (default: 50)
        
    Returns:
        dict: Result with success status and file contents
    """
    try:
        with open(filepath, 'r') as file:
            # Read all lines so we can count them
            lines = file.readlines()
            total_lines = len(lines)
            
            if start_line is not None or end_line is not None:
                # Read specific line range
                # Validate line numbers
                if start_line is None:
                    start_line = 1
                if end_line is None:
                    end_line = total_lines
                
                # Adjust for 1-indexed input
                start_idx = max(0, start_line - 1)
                end_idx = min(total_lines, end_line)
                
                if start_idx >= len(lines) or start_idx < 0:
                    return {
                        "success": False,
                        "message": f"Invalid start_line: {start_line}. File has {total_lines} lines.",
                        "total_lines": total_lines
                    }
                
                content = ''.join(lines[start_idx:end_idx])
                
                return {
                    "success": True,
                    "message": f"File '{filepath}' read successfully (lines {start_line}-{end_line})",
                    "content": content,
                    "start_line": start_line,
                    "end_line": end_line,
                    "total_lines": total_lines
                }
            else:
                # Read with default limit
                if total_lines > max_lines:
                    content = ''.join(lines[:max_lines])
                    return {
                        "success": True,
                        "message": f"File '{filepath}' read successfully (first {max_lines} of {total_lines} lines)",
                        "content": content,
                        "start_line": 1,
                        "end_line": max_lines,
                        "total_lines": total_lines,
                        "truncated": True
                    }
                else:
                    # File is smaller than max_lines, return everything
                    content = ''.join(lines)
                    return {
                        "success": True,
                        "message": f"File '{filepath}' read successfully",
                        "content": content,
                        "total_lines": total_lines
                    }
    except Exception as e:
        logger.error(f"File read failed for {filepath}: {e}")
        return {
            "success": False,
            "message": f"Failed to read file '{filepath}': {e}",
            "error": str(e)
        }

def count_file_lines(filepath: str) -> Dict[str, Any]:
    """
    Count the number of lines in a file
    
    Args:
        filepath: Path to the file to count lines
        
    Returns:
        dict: Result with success status and line count
    """
    try:
        with open(filepath, 'r') as file:
            line_count = sum(1 for _ in file)
        
        return {
            "success": True,
            "message": f"Line count for '{filepath}' retrieved successfully",
            "line_count": line_count
        }
    except Exception as e:
        logger.error(f"File line count failed for {filepath}: {e}")
        return {
            "success": False,
            "message": f"Failed to count lines in file '{filepath}': {e}",
            "error": str(e)
        }

def write_file(filepath: str, content: str, create_dirs: bool = True) -> Dict[str, Any]:
    """
    Write content to a file
    
    Args:
        filepath: Path to the file to write
        content: Content to write to the file
        create_dirs: Whether to create parent directories if they don't exist
        
    Returns:
        dict: Result with success status and message
    """
    try:
        # Create parent directories if needed
        if create_dirs:
            directory = os.path.dirname(filepath)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
        
        with open(filepath, 'w') as file:
            file.write(content)
        
        return {
            "success": True,
            "message": f"Content written to '{filepath}' successfully",
            "filepath": filepath
        }
    except Exception as e:
        logger.error(f"File write failed for {filepath}: {e}")
        return {
            "success": False,
            "message": f"Failed to write to file '{filepath}': {e}",
            "error": str(e)
        }

def list_directory(directory: str = '.') -> Dict[str, Any]:
    """
    List contents of a directory
    
    Args:
        directory: Path to the directory to list (default: current directory)
        
    Returns:
        dict: Result with success status and directory contents
    """
    try:
        items = os.listdir(directory)
        
        # Get additional info about each item
        contents = []
        for item in items:
            item_path = os.path.join(directory, item)
            item_type = "directory" if os.path.isdir(item_path) else "file"
            item_size = os.path.getsize(item_path) if os.path.isfile(item_path) else None
            
            contents.append({
                "name": item,
                "type": item_type,
                "size": item_size
            })
        
        return {
            "success": True,
            "message": f"Directory '{directory}' listed successfully",
            "contents": contents
        }
    except Exception as e:
        logger.error(f"Directory listing failed for {directory}: {e}")
        return {
            "success": False,
            "message": f"Failed to list directory '{directory}': {e}",
            "error": str(e)
        }

# Terminal execution function
def execute_command(command: Union[str, List[str]], cwd: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute a shell command
    
    Args:
        command: Command to execute (string or list of arguments)
        cwd: Working directory for the command
        
    Returns:
        dict: Result with success status, stdout, and stderr
    """
    try:
        # Convert string command to list if needed
        if isinstance(command, str):
            # Simple shell=True execution for string commands
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=cwd
            )
        else:
            # List-based execution (preferred for security)
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=cwd
            )
        
        # Check if command succeeded
        if result.returncode == 0:
            return {
                "success": True,
                "message": "Command executed successfully",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        else:
            return {
                "success": False,
                "message": f"Command failed with return code {result.returncode}",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
    except Exception as e:
        logger.error(f"Command execution failed: {e}")
        return {
            "success": False,
            "message": f"Failed to execute command: {e}",
            "error": str(e)
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
                "description": "Write content to a file",
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
