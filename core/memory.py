from collections import deque
from core.config import load_config

class SessionMemory:
    def __init__(self):
        cfg = load_config()
        self.max_turns = cfg["memory"]["max_turns"]
        self.buffer = deque(maxlen=self.max_turns * 2)

    def add_user(self, text: str):
        self.buffer.append({"role": "user", "content": text})

    def add_assistant(self, text: str):
        self.buffer.append({"role": "assistant", "content": text})

    def context(self) -> str:
        """
        Convert memory to a compact prompt context.
        """
        lines = []
        for msg in self.buffer:
            prefix = "User:" if msg["role"] == "user" else "Daemon:"
            lines.append(f"{prefix} {msg['content']}")
        return "\n".join(lines)

    def clear(self):
        self.buffer.clear()
