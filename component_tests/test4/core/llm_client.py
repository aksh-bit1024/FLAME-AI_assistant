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
        self.available_models = self._discover_models()

    def _discover_models(self) -> list[str]:
        try:
            response = self.client.models.list()
            models = getattr(response, "data", response)
            available = []
            for model in models or []:
                model_id = model.get("id") if isinstance(model, dict) else getattr(model, "id", None)
                if model_id:
                    available.append(str(model_id))
            return available
        except Exception as exc:
            print(f"[WARNING] Unable to discover Lemonade models: {exc}")
            return []

    def resolve_model_name(self, target_alias: str) -> str:
        """Resolve an internal target or model hint to an available backend ID."""
        available_models = getattr(self, "available_models", [])
        if not available_models:
            return target_alias

        target = str(target_alias)
        exact_match = next(
            (model for model in available_models if model == target), None
        )
        if exact_match:
            return exact_match

        aliases = {
            "heavy_general": "qwen2.5-14b",
            "coder": "qwen2.5-coder-7b",
            "reasoning": "deepseek-r1-distill-qwen-1.5b",
            "general_default": "gemma4-it-e4b",
            "fast_tool": "gemma4-it-e2b",
        }
        target_lower = target.lower()
        search_terms = [target_lower, aliases.get(target_lower, "")]
        search_terms.extend(
            hint for hint in set(aliases.values()) if hint in target_lower
        )
        for term in search_terms:
            if not term:
                continue
            match = next(
                (model for model in available_models if term in model.lower()), None
            )
            if match:
                return match

        fallback_model = available_models[0]
        print(
            f"[WARNING] Model alias '{target_alias}' not found. "
            f"Falling back to '{fallback_model}'"
        )
        return fallback_model

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
        model = self.resolve_model_name(model)
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