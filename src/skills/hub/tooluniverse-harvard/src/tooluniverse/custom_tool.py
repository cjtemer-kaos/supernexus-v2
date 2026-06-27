"""
CustomTool implementation for ToolUniverse
Handles execution of dynamically generated tools with external code files
"""

import importlib.util
import os
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("CustomTool")
class CustomTool(BaseTool):
    """
    CustomTool class for executing dynamically generated tools
    """

    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.code_file = tool_config.get("code_file")
        self.name = tool_config.get("name", "CustomTool")
        self.description = tool_config.get("description", "")

        # Load the external code if code_file is specified
        self.execute_function = None
        if self.code_file and os.path.exists(self.code_file):
            self._load_external_code()
        elif (
            "implementation" in tool_config
            and "source_code" in tool_config["implementation"]
        ):
            self._load_embedded_code(tool_config["implementation"])

    def _load_external_code(self):
        """Load the execute_tool function from external Python file"""
        try:
            # Load module from file
            spec = importlib.util.spec_from_file_location(
                "custom_tool_module", self.code_file
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Get the execute_tool function
            if hasattr(module, "execute_tool"):
                self.execute_function = module.execute_tool
            else:
                print(f"Warning: No execute_tool function found in {self.code_file}")

        except Exception as e:
            print(f"Error loading external code from {self.code_file}: {e}")

    def _load_embedded_code(self, implementation: Dict):
        """Load the execute_tool function from embedded source code"""
        try:
            source_code = implementation.get("source_code", "")
            main_function = implementation.get("main_function", "execute_tool")

            # Create a temporary module to execute the code
            import types

            module = types.ModuleType("embedded_tool_module")

            # Execute the source code in the module namespace
            exec(source_code, module.__dict__)

            # Get the main function
            if hasattr(module, main_function):
                self.execute_function = getattr(module, main_function)
            else:
                print(f"Warning: No {main_function} function found in embedded code")

        except Exception as e:
            print(f"Error loading embedded code: {e}")

    def run(self, arguments: Any = None) -> Dict[str, Any]:
        """
        Execute the custom tool

        Args:
            arguments: Input arguments for the tool

        Returns
            Dict containing the result of tool execution
        """
        try:
            if self.execute_function:
                # Use the loaded external function
                result = self.execute_function(
                    arguments if arguments is not None else {}
                )
                return {"success": True, "result": result, "tool_name": self.name}
            else:
                # Fallback to basic processing
                return {
                    "success": False,
                    "error": "No execute_tool function available",
                    "input_received": arguments,
                    "tool_name": self.name,
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "input_received": arguments,
                "tool_name": self.name,
            }
