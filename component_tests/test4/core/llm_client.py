import re
from importlib import import_module

STRICT_SYSTEM_PROMPT = (
    "You are an expert technical assistant. Answer the user's prompt directly, thoroughly, "
    "and completely according to all structural requirements. Do not provide study guides, "
    "meta-commentary, or instructions on how to read the prompt."
)

class LLMClient:
    def __init__(self, base_url: str = "http://localhost:8000/v1", api_key: str = "local"):
        openai = import_module("openai")
        self.client = openai.OpenAI(base_url=base_url, api_key=api_key)

    def chat(
        self,
        model: str,
        messages: list,
        tools: list = None,
        temperature: float = None,
        max_tokens: int = None,
        stop: list[str] = None,
    ):
        """
        Executes chat completion with dynamic model selection and 
        DeepSeek reasoning tag sanitization.
        """
        prepared_messages = list(messages)
        if not (
            prepared_messages
            and prepared_messages[0].get("role") == "system"
            and prepared_messages[0].get("content") == STRICT_SYSTEM_PROMPT
        ):
            prepared_messages.insert(
                0,
                {"role": "system", "content": STRICT_SYSTEM_PROMPT},
            )

        kwargs = {
            "model": model,
            "messages": prepared_messages,
        }

        # Keep standard OpenAI message objects and stop Qwen models at ChatML boundaries.
        if "qwen" in model.lower():
            kwargs.update(
                temperature=0.7 if temperature is None else temperature,
                max_tokens=1500 if max_tokens is None else max_tokens,
                stop=stop or ["<|im_end|>", "<|endoftext|>", "<|im_start|>"],
            )
        else:
            if temperature is not None:
                kwargs["temperature"] = temperature
            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens
            if stop is not None:
                kwargs["stop"] = stop
        
        # Only pass tools schema if provided
        if tools:
            kwargs["tools"] = tools

        response = self.client.chat.completions.create(**kwargs)
        
        # Sanitize <think> tags from DeepSeek R1 outputs
        msg = response.choices[0].message
        if msg.content and "<think>" in msg.content:
            msg.content = re.sub(r"<think>.*?(?:</think>|$)", "", msg.content, flags=re.DOTALL).strip()

        return response