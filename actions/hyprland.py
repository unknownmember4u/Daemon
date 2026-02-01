import subprocess

def _run(cmd: list[str]) -> bool:
    try:
        subprocess.run(
            ["hyprctl"] + cmd,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


def switch_workspace(n: int) -> str:
    if not isinstance(n, int) or n < 1 or n > 10:
        return "Invalid workspace number."
    _run(["dispatch", "workspace", str(n)])
    return f"Switched to workspace {n}."


def close_active_window() -> str:
    _run(["dispatch", "killactive"])
    return "Closed active window."


def focus_next() -> str:
    _run(["dispatch", "cyclenext"])
    return "Focused next window."


def focus_prev() -> str:
    _run(["dispatch", "cycleprev"])
    return "Focused previous window."
