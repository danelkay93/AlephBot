import sys
import os
import time
import signal
import asyncio
from pathlib import Path
from queue import Queue
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
import subprocess
import logging
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BotReloader(FileSystemEventHandler):
    def __init__(self, event_queue: Queue):
        self.process: Optional[subprocess.Popen] = None
        self.restart_lock = asyncio.Lock()
        self.event_queue = event_queue
        self.start_bot()
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)

    def handle_signal(self, signum: int, frame) -> None:
        """Handle termination signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.cleanup()
        sys.exit(0)

    def cleanup(self) -> None:
        """Clean up resources before shutdown"""
        if self.process:
            logger.info("Terminating bot process...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)  # Give it 5 seconds to terminate gracefully
            except subprocess.TimeoutExpired:
                logger.warning("Bot process did not terminate in time, forcing...")
                self.process.kill()  # Force kill if it doesn't terminate
                self.process.wait()

    def start_bot(self) -> None:
        """Start the bot process with proper environment"""
        self.cleanup()
        
        logger.info("Starting bot process...")
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'  # Ensure output is not buffered
        
        self.process = subprocess.Popen(
            [sys.executable, "alephbot.py"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Start output monitoring
        asyncio.create_task(self.monitor_output())

    async def monitor_output(self) -> None:
        """Monitor bot process output and log it"""
        if not self.process:
            return
            
        while True:
            if self.process.poll() is not None:  # Process has terminated
                break
                
            output = self.process.stdout.readline()
            if output:
                logger.info(f"Bot: {output.strip()}")
            
            error = self.process.stderr.readline()
            if error:
                logger.error(f"Bot Error: {error.strip()}")
            
            await asyncio.sleep(0.1)

    async def handle_modified(self, event: FileModifiedEvent) -> None:
        """Handle file modification events with debouncing"""
        if not event.src_path.endswith('.py'):
            return
            
        async with self.restart_lock:  # Prevent multiple simultaneous restarts
            logger.info(f"Detected change in {event.src_path}")
            self.start_bot()

    def on_modified(self, event: FileModifiedEvent) -> None:
        """Override watchdog's on_modified to queue events"""
        if event.src_path.endswith('.py'):
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
    observer.schedule(event_handler, path=str(path), recursive=True)
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
