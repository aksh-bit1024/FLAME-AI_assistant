import sys
from core.llm_client import LLMClient

def main():
    print("======================================")
    print("🔥 Welcome to Flame - Core Chat Test 🔥")
    print("======================================")
    print("Type 'exit' or 'quit' to stop.\n")
    
    # Create our connection to Lemonade
    llm = LLMClient() 

    # This list acts as Flame's short-term memory buffer
    chat_history = [
        {"role": "system", "content": "You are Flame, an intelligent local AI assistant."}
    ]

    # Start an infinite loop to keep the chat going
    while True:
        try:
            # Get input from the keyboard
            user_input = input("You: ")
            
            # Check if the user wants to leave
            if user_input.lower() in ["exit", "quit"]:
                print("Flame shutting down...")
                break
            
            # If they just pressed Enter with no text, skip to the next loop
            if not user_input.strip():
                continue

            # 1. Save what you typed into the history
            chat_history.append({"role": "user", "content": user_input})
            
            # 2. Get the response from the local model running in Lemonade
            response_text = llm.chat(chat_history)
            
            print(f"\nFlame: {response_text}\n")
            
            # 3. Save Flame's response into the history so it remembers the context
            chat_history.append({"role": "assistant", "content": response_text})

        except KeyboardInterrupt:
            # This catches the CTRL+C command to exit gracefully
            print("\nFlame shutting down...")
            break

if __name__ == "__main__":
    main()