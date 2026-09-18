import os
from pathlib import Path
from typing import Dict, Any, List

# Lock operations to the project root sandbox
PROJECT_ROOT = Path(__file__).resolve().parent.parent

def _validate_path(path_str: str) -> Path:
    """Ensures target path is within the project sandbox directory."""
    target_path = (PROJECT_ROOT / path_str).resolve()
    try:
        target_path.relative_to(PROJECT_ROOT)
    except ValueError:
        raise PermissionError(f"Access denied: '{path_str}' is outside the project sandbox ({PROJECT_ROOT}).")
    return target_path

def read_file(path: str) -> Dict[str, Any]:
    """Reads content from a text file within the project sandbox."""
    try:
        file_path = _validate_path(path)
        if not file_path.is_file():
            return {"status": "error", "content": "", "error": f"File not found: '{path}'"}
        
        content = file_path.read_text(encoding="utf-8")
        return {"status": "success", "content": content, "error": ""}
    except Exception as e:
        return {"status": "error", "content": "", "error": str(e)}

def write_file(path: str, content: str, mode: str = "w") -> Dict[str, Any]:
    """Writes or appends content to a file inside the project sandbox."""
    try:
        file_path = _validate_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_mode = "a" if mode.lower() == "append" else "w"
        with open(file_path, file_mode, encoding="utf-8") as f:
            f.write(content)
            
        return {"status": "success", "path": str(path), "error": ""}
    except Exception as e:
        return {"status": "error", "path": str(path), "error": str(e)}

def list_directory(path: str = ".") -> Dict[str, Any]:
    """Lists files and directories inside the specified relative directory."""
    try:
        dir_path = _validate_path(path)
        if not dir_path.is_dir():
            return {"status": "error", "items": [], "error": f"Not a directory: '{path}'"}
        
        items = []
        for item in dir_path.iterdir():
            items.append({
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
                "size_bytes": item.stat().st_size if item.is_file() else 0
            })
        return {"status": "success", "items": items, "error": ""}
    except Exception as e:
        return {"status": "error", "items": [], "error": str(e)}

# --- Function Schemas for LLM ---
FILES_SCHEMAS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Reads full text content of a file within project sandbox.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative file path from project root."
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Writes or appends text content to a file in project sandbox.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative file path from project root."
                    },
                    "content": {
                        "type": "string",
                        "description": "Text content to write."
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["write", "append"],
                        "description": "'write' to overwrite, 'append' to add at the end.",
                        "default": "write"
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "Lists contents of a folder within the project sandbox.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path. Defaults to root ('.').",
                        "default": "."
                    }
                }
            }
        }
    }
]