from typing import Dict, Any, List
from core.memory import MemoryManager

_memory: MemoryManager = None

def init_memory_tool(memory_manager: MemoryManager):
    """Initializes the global memory tool instance."""
    global _memory
    _memory = memory_manager

def save_memory(key: str, value: Any) -> Dict[str, Any]:
    """Saves a user preference or project fact into SQLite."""
    if not _memory:
        return {"status": "error", "message": "MemoryManager is not initialized."}
    _memory.set_preference(key, value)
    return {"status": "success", "key": key, "value": value}

def read_memory(key: str) -> Dict[str, Any]:
    """Retrieves a single memory by its key."""
    if not _memory:
        return {"status": "error", "message": "MemoryManager is not initialized."}
    val = _memory.get_preference(key)
    if val is None:
        return {"status": "not_found", "key": key}
    return {"status": "success", "key": key, "value": val}

def delete_memory(key: str) -> Dict[str, Any]:
    """Deletes a stored memory key."""
    if not _memory:
        return {"status": "error", "message": "MemoryManager is not initialized."}
    existed = _memory.delete_preference(key)
    return {"status": "success" if existed else "not_found", "key": key}

def get_all_memories() -> Dict[str, Any]:
    """Retrieves all stored key-value pairs."""
    if not _memory:
        return {"status": "error", "message": "MemoryManager is not initialized."}
    return {"status": "success", "memories": _memory.get_all_preferences()}


# Function schemas passed to the LLM
MEMORY_SCHEMAS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "Saves persistent user preferences, project rules, or key facts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "The category or key name (e.g., 'user_name', 'shell_type')."},
                    "value": {"type": "string", "description": "The information to save."}
                },
                "required": ["key", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_memory",
            "description": "Retrieves a stored memory by key.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Key name to search."}
                },
                "required": ["key"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_memory",
            "description": "Deletes a stored memory when it is no longer relevant.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Key name to delete."}
                },
                "required": ["key"]
            }
        }
    }
]