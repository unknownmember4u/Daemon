from google import genai
from google.genai import types
from core.config import load_config
import os

class GeminiClient:
    def __init__(self):
        cfg = load_config()
        self.api_key = cfg["gemini"].get("api_key")
        
        # fallback to env var if not in config
        if not self.api_key or self.api_key == "YOUR_GEMINI_API_KEY_HERE":
            self.api_key = os.environ.get("GEMINI_API_KEY")

        if self.api_key and self.api_key != "YOUR_GEMINI_API_KEY_HERE":
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None
            
        self.model_name = cfg["gemini"]["model"]
        self.max_tokens = cfg["gemini"]["max_tokens"]

    def generate(self, messages: list[dict]) -> str:
        if not self.client:
            return "Gemini error: API key not configured. Please add it to config slash daemon dot yaml"
        
        try:
            system_instruction = None
            contents = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_instruction = msg["content"]
                elif msg["role"] == "user":
                    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=msg["content"])]))
                elif msg["role"] == "assistant":
                    contents.append(types.Content(role="model", parts=[types.Part.from_text(text=msg["content"])]))
            
            config = types.GenerateContentConfig(
                max_output_tokens=self.max_tokens,
                system_instruction=system_instruction
            )
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config,
            )
            return response.text
        except Exception as e:
            return f"Gemini error: {e}"
