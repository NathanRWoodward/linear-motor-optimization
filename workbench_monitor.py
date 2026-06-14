import os
from types import ModuleType

os.environ["NATIVE_TESSELLATOR"] = "1"
# Preload this so it doesn't get reloaded on every change
from ocp_vscode import ignore_camera_warnings, set_defaults, set_port
from build123d import *
import time
import importlib
import sys
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from rich.console import Console
from rich import print

console = Console()


class CodeReloaderHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        # Keep track of exactly when the last reload happened
        self.last_reload_time = 0
        self.debounce_window = 2.0
        self._running = False

    def on_modified(self, event):
        full_path = os.path.abspath(event.src_path)
        if event.is_directory or not full_path.endswith(".py"):
            return

        if "__pycache__" in full_path or full_path == __file__:
            return

        current_time = time.time()
        if (current_time - self.last_reload_time) < self.debounce_window:
            return  # Drop the duplicate event silently
        self.last_reload_time = current_time

        if self._running:
            return  # A run is already in progress

        os.system("cls" if os.name == "nt" else "clear")

        changed_file = os.path.relpath(full_path)
        print(f"[cyan][Hot Reload][/cyan] [yellow]{changed_file}[/yellow]")

        threading.Thread(target=self.run, daemon=True).start()

    def _include_module(self, module: ModuleType) -> bool:
        # Only include modules that are part of our project (in our source directory)
        path = getattr(module, "__file__", "")
        if not path:
            return False
        if "site-packages" in path or "dist-packages" in path:
            return False
        if not path.startswith(os.path.abspath("./src")):
            return False

        if module.__name__ == "__main__":
            return False

        return True

    def run(self):
        self._running = True
        try:
            start = time.time()
            modules_to_purge = [module for module in sys.modules.values() if self._include_module(module)]

            for mod_name in modules_to_purge:
                # print(f"Purging module: {mod_name.__name__}")
                del sys.modules[mod_name.__name__]  # Forcibly evicts it from memory

            import workbench

            importlib.reload(workbench)
            workbench.main()
            print(f"[cyan][Hot Reload][/cyan] Done in {time.time() - start:.4f} seconds!")
        except Exception:
            console.print_exception(width=400, extra_lines=3, suppress=[__file__])
        finally:
            self._running = False


if __name__ == "__main__":
    os.system("cls" if os.name == "nt" else "clear")

    set_port(3939, host="127.0.0.1")
    set_defaults(
        deviation=0.5,  # Default is ~0.1 (Max chordal error)
        angular_tolerance=0.5,  # Default is ~0.1 (Curve smoothness)
        edge_accuracy=0.8,  # Lowers precision of rendered edge lines
        tree_width=300,
        black_edges=False,
    )
    ignore_camera_warnings()

    reloader = CodeReloaderHandler()

    observer = Observer()
    observer.schedule(reloader, path="./src", recursive=True)
    observer.schedule(reloader, path=".", recursive=False)
    observer.start()

    reloader.run()  # Run once at startup to display the initial design

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
