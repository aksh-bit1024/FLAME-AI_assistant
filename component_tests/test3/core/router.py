class ModelRouter:
    def __init__(self, llm_client):
        self.llm = llm_client
        
        # Map semantic intents directly to your Lemonade model names
        self.model_mapping = {
            "CODING": "Qwen2.5-Coder-7B-Instruct-Hybrid",
            "SCHEDULE": "gemma4-it-e4b-FLM",
            "FILE_MGMT": "gemma4-it-e4b-FLM",
            "GENERAL": "gemma4-it-e4b-FLM"
        }
        self.default_model = "gemma4-it-e4b-FLM"

    def route(self, user_prompt):
        """
        Flexibly classifies user intent using the LLM instead of rigid keyword matching.
        Returns a tuple of (detected_intent, target_model_name).
        """
        # A quick system prompt to force the model to act as a classifier
        classification_messages = [
            {
                "role": "system", 
                "content": (
                    "You are an intent classifier for an AI assistant. "
                    "Read the user prompt and categorize it into one of these exact words: "
                    "CODING (for writing code, debugging, algorithms, or math), "
                    "SCHEDULE (for calendar, meetings, reminders, or time management), "
                    "FILE_MGMT (for organizing, finding, or moving local files), "
                    "GENERAL (for general conversation, questions, or text processing). "
                    "Reply with ONLY the category word in uppercase, nothing else."
                )
            },
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            # Ask the model to classify with low temperature for stability
            response = self.llm.chat(classification_messages, temperature=0.1)
            intent = response.strip().upper()
            
            # Pick the model mapped to that intent, fallback to default if unknown
            target_model = self.model_mapping.get(intent, self.default_model)
            return intent, target_model
            
        except Exception:
            # Fallback if classification fails
            return "GENERAL", self.default_model