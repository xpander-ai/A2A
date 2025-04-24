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
def read_file(filepath: str) -> Dict[str, Any]:
    """
    Read contents of a file
    
    Args:
        filepath: Path to the file to read
        
    Returns:
        dict: Result with success status and file contents
    """
    try:
        with open(filepath, 'r') as file:
            content = file.read()
        
        return {
            "success": True,
            "message": f"File '{filepath}' read successfully",
            "content": content
        }
    except Exception as e:
        logger.error(f"File read failed for {filepath}: {e}")
        return {
            "success": False,
            "message": f"Failed to read file '{filepath}': {e}",
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
                "description": "Read contents of a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filepath": {
                            "type": "string",
                            "description": "Path to the file to read"
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
    }
]

local_tools_list = [tool['declaration'] for tool in local_tools]
local_tools_by_name = {tool['declaration']['function']['name']: tool['fn'] for tool in local_tools}
