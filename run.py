import sys
import os
import time
import signal
import asyncio
from pathlib import Path
from queue import Queue
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
import asyncio.subprocess
import logging
from typing import Optional
from asyncio.subprocess import Process

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)

# Suppress noisy loggers
logging.getLogger('discord').setLevel(logging.WARNING)
logging.getLogger('watchdog').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

class BotReloader(FileSystemEventHandler):
    def __init__(self, event_queue: Queue):
        self.process: Optional[Process] = None
        self.restart_lock = asyncio.Lock()
        self.event_queue = event_queue
        # Initialize bot in the event loop
        asyncio.create_task(self.start_bot())
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)

    def handle_signal(self, signum: int, frame) -> None:
        """Handle termination signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(self.cleanup())
        sys.exit(0)

    async def cleanup(self) -> None:
        """Clean up resources before shutdown"""
        if self.process:
            logger.info("Terminating bot process...")
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Bot process did not terminate in time, forcing...")
                self.process.kill()
                await self.process.wait()

    async def start_bot(self) -> None:
        """Start the bot process with proper environment"""
        await self.cleanup()
        
        logger.info("Starting bot process...")
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'  # Ensure output is not buffered
        
        self.process = await asyncio.create_subprocess_exec(
            sys.executable,
            "alephbot.py",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        
        # Start output monitoring
        asyncio.create_task(self.monitor_output())

    async def monitor_output(self) -> None:
        """Monitor bot process output and log it"""
        if not self.process or not self.process.stdout or not self.process.stderr:
            return

        async def read_stream(stream, level):
            while True:
                line = await stream.readline()
                if not line:
                    break
                msg = line.decode().strip()
                if msg:
                    if level == logging.ERROR:
                        logger.error("Bot Error: %s", msg)
                    else:
                        logger.info("Bot: %s", msg)

        try:
            # Create tasks to read both streams concurrently
            stdout_task = asyncio.create_task(read_stream(self.process.stdout, logging.INFO))
            stderr_task = asyncio.create_task(read_stream(self.process.stderr, logging.ERROR))
            
            # Wait for process to complete and streams to be fully read
            await self.process.wait()
            await stdout_task
            await stderr_task
            
        except Exception as e:
            logger.error("Error monitoring output: %s", e, exc_info=True)

    async def handle_modified(self, event: FileModifiedEvent) -> None:
        """Handle file modification events with debouncing"""
        if not event.src_path.endswith('.py'):
            return
            
        async with self.restart_lock:  # Prevent multiple simultaneous restarts
            logger.info(f"Detected change in {event.src_path}")
            await self.start_bot()

    def on_modified(self, event: FileModifiedEvent) -> None:
        """Override watchdog's on_modified to queue events"""
        # Only watch specific bot-related files
        watched_files = {
            'alephbot.py',
            str(Path('utils/nakdan_api.py')),
            str(Path('utils/config.py')),
            str(Path('utils/hebrew.py'))
        }
        if any(event.src_path.endswith(file) for file in watched_files):
            logger.info(f"Detected change in watched file: {event.src_path}")
            self.event_queue.put(event)

async def process_events(event_queue: Queue, reloader: BotReloader) -> None:
    """Process file modification events from the queue"""
    while True:
        try:
            # Non-blocking check for events
            while not event_queue.empty():
                event = event_queue.get_nowait()
                await reloader.handle_modified(event)
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Error processing events: {e}")
            await asyncio.sleep(1)

async def main() -> None:
    """Main async function to run the reloader"""
    path = Path.cwd()
    event_queue: Queue = Queue()
    event_handler = BotReloader(event_queue)
    observer = Observer()
    # Watch only the main directory and utils subdirectory
    observer.schedule(event_handler, path=str(path), recursive=False)
    utils_path = path / 'utils'
    if utils_path.exists():
        observer.schedule(event_handler, path=str(utils_path), recursive=False)
    observer.start()

    try:
        # Start event processing task
        event_processor = asyncio.create_task(process_events(event_queue, event_handler))
        
        # Keep main loop running
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        logger.info("Shutting down...")
    finally:
        event_processor.cancel()
        observer.stop()
        event_handler.cleanup()
        observer.join()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, exiting...")
