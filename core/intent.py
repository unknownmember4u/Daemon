import re
import yaml
import os

# Define the absolute path to commands.yaml
COMMANDS_FILE = os.path.join(os.path.dirname(__file__), '..', 'config', 'commands.yaml')

class IntentRecognizer:
    def __init__(self):
        self.commands = self._load_commands()

    def _load_commands(self):
        with open(COMMANDS_FILE, 'r') as f:
            all_commands = yaml.safe_load(f)

        commands = {}
        for intent_group, intent_data in all_commands.items():
            for command_name, command_config in intent_data.items():
                # Construct the full intent_key
                intent_key = f"{intent_group}_{command_name}"

                # Ensure command_config is a dictionary
                if not isinstance(command_config, dict):
                    print(f"Warning: Command '{command_name}' under group '{intent_group}' has an invalid configuration. Skipping.")
                    continue

                pattern = command_config.get("pattern")
                action = command_config.get("action")
                args = command_config.get("args", {})

                if not pattern or not action:
                    print(f"Warning: Command '{command_name}' under group '{intent_group}' is missing 'pattern' or 'action'. Skipping.")
                    continue

                commands[intent_key] = {
                    "pattern": re.compile(pattern, re.IGNORECASE),
                    "action": action,
                    "args": args,
                }
        return commands

    def detect_intent(self, text: str) -> tuple[str, dict]:
        text = text.lower()
        for intent_key, command_data in self.commands.items():
            match = command_data["pattern"].search(text)
            if match:
                extracted_args = match.groupdict()
                # Merge predefined args with extracted args
                final_args = {**command_data["args"], **extracted_args}
                return intent_key, {"action": command_data["action"], "args": final_args}
        return "llm", {}

# Global instance for easy access
intent_recognizer = IntentRecognizer()

def detect_intent(text: str) -> tuple[str, dict]:
    return intent_recognizer.detect_intent(text)
