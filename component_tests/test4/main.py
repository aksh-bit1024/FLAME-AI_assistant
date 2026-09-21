import sys
import json
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown

# Path resolution
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from core.llm_client import LLMClient, STRICT_SYSTEM_PROMPT
from core.router import LLMRouter
from core.memory import MemoryManager
from tools.dispatcher import ToolDispatcher

console = Console()

SYSTEM_PROMPT = f"""{STRICT_SYSTEM_PROMPT}

You are Flame, an autonomous CLI assistant.

ACTIVE MEMORY PROTOCOL:
- When the user mentions personal details, preferences, workflow habits, or project rules, call `save_memory(key, value)` immediately to persist them.

AUTONOMOUS ERROR DIAGNOSTICS:
- If a tool call fails (e.g., returns error output, missing file, or non-zero exit code):
  1. Inspect the error output and stderr details carefully.
  2. Reformulate your plan (e.g., correct paths, adjust command flags, check list_directory).
  3. Automatically issue a new, corrected tool call without quitting or asking the user prematurely.
"""

MODEL_TARGETS = {
    "heavy": "heavy_general",
    "14b": "heavy_general",
    "qwen": "heavy_general",
    "heavy_general": "heavy_general",
    "coder": "coder",
    "code": "coder",
    "py": "coder",
    "reasoning": "reasoning",
    "r1": "reasoning",
    "think": "reasoning",
    "fast": "general_default",
    "general": "general_default",
    "gemma": "general_default",
    "general_default": "general_default",
}
INLINE_MODEL_ALIASES = {
    "/heavy": "heavy_general",
    "/14b": "heavy_general",
    "/qwen": "heavy_general",
    "/coder": "coder",
    "/code": "coder",
    "/py": "coder",
    "/reasoning": "reasoning",
    "/r1": "reasoning",
    "/think": "reasoning",
    "/fast": "general_default",
    "/general": "general_default",
    "/gemma": "general_default",
}
VALID_MODEL_ALIASES = "/heavy, /coder, /reasoning, /fast, /auto"


def resolve_model_target(target: str):
    return MODEL_TARGETS.get(target.strip().lower())


def parse_model_command(user_input: str):
    """Return (action, prompt, target) for model-related slash commands."""
    command, separator, remainder = user_input.partition(" ")
    command = command.lower()

    if command in INLINE_MODEL_ALIASES:
        if not separator or not remainder.strip():
            return "invalid", "", None
        return "prompt", remainder.strip(), INLINE_MODEL_ALIASES[command]

    if command in ("/model", "/use"):
        target_name = remainder.strip().lower() if separator else ""
        if target_name == "auto":
            return "unlock", "", None
        target = resolve_model_target(target_name) if target_name else None
        if target is None:
            return "invalid", "", None
        return "lock", "", target

    if command == "/auto":
        if remainder.strip():
            return "invalid", "", None
        return "unlock", "", None

    if command == "/lock":
        if remainder.strip():
            return "invalid", "", None
        return "lock_current", "", None

    if command == "/unlock":
        if remainder.strip():
            return "invalid", "", None
        return "unlock", "", None

    return "unrecognized", "", None

def display_banner():
    header_text = Text()
    header_text.append("FLAME CLI SYSTEM\n", style="bold orange1")
    header_text.append("Autonomous Diagnostic & Semantic Router Shell", style="dim orange1")
    header_text.append("\n\nCommands: /memory  |  /clear  |  exit", style="dark_orange")

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

def run_with_thinking(operation):
    status = console.status("[dim]thinking...[/dim]", spinner="dots")
    status.start()
    try:
        return operation()
    finally:
        status.stop()

