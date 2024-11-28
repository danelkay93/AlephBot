# run.py
"""
File watcher and bot reloader for AlephBot.
Automatically restarts the bot on file changes.
"""
import logging
import sys
import os
import asyncio
from pathlib import Path
from queue import Queue
import signal
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from asyncio.subprocess import Process
from utils.logging_config import configure_logging

# Centralized logging configuration
configure_logging("bot_reloader.log", encoding='utf-8')

logger = logging.getLogger(__name__)

class BotReloader(FileSystemEventHandler):
    """Handles bot process management and file modification detection."""
    def __init__(self, event_queue: Queue):
        self.event_queue = event_queue
        self.process: Process | None = None
        self.restart_lock = asyncio.Lock()

        # Start the bot on initialization
        asyncio.create_task(self.start_bot())

        # Handle termination signals
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)

    def handle_signal(self, signum: int, frame) -> None:
        """Gracefully handle termination signals."""
        logger.info(f"Received signal {signum}. Shutting down...")
        asyncio.create_task(self.cleanup())
        sys.exit(0)

    async def cleanup(self) -> None:
        """Clean up bot process resources."""
        if self.process:
            logger.info("Terminating bot process...")
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Bot process did not terminate in time. Forcing termination...")
                self.process.kill()
                await self.process.wait()

    async def start_bot(self) -> None:
        """Start the bot process asynchronously."""
        await self.cleanup()

        logger.info("Starting bot process...")
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        try:
            self.process = await asyncio.create_subprocess_exec(
                sys.executable,
                "alephbot.py",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            asyncio.create_task(self.monitor_output())

            logger.info("Bot process started successfully.")
        except Exception as e:
            logger.error(f"Failed to start bot process: {e}")
            await self.cleanup()
            raise

    async def monitor_output(self) -> None:
        """Monitor bot process output and log it."""
        if not self.process or not self.process.stdout or not self.process.stderr:
            return

        async def read_stream(stream, level):
            while True:
                line = await stream.readline()
                if not line:
                    break
                msg = line.decode().strip()
                if msg:
                    logger.log(level, msg)

        await asyncio.gather(
            read_stream(self.process.stdout, logging.INFO),
            read_stream(self.process.stderr, logging.ERROR),
        )

    async def handle_modified(self, event: FileModifiedEvent) -> None:
        """Handle file modifications and restart the bot."""
        if not event.src_path.endswith(".py"):
            return

        async with self.restart_lock:
            logger.info(f"Detected file change: {event.src_path}")
            await self.start_bot()

    def on_modified(self, event: FileModifiedEvent) -> None:
        """Handle file modification events and queue them."""
        if any(event.src_path.endswith(file) for file in ["alephbot.py", "utils/config.py"]):
            logger.info(f"Change detected in {event.src_path}")
            self.event_queue.put(event)

async def process_events(event_queue: Queue, reloader: BotReloader) -> None:
    """Process file modification events from the queue."""
    while True:
        try:
            while not event_queue.empty():
                event = event_queue.get_nowait()
                await reloader.handle_modified(event)
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Error processing events: {e}")
            await asyncio.sleep(1)

async def main() -> None:
    """Main function to initialize file watcher and event processing."""
    event_queue: Queue = Queue()
    event_handler = BotReloader(event_queue)
    observer = Observer()

    # Watch the current directory and utils subdirectory
    path = Path.cwd()
    observer.schedule(event_handler, str(path), recursive=False)
    utils_path = path / "utils"
    if utils_path.exists():
        observer.schedule(event_handler, str(utils_path), recursive=False)

    observer.start()

    try:
        await process_events(event_queue, event_handler)
    finally:
        observer.stop()
        await event_handler.cleanup()
        observer.join()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Exiting...")
