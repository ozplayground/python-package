"""Pydantic v2 structured output parser with markdown fence stripping."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Type, TypeVar
from pydantic import BaseModel, ValidationError

from archon.exceptions import ModelResponseValidationError

T = TypeVar("T", bound=BaseModel)


class StructuredOutputParser:
    """Parses and validates raw LLM output text into strictly typed Pydantic models."""

    @classmethod
    def strip_markdown_fences(cls, raw_text: str) -> str:
        """Strip enclosing markdown code blocks or surrounding text from JSON."""
        trimmed = raw_text.strip()
        # Match ```json ... ``` anywhere in text
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", trimmed, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        # Fallback to outermost { ... } or [ ... ]
        brace_match = re.search(r"(\{.*\}|\[.*\])", trimmed, re.DOTALL)
        if brace_match:
            return brace_match.group(1).strip()
        return trimmed

    @classmethod
    def parse(cls, raw_text: str, response_format: Type[T]) -> T:
        """Parse raw text into a validated Pydantic model instance.

        Raises:
            ModelResponseValidationError: If parsing or schema validation fails.
        """
        if not issubclass(response_format, BaseModel):
            raise TypeError(f"response_format must be a subclass of pydantic.BaseModel, got {response_format}")

        clean_text = cls.strip_markdown_fences(raw_text)

        # Basic JSON syntax check
        try:
            json.loads(clean_text)
        except Exception as e:
            raise ModelResponseValidationError(
                message=f"Model response is not valid JSON: {e}. Content: '{clean_text[:120]}'",
                raw_response=raw_text,
                validation_errors=None,
            ) from e

        try:
            return response_format.model_validate_json(clean_text)
        except ValidationError as e:
            raise ModelResponseValidationError(
                message=f"Model response failed Pydantic schema validation for {response_format.__name__}: {e}",
                raw_response=raw_text,
                validation_errors=e.errors(),
            ) from e

    @classmethod
    def get_strict_json_schema(cls, model_class: Type[BaseModel]) -> Dict[str, Any]:
        """Generate OpenAI strict mode compatible JSON Schema."""
        schema = model_class.model_json_schema()
        schema["additionalProperties"] = False
        return schema
