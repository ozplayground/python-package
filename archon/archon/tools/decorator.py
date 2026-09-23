"""Declarative @tool decorator and FunctionTool wrapper."""
import inspect
from typing import Any, Callable, Dict, List, Optional
from archon.tools.base import BaseTool
from archon.tools.result import ToolExecutionResult


def _py_type_to_json_type(py_type: Any) -> str:
    """Map python type annotation to JSON schema type."""
    if py_type in (int,):
        return "integer"
    if py_type in (float,):
        return "number"
    if py_type in (str,):
        return "string"
    if py_type in (bool,):
        return "boolean"
    if py_type in (list, List):
        return "array"
    if py_type in (dict, Dict):
        return "object"
    return "string"


class FunctionTool(BaseTool):
    """Wrapper that turns a standard Python function into an Archon BaseTool."""

    func: Callable[..., Any]

    def __init__(
        self,
        func: Callable[..., Any],
        name: Optional[str] = None,
        description: Optional[str] = None,
        parameters_schema: Optional[Dict[str, Any]] = None,
    ) -> None:
        tool_name = name or func.__name__
        tool_desc = description or (inspect.getdoc(func) or "").strip()

        schema = parameters_schema or self._generate_schema(func)
        super().__init__(
            func=func,
            name=tool_name,
            description=tool_desc,
            parameters_schema=schema,
        )

    def _generate_schema(self, func: Callable[..., Any]) -> Dict[str, Any]:
        """Generate JSON schema from function signature and type annotations."""
        sig = inspect.signature(func)
        properties: Dict[str, Any] = {}
        required: List[str] = []

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue

            param_type = _py_type_to_json_type(param.annotation)
            properties[param_name] = {
                "type": param_type,
                "description": f"Parameter {param_name}",
            }

            if param.default is inspect.Parameter.empty:
                required.append(param_name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    def execute(self, **kwargs: Any) -> ToolExecutionResult:
        """Call the underlying function and return a ToolExecutionResult."""
        try:
            res = self.func(**kwargs)
            return ToolExecutionResult(
                exit_code=0,
                stdout=str(res) if res is not None else "",
                stderr="",
                error=None,
            )
        except Exception as e:
            return ToolExecutionResult(
                exit_code=1,
                stdout="",
                stderr="",
                error=str(e),
            )

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Allow calling the function directly."""
        return self.func(*args, **kwargs)


def tool(
    func_or_name: Optional[Any] = None,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> Any:
    """Decorator to declare an agent tool from a Python function."""

    def decorator(fn: Callable[..., Any]) -> FunctionTool:
        tool_name = name or (func_or_name if isinstance(func_or_name, str) else None)
        return FunctionTool(
            func=fn,
            name=tool_name,
            description=description,
        )

    if callable(func_or_name):
        return FunctionTool(func=func_or_name, name=name, description=description)

    return decorator
