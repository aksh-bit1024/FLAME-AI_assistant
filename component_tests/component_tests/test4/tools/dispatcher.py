from typing import Dict, List, Any, Callable
from .system import run_command, RUN_COMMAND_SCHEMA
from .files import read_file, write_file, list_directory, FILES_SCHEMAS
from .memory_tool import save_memory, read_memory, delete_memory, MEMORY_SCHEMAS, init_memory_tool
from core.memory import MemoryManager

class ToolDispatcher:
    def __init__(self, memory_manager: MemoryManager = None):
        self._tools: Dict[str, Callable] = {}
        self._schemas: List[Dict[str, Any]] = []

        if memory_manager:
            init_memory_tool(memory_manager)

        # System tools
        self.register_tool("run_command", run_command, RUN_COMMAND_SCHEMA)

        # File tools
        self.register_tool("read_file", read_file, FILES_SCHEMAS[0])
        self.register_tool("write_file", write_file, FILES_SCHEMAS[1])
        self.register_tool("list_directory", list_directory, FILES_SCHEMAS[2])

        # Memory tools
        self.register_tool("save_memory", save_memory, MEMORY_SCHEMAS[0])
        self.register_tool("read_memory", read_memory, MEMORY_SCHEMAS[1])
        self.register_tool("delete_memory", delete_memory, MEMORY_SCHEMAS[2])

    def register_tool(self, name: str, func: Callable, schema: Dict[str, Any]):
        self._tools[name] = func
        self._schemas = [item for item in self._schemas if item.get("function", {}).get("name") != name]
        self._schemas.append(schema)

    def get_schemas(self) -> List[Dict[str, Any]]:
        return self._schemas

    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        if tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' is not registered.")
        if not isinstance(arguments, dict):
            raise TypeError("Tool arguments must be a JSON object.")
        return self._tools[tool_name](**arguments)