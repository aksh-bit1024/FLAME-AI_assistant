import os
import subprocess
import re
from pathlib import Path
from typing import Dict, Any, Optional

# Define the root path of the project sandbox
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# List of forbidden patterns (Strategy 1 fallback)
BLOCKED_PATTERNS = [
    r"\brm\s+-rf\b", r"\bdel\s+/f\b", r"\bformat\b", 
    r"\bshutdown\b", r"\breboot\b", r">\s*/dev/"
]

def run_command(command: str, timeout: int = 30, cwd: Optional[str] = None) -> Dict[str, Any]:
    """
    Executes a shell command safely using Path Sandboxing, 
    Interactive User Confirmation, and Strict Timeouts.
    """
    
    # --- Strategy 1 Guard: Pattern Filter ---
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return {
                "status": "error",
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Security Guard: Blocked dangerous command pattern '{pattern}'."
            }

    # --- Strategy 2 Guard: Path Sandboxing ---
    if not isinstance(command, str) or not command.strip():
        return {"status": "error", "exit_code": -1, "stdout": "", "stderr": "Command must be a non-empty string."}
    if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= 300:
        return {"status": "error", "exit_code": -1, "stdout": "", "stderr": "Timeout must be an integer from 1 to 300 seconds."}
    if cwd is not None and not isinstance(cwd, (str, os.PathLike)):
        return {"status": "error", "exit_code": -1, "stdout": "", "stderr": "Working directory must be a path string."}

    target_dir = (PROJECT_ROOT / cwd).resolve() if cwd else PROJECT_ROOT
    try:
        # Verify target_dir is at or inside PROJECT_ROOT
        target_dir.relative_to(PROJECT_ROOT)
    except ValueError:
        return {
            "status": "error",
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Security Guard: Target directory '{target_dir}' is outside project sandbox ({PROJECT_ROOT})."
        }

    # --- Strategy 3 Guard: Interactive Confirmation Prompt ---
    print("\n" + "="*50)
    print("⚠️  [FLAME SECURITY GUARD] Shell Command Execution Request")
    print(f"👉 Command : {command}")
    print(f"📂 Sandbox : {target_dir}")
    print("="*50)
    
    approval = input("Allow execution? (y/N): ").strip().lower()
    if approval != 'y':
        return {
            "status": "cancelled",
            "exit_code": -1,
            "stdout": "",
            "stderr": "Command execution rejected by user."
        }

    # --- Strategy 4 Guard: Timeout & Subprocess Constraints ---
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=target_dir
        )
        return {
            "status": "success" if result.returncode == 0 else "error",
            "exit_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip()
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Execution timed out after {timeout} seconds."
        }
    except Exception as e:
        return {
            "status": "error",
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Execution failed: {str(e)}"
        }

# --- Function Schema for LLM ---
RUN_COMMAND_SCHEMA = {
    "type": "function",
    "function": {
        "name": "run_command",
        "description": "Executes a system shell command inside the project sandbox with user approval.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command line string to run."
                },
                "timeout": {
                    "type": "integer",
                    "description": "Maximum execution time in seconds. Default is 30.",
                    "default": 30
                }
            },
            "required": ["command"]
        }
    }
}