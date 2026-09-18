import sys
from pathlib import Path

# Force current folder into sys.path
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR)) 
    
import json
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich.prompt import Prompt

from core.llm_client import LLMClient
from core.router import ModelRouter
from core.memory import MemoryManager
from tools.dispatcher import ToolDispatcher

# Initialize Rich console
console = Console()

def display_header(user_name: str):
    """Renders a styled header panel on startup or screen clear."""
    title = Text("🔥  FLAME  AI  ASSISTANT", style="bold bright_white")
    subtitle = Text("Memory  •  Model Router  •  Tools Active", style="italic bright_black")
    user_info = Text.assemble(
        Text("\nWelcome, ", style="bright_black"),
        Text(user_name, style="bold yellow"),
    )

    header_text = Text.assemble(title, "\n", subtitle, user_info, justify="center")

    console.print(
        Panel(
            header_text,
            title="[bold orange1]✦ ONLINE ✦[/bold orange1]",
            title_align="right",
            border_style="orange1",
            padding=(1, 4),
            expand=False,
        )
    )
    console.print(
        "[bright_black]╭─[/bright_black] [bold cyan]/clear[/bold cyan] [dim]screen[/dim]  "
        "[bright_black]│[/bright_black] [bold cyan]/memory[/bold cyan] [dim]memory[/dim]  "
        "[bright_black]│[/bright_black] [bold cyan]/help[/bold cyan] [dim]commands[/dim]  "
        "[bright_black]│[/bright_black] [bold red]exit[/bold red] [dim]quit[/dim] [bright_black]─╮[/bright_black]\n"
    )

def main():
    console.clear()
    
    # Initialize core modules
    llm = LLMClient()
    router = ModelRouter(llm)
    memory = MemoryManager(db_path="data/memory.sqlite")
    dispatcher = ToolDispatcher()

    user_name = memory.get_preference("user_name", "User")
    display_header(user_name)

    chat_history = [
        {
            "role": "system",
            "content": f"You are Flame, a helpful local terminal assistant for {user_name}. Keep explanations concise, clear, and easy to read in a CLI terminal. You have tools available for file operations and system execution."
        }
    ]

    while True:
        try:
            # Custom styled input prompt
            user_input = Prompt.ask("[bold cyan]You[/bold cyan]").strip()
            
            if not user_input:
                continue

            # Handle application exit
            if user_input.lower() in ["exit", "quit"]:
                console.print("\n[bold red]🔥 Flame shutting down... Goodbye![/bold red]")
                break

            # Handle slash commands
            if user_input.startswith("/"):
                cmd = user_input.lower()
                if cmd == "/clear":
                    console.clear()
                    display_header(user_name)
                    continue
                elif cmd == "/memory":
                    pref_name = memory.get_preference("user_name", "Not Set")
                    console.print(
                        Panel(
                            f"[bold yellow]Current user_name preference:[/bold yellow] {pref_name}",
                            title="[bold blue]🧠 Memory State[/bold blue]",
                            border_style="blue"
                        )
                    )
                    continue
                elif cmd == "/help":
                    console.print("[yellow]Commands:[/yellow] /clear - Clear screen | /memory - Show stored key-values | exit - Quit\n")
                    continue

            # Check and store name changes in SQLite memory
            if "my name is" in user_input.lower():
                parts = user_input.lower().split("my name is")
                if len(parts) > 1:
                    extracted_name = parts[1].strip().split()[0].capitalize()
                    memory.set_preference("user_name", extracted_name)
                    user_name = extracted_name
                    console.print(
                        Panel(
                            f"Saved new user_name preference: [bold green]{extracted_name}[/bold green]",
                            title="[bold blue]🧠 Memory Updated[/bold blue]",
                            border_style="blue",
                            padding=(0, 2)
                        )
                    )

            # Route intent and display routing badge
            intent, chosen_model = router.route(user_input)
            console.print(
                Panel(
                    f"[dim]Intent:[/dim] [bold white]{intent}[/bold white]  │  [dim]Model:[/dim] [bold green]{chosen_model}[/bold green]",
                    title="[dim green]⚙️ Model Router[/dim green]",
                    border_style="dim green",
                    padding=(0, 1)
                )
            )

            chat_history.append({"role": "user", "content": user_input})

            # --- Tool Execution Sub-loop ---
            while True:
                active_history = memory.trim_history(chat_history, max_messages=12)

                with console.status("[bold orange1]🔥 Flame is thinking...[/bold orange1]", spinner="simpleDots"):
                    # Call LLM passing tool schemas
                    response = llm.client.chat.completions.create(
                        model=chosen_model,
                        messages=active_history,
                        tools=dispatcher.get_schemas(),
                        tool_choice="auto"
                    )

                response_message = response.choices[0].message
                
                # Check if model triggered a tool call
                if response_message.tool_calls:
                    # Append assistant tool call request to chat history
                    chat_history.append(response_message)

                    for tool_call in response_message.tool_calls:
                        function_name = tool_call.function.name
                        arguments = json.loads(tool_call.function.arguments or "{}")

                        # Display Tool Execution Callout Box
                        console.print(
                            Panel(
                                f"[bold white]Tool:[/bold white] {function_name}\n[bold white]Args:[/bold white] {json.dumps(arguments)}",
                                title="[bold yellow]⚙️ Tool Execution Requested[/bold yellow]",
                                border_style="yellow",
                                padding=(0, 1)
                            )
                        )

                        try:
                            # Run tool via dispatcher
                            result = dispatcher.execute(function_name, arguments)
                        except Exception as e:
                            result = {"status": "error", "error": str(e)}

                        # Display Tool Result
                        console.print(
                            Panel(
                                f"[dim]{json.dumps(result, indent=2)}[/dim]",
                                title="[dim green]✅ Tool Output[/dim green]",
                                border_style="dim green",
                                padding=(0, 1)
                            )
                        )

                        # Feedback result to LLM context
                        chat_history.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result)
                        })

                    # Continue sub-loop to give LLM a turn to inspect tool output
                    continue

                # Final text output from Assistant
                if response_message.content:
                    response_text = response_message.content
                    console.print(
                        Panel(
                            Markdown(response_text),
                            title="[bold orange1]🔥 Flame[/bold orange1]",
                            title_align="left",
                            border_style="orange1",
                            padding=(1, 2)
                        )
                    )
                    console.print("")
                    chat_history.append({"role": "assistant", "content": response_text})

                break

        except KeyboardInterrupt:
            console.print("\n[bold red]🔥 Flame shutting down... Goodbye![/bold red]")
            break

if __name__ == "__main__":
    main()