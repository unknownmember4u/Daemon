import requests
from core.config import load_config

class OllamaClient:
    def __init__(self):
        cfg = load_config()
        self.url = f"{cfg['ollama']['host']}/api/chat"
        self.model = cfg["ollama"]["model"]
        self.timeout = cfg["ollama"]["timeout"]
        self.max_tokens = cfg["ollama"]["max_tokens"]

    def generate(self, messages: list[dict]) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_predict": self.max_tokens
            }
        }

        try:
            r = requests.post(
                self.url,
                json=payload,
                timeout=self.timeout,
            )
            r.raise_for_status()
            data = r.json()
            return data.get("message", {}).get("content", "").strip()
        except requests.RequestException as e:
            return f"[LLM error: {e}]"
