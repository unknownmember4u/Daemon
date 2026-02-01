import subprocess
from core.config import load_config

def run_command(cmd: list[str]) -> str:
    cfg = load_config()
    blocked = cfg["security"]["blocked_commands"]

    if not cmd:
        return "No command provided."

    if cmd[0] in blocked:
        return f"Command '{cmd[0]}' is blocked."

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        output = result.stdout.strip() or result.stderr.strip()
        return output or "Command executed."
    except Exception as e:
        return f"Execution error: {e}"
