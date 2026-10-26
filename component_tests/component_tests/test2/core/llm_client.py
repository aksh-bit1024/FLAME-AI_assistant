from openai import OpenAI

class LLMClient:
    # We set the URL to Port 13305 and pick one of your specific Lemonade models
    def __init__(self, base_url="http://localhost:13305/v1", api_key="lemonade-key", default_model="gemma4-it-e4b-FLM"):
        """
        Initializes the connection to the Lemonade inference server.
        """
        # The OpenAI client lets us talk to Lemonade just like we would talk to a cloud AI
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.default_model = default_model

    def chat(self, messages, model=None, temperature=0.7):
        """Sends a list of chat messages to the local AI model."""
        # If we don't ask for a specific model, use the default (Gemma 4)
        target_model = model or self.default_model
        
        try:
            # Send the request to Lemonade and wait for the response
            response = self.client.chat.completions.create(
                model=target_model,
                messages=messages,
                temperature=temperature
            )
            # Return just the text of the AI's answer
            return response.choices[0].message.content
        except Exception as e:
            return f"[Connection Error]: Could not reach Lemonade. Details: {e}"