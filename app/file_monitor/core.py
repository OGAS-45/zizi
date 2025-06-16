from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import os

class FileWatcher(threading.Thread):
    def __init__(self, processor, folder_path):
        super().__init__(daemon=True)
        self.processor = processor
        self.folder_path = folder_path
        self.observer = Observer()
        self.running = True
        
    def run(self):
        event_handler = Handler(self.processor)
        self.observer.schedule(event_handler, self.folder_path, recursive=True)
        self.observer.start()
        while self.running:
            pass
            
class Handler(FileSystemEventHandler):
    def __init__(self, processor):
        self.processor = processor
        
    def on_modified(self, event):
        if not event.is_directory:
            print(f"检测到文件更新: {event.src_path}")
            self.processor._batch_process_markdown(os.path.dirname(event.src_path))