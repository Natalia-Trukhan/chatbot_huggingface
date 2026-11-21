from pathlib import Path
from typing import Final
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM


class ConversationHistory:
    # Maximum number of messages kept before trimming older middle messages
    MAX_HISTORY_MESSAGES: Final[int] = 50
    # Number of initial messages preserved from the start of the chat
    START_HISTORY_MESSAGES: Final[int] = 6
    # Number of most recent messages preserved at the end of the chat
    END_HISTORY_MESSAGES: Final[int] = 10

    def __init__(self, prompt_path: str = "system_prompt.txt") -> None:
        # Load the system instruction from file
        self.SYSTEM_PROMPT: Final[str] = Path(prompt_path).read_text(encoding="utf-8")
        self.messages: list[dict[str, str]] = []

    def _trim_history(self) -> None:
        # Keep the beginning and the tail of the conversation when limit is exceeded
        if len(self.messages) > self.MAX_HISTORY_MESSAGES:
            start_part = self.messages[:self.START_HISTORY_MESSAGES]
            end_part = self.messages[-self.END_HISTORY_MESSAGES:]
            self.messages = start_part + end_part

    def add_request(self, user_text: str) -> None:
        # Append a new user message to history
        self.messages.append({"role": "user", "content": user_text})
        self._trim_history()

    def add_response(self, assistant_text: str) -> None:
        # Append an assistant reply and trim if needed
        self.messages.append({"role": "assistant", "content": assistant_text})
        self._trim_history()

    def get_messages(self) -> list[dict[str, str]]:
        # Prepend system prompt to the current chat history
        return [{"role": "system", "content": self.SYSTEM_PROMPT}, *self.messages]

    def pop_last_message(self) -> None:
        # Remove the last message if generation failed
        if self.messages:
            self.messages.pop()


class Bot:
    MODEL_NAME: str = "Qwen/Qwen3-1.7B"

    def __init__(self) -> None:
        self.history = ConversationHistory("system_prompt.txt")
        # Use GPU if CUDA is available, otherwise fall back to CPU
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Пристрій обчислень: {self.device}")
        print("Завантаження моделі та токенізатора...")

        self.tokenizer = AutoTokenizer.from_pretrained(self.MODEL_NAME)
        self.model = AutoModelForCausalLM.from_pretrained(self.MODEL_NAME)
        self.model.to(self.device)
        # Switch model to evaluation mode for inference
        self.model.eval()

    def generate_response(self, user_text: str) -> str:
        self.history.add_request(user_text)
        prepared_messages = self.history.get_messages()

        # Format messages using the model's chat template
        inputs = self.tokenizer.apply_chat_template(
            prepared_messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        )
        inputs = inputs.to(self.device)

        # Disable gradient tracking to save memory during inference
        with torch.inference_mode():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=3000,
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id,
            )

        # Slice off input tokens to keep only newly generated ones
        input_len = inputs["input_ids"].shape[-1]
        new_tokens = outputs[0][input_len:]
        response = self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

        self.history.add_response(response)
        return response