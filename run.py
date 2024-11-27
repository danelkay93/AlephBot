import sys
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BotReloader(FileSystemEventHandler):
    def __init__(self):
        self.process = None
        self.start_bot()

    def start_bot(self):
        if self.process:
            self.process.terminate()
            self.process.wait()
        
        logger.info("Starting bot process...")
        self.process = subprocess.Popen([sys.executable, "alephbot.py"])

    def on_modified(self, event):
        if event.src_path.endswith('.py'):
            logger.info(f"Detected change in {event.src_path}")
            self.start_bot()

def main():
    path = Path.cwd()
    event_handler = BotReloader()
    observer = Observer()
    observer.schedule(event_handler, path=str(path), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        if event_handler.process:
            event_handler.process.terminate()
    observer.join()

if __name__ == "__main__":
    main()
