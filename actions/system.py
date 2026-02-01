import psutil

def cpu_usage() -> str:
    percent = psutil.cpu_percent(interval=1)
    return f"CPU usage is {percent}%."

def memory_usage() -> str:
    mem = psutil.virtual_memory()
    return f"Memory usage is {mem.percent}%."

import subprocess

def open_app(command: str) -> str:
    if not command:
        return "No application specified."
    try:
        subprocess.Popen(
            [command],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return f"Opened {command}."
    except FileNotFoundError:
        return f"Application '{command}' not found."
    except Exception as e:
        return f"Failed to open application: {e}"


def open_url(url: str) -> str:
    try:
        subprocess.Popen(
            ["xdg-open", url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return f"Opened {url}."
    except Exception as e:
        return f"Failed to open URL: {e}"
