"""
ToolUniverse Exception Classes

Structured exceptions for tool execution errors with actionable recovery guidance.
"""


class ToolError(Exception):
    """
    Base exception for all tool-related errors.

    Attributes:
        error_type (str): Type of error for classification
        retriable (bool): Whether the operation can be retried
        next_steps (list): Actionable steps to resolve the error
        details (dict): Additional context about the error
    """

    def __init__(
        self, message, error_type=None, retriable=False, next_steps=None, details=None
    ):
        super().__init__(message)
        self.error_type = error_type or self.__class__.__name__
        self.retriable = retriable
        self.next_steps = next_steps or []
        self.details = details or {}

    def to_dict(self):
        """Convert exception to structured dictionary format."""
        return {
            "type": self.error_type,
            "message": str(self),
            "retriable": self.retriable,
            "next_steps": self.next_steps,
            "details": self.details,
        }


class ToolAuthError(ToolError):
    """Authentication or authorization error (missing/invalid API key, permissions)."""

    def __init__(self, message, retriable=False, next_steps=None, details=None):
        if next_steps is None:
            next_steps = [
                "Check API key configuration",
                "Verify environment variables",
                "Review authentication documentation",
            ]
        super().__init__(
            message,
            error_type="ToolAuthError",
            retriable=retriable,
            next_steps=next_steps,
            details=details,
        )


class ToolUnavailableError(ToolError):
    """Tool or service is unavailable (network issues, service down, tool not found)."""

    def __init__(self, message, retriable=True, next_steps=None, details=None):
        if next_steps is None:
            next_steps = [
                "Check network connection",
                "Verify service status",
                "Run tu.tools.refresh() if MCP tool",
                "Check tool name spelling",
            ]
        super().__init__(
            message,
            error_type="ToolUnavailableError",
            retriable=retriable,
            next_steps=next_steps,
            details=details,
        )


class ToolRateLimitError(ToolError):
    """Rate limit or quota exceeded."""

    def __init__(self, message, retriable=True, next_steps=None, details=None):
        if next_steps is None:
            next_steps = [
                "Wait and retry with exponential backoff",
                "Check API quota limits",
                "Use alternative API key if available",
            ]
        super().__init__(
            message,
            error_type="ToolRateLimitError",
            retriable=retriable,
            next_steps=next_steps,
            details=details,
        )


class ToolValidationError(ToolError):
    """Parameter validation failed (invalid parameters, schema mismatch)."""

    def __init__(self, message, retriable=False, next_steps=None, details=None):
        if next_steps is None:
            next_steps = [
                "Check parameter types and values",
                "Review tool documentation",
                "Verify required parameters are provided",
            ]
        super().__init__(
            message,
            error_type="ToolValidationError",
            retriable=retriable,
            next_steps=next_steps,
            details=details,
        )


class ToolConfigError(ToolError):
    """Tool configuration error (missing config, invalid setup)."""

    def __init__(self, message, retriable=False, next_steps=None, details=None):
        if next_steps is None:
            next_steps = [
                "Review tool configuration",
                "Check environment variables",
                "Verify required dependencies are installed",
            ]
        super().__init__(
            message,
            error_type="ToolConfigError",
            retriable=retriable,
            next_steps=next_steps,
            details=details,
        )


class ToolDependencyError(ToolError):
    """Missing or incompatible dependencies."""

    def __init__(self, message, retriable=False, next_steps=None, details=None):
        if next_steps is None:
            next_steps = [
                "Install missing dependencies",
                "Check dependency versions",
                "Review installation documentation",
            ]
        super().__init__(
            message,
            error_type="ToolDependencyError",
            retriable=retriable,
            next_steps=next_steps,
            details=details,
        )


class ToolServerError(ToolError):
    """Server-side error (5xx responses, unexpected failures)."""

    def __init__(self, message, retriable=True, next_steps=None, details=None):
        if next_steps is None:
            next_steps = [
                "Retry the request",
                "Check service status",
                "Report issue if persistent",
            ]
        super().__init__(
            message,
            error_type="ToolServerError",
            retriable=retriable,
            next_steps=next_steps,
            details=details,
        )
