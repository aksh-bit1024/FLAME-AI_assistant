import sys
from core.llm_client import LLMClient
from core.router import ModelRouter

def main():
    print("======================================")
    print("🔥 Welcome to Flame - Router Test 🔥")
    print("======================================")
    print("Type 'exit' or 'quit' to stop.\n")
    
    # Initialize our components
    llm = LLMClient()
    router = ModelRouter(llm)

    chat_history = [
        {"role": "system", "content": "You are Flame, an intelligent local AI assistant."}
    ]

    while True:
        try:
            user_input = input("You: ")
            
            if user_input.lower() in ["exit", "quit"]:
                print("Flame shutting down...")
                break
            
            if not user_input.strip():
                continue

            # 1. Dynamically classify intent and choose the right model
            intent, chosen_model = router.route(user_input)
            print(f"⚙️ [Router] Intent: {intent} --> Model: {chosen_model}")

            # 2. Append user message to history
            chat_history.append({"role": "user", "content": user_input})
            
            # 3. Send request to Lemonade using the dynamically selected model
            response_text = llm.chat(chat_history, model=chosen_model)
            
            print(f"\nFlame: {response_text}\n")
            
            # 4. Save response to history
            chat_history.append({"role": "assistant", "content": response_text})

        except KeyboardInterrupt:
            print("\nFlame shutting down...")
            break

if __name__ == "__main__":
    main()