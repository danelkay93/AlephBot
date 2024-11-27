"""Custom exceptions for the AlephBot application."""

class NakdanAPIError(Exception):
    """Raised when there is an error with the Nakdan API."""
    pass

class TextValidationError(Exception):
    """Raised when text validation fails (empty, too long, non-Hebrew)."""
    def __init__(self, message: str, validation_type: str):
        self.validation_type = validation_type
        super().__init__(message)

class EmptyTextError(TextValidationError):
    """Raised when input text is empty."""
    def __init__(self):
        super().__init__("Text cannot be empty", "empty")

class TextTooLongError(TextValidationError):
    """Raised when input text exceeds maximum length."""
    def __init__(self, max_length: int):
        super().__init__(
            f"Text exceeds maximum length of {max_length} characters",
            "length"
        )

class NonHebrewTextError(TextValidationError):
    """Raised when input text doesn't contain Hebrew characters."""
    def __init__(self):
        super().__init__("Text must contain Hebrew characters", "non_hebrew")

class CommandError(Exception):
    """Base exception for command-related errors."""
    pass

class CooldownError(CommandError):
    """Raised when a command is on cooldown."""
    def __init__(self, retry_after: float):
        self.retry_after = retry_after
        super().__init__(
            f"Please wait {retry_after:.1f} seconds before using this command again"
        )