def main():
    memory_mgr = MemoryManager()
    dispatcher = ToolDispatcher(memory_manager=memory_mgr)
    llm = LLMClient()
    router = LLMRouter(llm_client=llm)

    chat_history = []
    current_session_model = None
    active_model = None

    display_banner()

    while True:
        try:
            user_input = console.input("\n[bold orange1]USER>[/bold orange1] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim orange1][SYS] Terminating process.[/dim orange1]")
            break

        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit"]:
            console.print("[dim orange1][SYS] Goodbye.[/dim orange1]")
            break

        # Command Handlers
        if user_input == "/memory":
            memories = memory_mgr.get_all_preferences()
            console.print("\n[bold orange1][MEM] Stored preferences:[/bold orange1]")
            console.print(json.dumps(memories, indent=2) if memories else "  (none)")
            continue

        if user_input == "/clear":
            chat_history = []
            console.print("[dim orange1][SYS] Session context purged.[/dim orange1]")
            continue

        prompt_for_model = user_input
        one_turn_model = None
        if user_input.startswith("/"):
            action, prompt_for_model, one_turn_model = parse_model_command(user_input)
            if action == "lock":
                current_session_model = one_turn_model
                active_model = one_turn_model
                console.print(f"[dim]Session locked to: {current_session_model}[/dim]")
                continue
            if action == "lock_current":
                if active_model is None:
                    console.print("[dim]No active model to lock[/dim]")
                else:
                    current_session_model = active_model
                    console.print(f"[dim]Session locked to: {current_session_model}[/dim]")
                continue
            if action == "unlock":
                current_session_model = None
                console.print("[dim]Session model lock released; routing is automatic[/dim]")
                continue
            if action == "prompt":
                pass
            elif action in ("invalid", "unrecognized"):
                console.print(
                    f"[dim]Valid model aliases: {VALID_MODEL_ALIASES}[/dim]"
                )
                continue

        # 1. Route Intent & Log Classification Latency (in ms)
        if one_turn_model is not None:
            chosen_model = one_turn_model
            route_ms = 0.0
            route_notice = " (Bypassed via /command)"
        elif current_session_model is not None:
            chosen_model = current_session_model
            route_ms = 0.0
            route_notice = " (Session Locked)"
        else:
            chosen_model, route_ms = run_with_thinking(
                lambda: router.route_with_timing(prompt_for_model)
            )
            route_notice = ""
            current_session_model = chosen_model
        active_model = chosen_model
        lock_indicator = " [LOCKED]" if current_session_model else " [AUTO]"
        console.print(
            f"[dim orange1][ROUTER][/dim orange1] Model: [bold orange1]{chosen_model}{lock_indicator}[/bold orange1] "
            f"([cyan]{route_ms:.1f} ms{route_notice}[/cyan])"
        )

        # 2. Prepare Context Injection
        current_memories = memory_mgr.get_all_preferences()
        dynamic_system_prompt = (
            f"{SYSTEM_PROMPT}\n\nCURRENT STORED MEMORIES:\n"
            f"{json.dumps(current_memories, indent=2)}"
        )

        if chat_history and chat_history[0].get("role") == "system":
            chat_history[0]["content"] = dynamic_system_prompt
        else:
            chat_history.insert(0, {"role": "system", "content": dynamic_system_prompt})

        chat_history.append({"role": "user", "content": prompt_for_model})

        # 3. Start Main Response Timer
        start_response_time = time.perf_counter()

        max_diagnostic_turns = 5
        turn_count = 0

        # Multi-Turn Diagnostic Loop
        while turn_count < max_diagnostic_turns:
            turn_count += 1
            trimmed_messages = memory_mgr.trim_history(chat_history, max_messages=10)

            response = run_with_thinking(
                lambda: llm.chat(
                    model=chosen_model,
                    messages=trimmed_messages,
                    tools=dispatcher.get_schemas()
                )
            )

            response_message = response.choices[0].message

            if response_message.tool_calls:
                chat_history.append(response_message)

                for tool_call in response_message.tool_calls:
                    func_name = tool_call.function.name
                    try:
                        args = json.loads(tool_call.function.arguments or "{}")
                        if not isinstance(args, dict):
                            raise ValueError("Tool arguments must be a JSON object.")
                    except (TypeError, ValueError, json.JSONDecodeError) as exc:
                        args = {}
                        result = {"status": "error", "error": f"Invalid tool arguments: {exc}"}
                    else:
                        try:
                            result = dispatcher.execute(func_name, args)
                        except Exception as exc:
                            result = {"status": "error", "error": str(exc)}

                    console.print(
                        f"[dim orange1][EXEC][/dim orange1] "
                        f"[bold dark_orange]{func_name}[/bold dark_orange]({args})"
                    )
                    chat_history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result)
                    })

                continue

            if response_message.content:
                # Stop response timer and convert duration to minutes
                elapsed_min = (time.perf_counter() - start_response_time) / 60

                console.print("\n[bold orange1]FLAME>[/bold orange1]")
                console.print(Markdown(response_message.content))
                
                console.print(
                    f"\n[dim orange1][PERF][/dim orange1] Generation complete in "
                    f"[bold dark_orange]{elapsed_min:.3f} min[/bold dark_orange]\n"
                )
                
                chat_history.append({"role": "assistant", "content": response_message.content})
                break
        else:
            console.print("\n[bold red][ERROR] Maximum diagnostic retry limit reached.[/bold red]")

if __name__ == "__main__":
    main()