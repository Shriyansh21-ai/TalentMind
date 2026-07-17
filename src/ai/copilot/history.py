"""Conversation history for the Recruiter Copilot."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.ai.copilot.models import Message


@dataclass
class ConversationHistory:
    """An ordered log of conversation messages."""

    messages: list[Message] = field(default_factory=list)

    def add_user(self, content: str) -> None:
        """Append a recruiter message."""
        self.messages.append(Message(role="user", content=content))

    def add_assistant(self, content: str) -> None:
        """Append a copilot message."""
        self.messages.append(Message(role="assistant", content=content))

    def recent(self, limit: int = 10) -> list[Message]:
        """Return the most recent ``limit`` messages."""
        return self.messages[-limit:]

    def __len__(self) -> int:
        return len(self.messages)
