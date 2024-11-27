"""Custom exceptions for the AlephBot application."""

class NakdanAPIError(Exception):
    """Raised when there is an error with the Nakdan API."""
    pass

class TextValidationError(Exception):
    """Raised when text validation fails (empty, too long, non-Hebrew)."""
    pass

class CommandError(Exception):
    """Base exception for command-related errors."""
    pass

class CooldownError(CommandError):
    """Raised when a command is on cooldown."""
    pass
