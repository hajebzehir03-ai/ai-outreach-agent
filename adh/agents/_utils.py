"""Shared utilities for agents."""
from anthropic.types import Message, TextBlock


def extract_text(response: Message) -> str:
    """
    Extract concatenated text from an Anthropic API response.

    Anthropic responses contain blocks of different types (TextBlock, ToolUseBlock,
    ThinkingBlock, etc.) — only TextBlock has a `.text` attribute. This helper
    filters and concatenates them safely.

    Raises:
        ValueError: if no TextBlock is found in the response.
    """
    text_parts = [
        block.text for block in response.content
        if isinstance(block, TextBlock)
    ]
    if not text_parts:
        raise ValueError(
            f"No TextBlock found in response. Got: "
            f"{[type(b).__name__ for b in response.content]}"
        )
    return "".join(text_parts)
