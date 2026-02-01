from pathlib import Path

def create_file(path: str, content: str = "") -> str:
    try:
        p = Path(path).expanduser()
        p.write_text(content)
        return f"File created at {p}"
    except Exception as e:
        return f"File error: {e}"

def delete_file(path: str) -> str:
    try:
        p = Path(path).expanduser()
        p.unlink()
        return f"File {p} deleted."
    except Exception as e:
        return f"File error: {e}"
