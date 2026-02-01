import time
import inspect
import importlib
import os

from core.config import load_config
from core.intent import IntentRecognizer
from core.memory import SessionMemory

from voice.wake_word import WakeWordListener
from voice.stt_vosk import SpeechToText

from ai.ollama_client import OllamaClient

# TTS (piper)
from voice.tts_piper import PiperTTS


class DaemonAssistant:
    def __init__(self):
        self.cfg = load_config()

        # Audio + AI components
        self.wake = WakeWordListener()
        self.stt = SpeechToText()
        self.tts = PiperTTS()
        self.llm = OllamaClient()
        self.memory = SessionMemory()
        self.intent_recognizer = IntentRecognizer()

        # Assistant identity
        self.name = self.cfg["assistant"]["name"]
        self.ack = self.cfg["assistant"]["response_ack"]
        self.wake_word = self.cfg["assistant"]["wake_word"].lower()
        self.system_prompt = self.cfg["assistant"]["system_prompt"]

        # Wake state control
        self.last_wake_time = 0.0
        self.wake_cooldown = 3.0  # seconds
        self.is_speaking = False

        # Dynamically load actions
        self.actions = self._load_actions()

    def _load_actions(self):
        actions_dir = os.path.join(os.path.dirname(__file__), "actions")
        loaded_actions = {}
        for filename in os.listdir(actions_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = filename[:-3]
                module = importlib.import_module(f"actions.{module_name}")
                for name, func in inspect.getmembers(module, inspect.isfunction):
                    loaded_actions[f"{module_name}_{name}"] = func
        return loaded_actions

    def respond(self, text: str):
        if not text:
            return
        self.is_speaking = True
        self.tts.speak(text)
        self.is_speaking = False
        self.memory.add_assistant(text)

    def handle_intent(self, text: str) -> str:
        intent_key, action_data = self.intent_recognizer.detect_intent(text)

        if intent_key == "llm":
            self.memory.add_user(text)
            # Construct messages in a structured format for the LLM
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(list(self.memory.buffer)) # Add conversational memory
            messages.append({"role": "user", "content": text})

            # Instead of a single prompt string, pass a list of messages to OllamaClient
            # This requires a change in OllamaClient.generate to accept messages
            return self.llm.generate(messages)
        
        action_func_key = action_data["action"]

        action_func = self.actions.get(action_func_key)

        if action_func:
            try:
                args = action_data.get("args", {})
                # Filter args to only include those accepted by the function
                sig = inspect.signature(action_func)
                filtered_args = {k: v for k, v in args.items() if k in sig.parameters}
                
                # If there's a single non-keyword argument expected and it's not in filtered_args,
                # try to pass the first value from args directly. This handles cases like
                # open_app('firefox') where 'firefox' is not a named arg.
                if len(sig.parameters) == 1 and not list(sig.parameters.values())[0].kind == inspect.Parameter.VAR_KEYWORD:
                    param_name = list(sig.parameters.keys())[0]
                    if param_name not in filtered_args and args:
                        first_arg_value = next(iter(args.values()))
                        filtered_args[param_name] = first_arg_value


                # Attempt type conversion for arguments
                converted_args = {}
                for param_name, param_value in filtered_args.items():
                    param_type = sig.parameters[param_name].annotation
                    try:
                        if param_type is int:
                            converted_args[param_name] = int(param_value)
                        elif param_type is float:
                            converted_args[param_name] = float(param_value)
                        else:
                            converted_args[param_name] = param_value
                    except (ValueError, TypeError):
                        return f"Invalid type for argument '{param_name}'. Expected {param_type.__name__}."
                                
                result = action_func(**converted_args)
                return str(result)
            except Exception as e:
                return f"I encountered an error while trying to {func_name}."
        else:
            return "I don't know how to perform that action yet."

    def run(self):
        print(f"{self.name} is running. Say 'hey daemon' to begin.")
        
        while True:
            print("DEBUG: Waiting for wake word...")
            # ===== IDLE: wait for wake word =====
            self.wake.wait()
            
            now = time.time()
            if now - self.last_wake_time < self.wake_cooldown:
                continue
            self.last_wake_time = now
            
            # Acknowledge wake
            self.is_speaking = True
            self.tts.speak(self.ack)
            self.is_speaking = False
            
            # Short pause to avoid speaker->mic echo
            time.sleep(0.5)
            
            # ===== COMMAND LISTEN =====
            text = self.stt.listen_once()
            
            # ❗ CRITICAL FIX: if no command, go silent and idle
            if not text or not text.strip():
                continue
            
            text_l = text.lower()
            
            # Ignore wake-only speech
            if self.wake_word in text_l and len(text_l.split()) <= 2:
                continue
            
            # Handle real command
            response = self.handle_intent(text)
            self.respond(response)


if __name__ == "__main__":
    DaemonAssistant().run()
