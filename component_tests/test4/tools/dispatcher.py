from typing import Dict, List, Any, Callable

from .system import run_command, RUN_COMMAND_SCHEMA
from .files import read_file, write_file, list_directory, FILES_SCHEMAS


class ToolDispatcher:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._schemas: List[Dict[str, Any]] = []

        # Register System Tools
        self.register_tool("run_command", run_command, RUN_COMMAND_SCHEMA)

        # Register File Tools
        self.register_tool("read_file", read_file, FILES_SCHEMAS[0])
        self.register_tool("write_file", write_file, FILES_SCHEMAS[1])
        self.register_tool("list_directory", list_directory, FILES_SCHEMAS[2])

    def register_tool(self, name: str, func: Callable, schema: Dict[str, Any]):
        """Registers a function and its OpenAI-compatible JSON schema."""
        self._tools[name] = func
        self._schemas.append(schema)

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Returns registered tool schemas to pass to the LLM."""
        return self._schemas

    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Executes a registered tool by name with provided dictionary arguments."""
        if tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' is not registered with dispatcher.")

        func = self._tools[tool_name]
        return func(**arguments)