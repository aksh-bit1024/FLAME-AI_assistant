import json
import time
import unicodedata
import re

class LLMRouter:
    _CODE_PATTERN = re.compile(
        r"```|\bdef\s+|\bclass\s+|\bimport\s+|\bCustomTkinter\b",
        re.IGNORECASE,
    )
    _HEAVY_MARKER_PATTERN = re.compile(
        r"(?:\bsection\b|\bcompare\b|\bbreakdown\b|\b1\.|\b2\.)",
        re.IGNORECASE,
    )

    def __init__(self, llm_client):
        self.llm = llm_client
        self.router_model = "gemma4-it-e2b-FLM"
        
        self.models = {
            "fast_tool": "gemma4-it-e2b-FLM",
            "general_default": "gemma4-it-e4b-FLM",
            "reasoning": "DeepSeek-R1-Distill-Qwen-1.5B-NPU",
            "coder": "Qwen2.5-Coder-7B-Instruct",
            "instruct_npu": "Qwen2.5-7B-Instruct-NPU",
            "heavy_general": "Qwen2.5-14B-Instruct-Hybrid"
        }

    @staticmethod
    def _sanitize_prompt(prompt: str) -> str:
        """Normalize user text without removing meaningful punctuation or Unicode."""
        normalized = unicodedata.normalize("NFKC", str(prompt))
        return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", normalized).strip()[:200]

    @staticmethod
    def _clean_prompt(prompt: str) -> str:
        normalized = unicodedata.normalize("NFKC", str(prompt))
        return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", normalized).strip()

    def route_with_timing(self, prompt: str) -> tuple[str, float]:
        """
        Uses gemma4-2b as a semantic intent classifier and measures
        classification latency in milliseconds.
        """
        start_time = time.perf_counter()

        clean_prompt = self._clean_prompt(prompt)
        sanitized_prompt = clean_prompt[:200]

        # Use cheap local signals before spending a request on semantic routing.
        if self._CODE_PATTERN.search(clean_prompt):
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return self.models["coder"], elapsed_ms

        if len(clean_prompt) > 350 and self._HEAVY_MARKER_PATTERN.search(clean_prompt):
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return self.models["heavy_general"], elapsed_ms

        # Fast path for slash commands
        if sanitized_prompt.startswith("/"):
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return self.models["fast_tool"], elapsed_ms

        system_instruction = (
            "Classify target: 'coder', 'reasoning', 'heavy_general', or 'general_default'. "
            "JSON only: {\"target\": \"<category>\"}"
        )

        try:
            response = self.llm.chat(
                model=self.router_model,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": sanitized_prompt}
                ],
                max_tokens=20,
                temperature=0.0,
            )
            raw_text = response.choices[0].message.content.strip()
            
            # Extract JSON block
            start = raw_text.find("{")
            end = raw_text.rfind("}") + 1
            if start != -1 and end != 0:
                parsed = json.loads(raw_text[start:end])
                target = parsed.get("target", "general_default")
                chosen_model = self.models.get(target, self.models["general_default"])
            else:
                chosen_model = self.models["general_default"]
        except Exception:
            chosen_model = self.models["general_default"]

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        return chosen_model, elapsed_ms