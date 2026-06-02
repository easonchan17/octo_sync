import litellm
from typing import Optional
from functools import cache
from langchain_litellm import ChatLiteLLM
from core.config.config_manager import get_config_manager


class ChatLLMClient:
    def __init__(self, model: str, vision_support: bool, max_tokens: int, temperature: float) -> None:
        self.model          = model
        self.vision_support = vision_support
        self.max_tokens     = max_tokens
        self.temperature    = temperature

    def validate_environment(self) -> None:
        missing_keys = litellm.validate_environment(self.model).get("missing_keys", [])
        if missing_keys:
            raise RuntimeError(f"Missing LLM API key(s) for model '{self.model}': {missing_keys}")

    def build_llm(self) -> ChatLiteLLM:
        return ChatLiteLLM(
            model=self.model,
            max_tokens=self.max_tokens,
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
    )
