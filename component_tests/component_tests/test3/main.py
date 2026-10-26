import sys
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich.prompt import Prompt

from core.llm_client import LLMClient
from core.router import ModelRouter
from core.memory import MemoryManager

# Initialize Rich console
console = Console()

def display_header(user_name: str):
    """Renders a styled header panel on startup or screen clear."""
    title = Text("🔥  FLAME  AI  ASSISTANT", style="bold bright_white")
    subtitle = Text("Memory  •  Model Router  •  Ready", style="italic bright_black")
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

    user_name = memory.get_preference("user_name", "User")
    display_header(user_name)

    chat_history = [
        {
            "role": "system",
            "content": f"You are Flame, a helpful local terminal assistant for {user_name}. Keep explanations concise, clear, and easy to read in a CLI terminal."
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
            active_history = memory.trim_history(chat_history, max_messages=10)

            # Render live spinner while query is running
            with console.status("[bold orange1]🔥 Flame is thinking...[/bold orange1]", spinner="simpleDots"):
                response_text = llm.chat(active_history, model=chosen_model)
            
            # Pretty render Flame response with Markdown support inside a Panel
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

        except KeyboardInterrupt:
            console.print("\n[bold red]🔥 Flame shutting down... Goodbye![/bold red]")
            break

if __name__ == "__main__":
    main()