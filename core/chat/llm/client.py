import litellm
from typing import Optional
from functools import cache
from langchain_litellm import ChatLiteLLM
from core.config.config_manager import get_config_manager


class ChatLLMClient:
    def __init__(self, model: str, vision_support: bool, max_tokens: int, temperature: float, max_context_tokens: int, max_tokens_per_hour: int, max_tokens_per_day: int) -> None:
        self.model               = model
        self.vision_support      = vision_support
        self.max_tokens          = max_tokens
        self.temperature         = temperature
        self.max_context_tokens  = max_context_tokens
        self.max_tokens_per_hour = max_tokens_per_hour
        self.max_tokens_per_day  = max_tokens_per_day

    def validate_environment(self) -> None:
        missing_keys = litellm.validate_environment(self.model).get("missing_keys", [])
        if missing_keys:
            raise RuntimeError(f"Missing LLM API key(s) for model '{self.model}': {missing_keys}")

    def build_llm(self, max_tokens: Optional[int] = None) -> ChatLiteLLM:
        return ChatLiteLLM(
            model=self.model,
            max_tokens=max_tokens or self.max_tokens,
            temperature=self.temperature,
            streaming=True,
        )

    def build_content(self, text: str, image_b64: Optional[str] = None) -> list:
        content = [{"type": "text", "text": text}]
        if image_b64:
            if self.vision_support:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_b64}"}
                })
            else:
                content[0]["text"] += "\n[用户附带了截图，请引导用户用文字补充描述图片内容]"

        return content


@cache
def get_chat_llm_client() -> ChatLLMClient:
    config_manager = get_config_manager()
    config = {
        **config_manager.get_config('llm.default', {}),
        **config_manager.get_config('llm.chat', {}),
    }

    return ChatLLMClient(
        model=f"{config['provider']}/{config['model']}",
        vision_support=config['vision_support'],
        max_tokens=config['max_tokens'],
        temperature=config['temperature'],
        max_context_tokens=config['max_context_tokens'],
        max_tokens_per_hour=config['max_tokens_per_hour'],
        max_tokens_per_day=config['max_tokens_per_day'],
    )
