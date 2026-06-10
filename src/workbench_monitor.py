import time
import importlib
import sys
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Preload this so it doesn't get reloaded on every change
from build123d import *
from ocp_vscode import ignore_camera_warnings, set_defaults, set_port, show, show_clear
import os
from rich.console import Console
from rich import print

console = Console()


import workbench


class CodeReloaderHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        # Keep track of exactly when the last reload happened
        self.last_reload_time = 0
        self.debounce_window = 2.0
        self._running = False

    def on_modified(self, event):
        if event.is_directory or not event.src_path.endswith(".py"):
            return

        if "__pycache__" in event.src_path:
            return

        current_time = time.time()
        if (current_time - self.last_reload_time) < self.debounce_window:
            return  # Drop the duplicate event silently
        self.last_reload_time = current_time

        if self._running:
            return  # A run is already in progress

        os.system("cls" if os.name == "nt" else "clear")
        changed_file = os.path.relpath(event.src_path)
        print(f"[cyan][Hot Reload][/cyan] [yellow]{changed_file}[/yellow]")

        threading.Thread(target=self.run, daemon=True).start()

    def run(self):
        self._running = True
        try:
            start = time.time()
            modules = list(sys.modules.keys())
            modules_to_purge = [
                name
                for name in modules
                if name == "workbench" or name.startswith("optimize")
            ]

            for mod_name in modules_to_purge:
                # print(f"Purging module: {mod_name}")
                del sys.modules[mod_name]  # Forcibly evicts it from memory

            import workbench

            importlib.reload(workbench)
            workbench.main()
            print(
                f"[cyan][Hot Reload][/cyan] Done in {time.time() - start:.4f} seconds!"
            )
        except Exception:
            console.print_exception(width=400, extra_lines=3, suppress=[__file__])
        finally:
            self._running = False


if __name__ == "__main__":

    set_port(3939, host="127.0.0.1")
    set_defaults(
        deviation=0.5,  # Default is ~0.1 (Max chordal error)
        angular_tolerance=0.5,  # Default is ~0.1 (Curve smoothness)
        edge_accuracy=0.8,  # Lowers precision of rendered edge lines
        tree_width=300,
        black_edges=False,
        render_edges=False,
    )
    ignore_camera_warnings()

    reloader = CodeReloaderHandler()

    observer = Observer()
    observer.schedule(reloader, path="./src", recursive=True)
    observer.start()

    reloader.run()  # Run once at startup to display the initial design

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
