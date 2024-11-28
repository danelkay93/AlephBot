# utils/logging_config.py
"""
Centralized logging configuration for the bot project.
"""
import logging
import sys

def configure_logging(log_file: str = 'bot.log', level: int = logging.DEBUG) -> None:
    """Configure centralized logging for the bot."""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding='utf-8'),
        ]
    )

    # Suppress noisy loggers
    noisy_loggers = [
        'httpx', 'httpcore', 'websockets', 'asyncio', 'aiohttp',
        'watchdog', 'discord.http', 'discord.gateway'
    ]
    for logger_name in noisy_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)
        logger.propagate = False

    # Reduce verbosity for Discord logs
    discord_logger = logging.getLogger('discord')
    discord_logger.setLevel(logging.WARNING)
