from pathlib import Path
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from core import ConversationHistory
from web_search import WebSearch


class BotWeb:
    MODEL_NAME: str = "google/gemma-3-4b-it"

    def __init__(self) -> None:
        self.history = ConversationHistory("system_prompt_web.txt")
        # Load prompt template used when attaching search results
        self.web_prompt: str = Path("web_prompt.txt").read_text(encoding="utf-8")
        self.web_search = WebSearch()

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Пристрій обчислень: {self.device}")
        print(f"Завантаження моделі {self.MODEL_NAME}...")

        self.tokenizer = AutoTokenizer.from_pretrained(self.MODEL_NAME)
        self.model = AutoModelForCausalLM.from_pretrained(self.MODEL_NAME)
        self.model.to(self.device)
        self.model.eval()

    def _build_user_message_with_search(self, user_text: str) -> str:
        # Search the web and fetch page text when available
        results = self.web_search.search(user_text)
        if not results:
            return (
                f"Запит користувача: {user_text}\n\n"
                "Результати пошуку в інтернеті відсутні або нічого не знайдено."
            )

        blocks: list[str] = []
        for idx, item in enumerate(results, start=1):
            page_text = self.web_search.read_page(item["url"])
            # Fall back to search snippet if full page text is unavailable
            excerpt = page_text if page_text else item["snippet"]
            blocks.append(
                f"[{idx}] Заголовок: {item['title']}\n"
                f"URL: {item['url']}\n"
                f"Опис: {item['snippet']}\n"
                f"Текст: {excerpt}"
            )

        sources_text = "\n\n".join(blocks)
        return (
            f"Запит користувача: {user_text}\n\n"
            f"{self.web_prompt}\n\n"
            f"Вебматеріали:\n{sources_text}"
        )

    def generate_response(self, user_text: str) -> str:
        # Add user query together with web search context as a user message
        enriched_user_msg = self._build_user_message_with_search(user_text)
        self.history.add_request(enriched_user_msg)
        prepared_messages = self.history.get_messages()

        inputs = self.tokenizer.apply_chat_template(
            prepared_messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        )
        inputs = inputs.to(self.device)

        # Some chat models don't define a dedicated pad_token_id
        pad_id = self.tokenizer.pad_token_id
        if pad_id is None:
            pad_id = self.tokenizer.eos_token_id

        with torch.inference_mode():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=3000,
                do_sample=False,
                pad_token_id=pad_id,
            )

        input_len = inputs["input_ids"].shape[-1]
        new_tokens = outputs[0][input_len:]
        response = self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

        self.history.add_response(response)
        return response