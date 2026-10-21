"""Base action definition and interfaces for Flash Agent."""

from abc import ABC, abstractmethod
from typing import Any
from app.models import ActionResponse


class BaseAction(ABC):
    """Abstract base class for all executable agent actions."""

    name: str = ""
    description: str = ""
    requires_confirmation: bool = False
    parameters_schema: dict[str, Any] = {}

    @abstractmethod
    def run(self, parameters: dict[str, Any], confirmed: bool = False) -> ActionResponse:
        """Execute the action with provided parameters and return a structured ActionResponse."""
        pass
