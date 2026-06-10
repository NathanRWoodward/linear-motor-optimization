import time
import importlib
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Preload this so it doesn't get reloaded on every change
from build123d import *
from ocp_vscode import show, show_clear
import os
from rich.console import Console
from rich import print

console = Console()

# def my_project_entrypoint():
#     os.system("cls" if os.name == "nt" else "clear")
#     print("Running my project entrypoint...")

#     importlib.reload(workbench    )

#     workbench .test()
#     print("Finished running entrypoint.")


# # if __name__ == "__main__":
# #     show_clear()
# #     # This monitors the current directory ('.') and re-runs the entrypoint function on changes
# #     run_process("./src/optimize", target=my_project_entrypoint)


import workbench


class CodeReloaderHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        # Keep track of exactly when the last reload happened
        self.last_reload_time = 0
        self.debounce_window = 1.0

    def on_modified(self, event):
        if event.is_directory or not event.src_path.endswith(".py"):
            return

        if "__pycache__" in event.src_path:
            return

        current_time = time.time()
        if (current_time - self.last_reload_time) < self.debounce_window:
            return  # Drop the duplicate event silently
        self.last_reload_time = current_time

        os.system("cls" if os.name == "nt" else "clear")
        changed_file = os.path.relpath(event.src_path)
        print(f"[cyan][Hot Reload][/cyan] [yellow]{changed_file}[/yellow]")
        console

        try:
            self.run()
        except Exception:
            console.print_exception(width=400, extra_lines=3, suppress=[__file__])

    def run(self):
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
        print(f"[cyan][Hot Reload][/cyan] Done in {time.time() - start:.4f} seconds!")


if __name__ == "__main__":
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
