"""
app.py - Privacy-First Local LLM Chatbot with Memory Management
Connects to local Ollama runtime, manages sliding-window conversational memory,
supports real-time token streaming, and provides shell slash commands.
"""

import os
import sys
import json
import time
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

load_dotenv()
console = Console()

# -----------------------------
# CONFIGURATION
# -----------------------------
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
CURRENT_MODEL = os.getenv("DEFAULT_MODEL", "llama3.2")
MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "10"))

TRANSCRIPT_DIR = "chat_transcripts"
os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful, knowledgeable, and concise local AI assistant. "
    "Provide clear, direct answers and format code using Markdown syntax."
)


class ChatSession:
    """Manages chat messages, sliding memory window, and Ollama streaming."""
    def __init__(self, system_prompt: str = DEFAULT_SYSTEM_PROMPT, model: str = CURRENT_MODEL):
        self.model = model
        self.system_prompt = system_prompt
        self.history: List[Dict[str, str]] = []

    def clear(self):
        self.history.clear()

    def get_payload_messages(self) -> List[Dict[str, str]]:
        """Returns system prompt + sliding window of recent messages."""
        # Sliding window keeps the most recent turns (user + assistant pairs)
        recent_window = self.history[-(MAX_HISTORY_TURNS * 2):]
        return [{"role": "system", "content": self.system_prompt}] + recent_window

    def save_transcript(self, filename: Optional[str] = None) -> str:
        """Exports chat history to a JSON file."""
        ts = int(time.time())
        name = filename or f"chat_session_{ts}"
        if not name.endswith(".json"):
            name += ".json"
        filepath = os.path.join(TRANSCRIPT_DIR, name)

        export_data = {
            "model": self.model,
            "timestamp": ts,
            "system_prompt": self.system_prompt,
            "turns_count": len(self.history) // 2,
            "messages": self.history
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2)
        return filepath

    def stream_chat(self, user_message: str) -> str:
        """Sends message to Ollama and streams response in real time."""
        self.history.append({"role": "user", "content": user_message})
        messages = self.get_payload_messages()

        url = f"{OLLAMA_HOST}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True
        }

        full_reply = []
        try:
            with requests.post(url, json=payload, stream=True, timeout=60) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines(decode_unicode=True):
                    if line:
                        chunk_json = json.loads(line)
                        token = chunk_json.get("message", {}).get("content", "")
                        print(token, end="", flush=True)
                        full_reply.append(token)
                        if chunk_json.get("done", False):
                            break
        except Exception as e:
            err_msg = f"\n[Error communicating with Ollama: {e}]"
            print(err_msg)
            full_reply.append(err_msg)

        reply_str = "".join(full_reply).strip()
        self.history.append({"role": "assistant", "content": reply_str})
        return reply_str


def check_ollama_status() -> bool:
    """Verifies that Ollama server is running and lists models."""
    try:
        resp = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=3)
        if resp.status_code == 200:
            models = [m["name"] for m in resp.json().get("models", [])]
            console.print(f"[green]✓ Connected to Ollama at {OLLAMA_HOST}[/green]")
            if models:
                console.print(f"  Available models: [dim]{', '.join(models)}[/dim]")
            return True
    except Exception:
        pass

    console.print(f"[bold yellow]⚠️ Ollama is not reachable at {OLLAMA_HOST}[/bold yellow]")
    console.print("[dim]To run locally: install Ollama from https://ollama.com and run 'ollama run llama3.2'[/dim]\n")
    return False


def main():
    console.print("=" * 70, style="bold cyan")
    console.print("  🦙 Local LLM Chatbot (Ollama Powered)", style="bold cyan")
    console.print("=" * 70, style="bold cyan")

    check_ollama_status()
    session = ChatSession()

    console.print(f"\nActive Model: [bold yellow]{session.model}[/bold yellow] | Sliding Window: [bold yellow]{MAX_HISTORY_TURNS} turns[/bold yellow]")
    console.print("Commands: [cyan]/clear[/cyan], [cyan]/save [name][/cyan], [cyan]/model [name][/cyan], [cyan]/system [prompt][/cyan], [cyan]/exit[/cyan]\n")

    while True:
        try:
            user_input = input("🧑 You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSession ended.")
            break

        if not user_input:
            continue

        # Handle Slash Commands
        if user_input.startswith("/"):
            parts = user_input.split(" ", 1)
            cmd = parts[0].lower()
            arg = parts[1].strip() if len(parts) > 1 else ""

            if cmd in ("/exit", "/quit"):
                console.print("[yellow]Exiting chat. Goodbye![/yellow]")
                break
            elif cmd == "/clear":
                session.clear()
                console.print("[green]✓ Conversation history cleared.[/green]\n")
                continue
            elif cmd == "/save":
                path = session.save_transcript(arg or None)
                console.print(f"[green]✓ Transcript saved to {path}[/green]\n")
                continue
            elif cmd == "/model":
                if arg:
                    session.model = arg
                    console.print(f"[green]✓ Active model switched to: {session.model}[/green]\n")
                else:
                    console.print(f"Current model: {session.model}\n")
                continue
            elif cmd == "/system":
                if arg:
                    session.system_prompt = arg
                    console.print(f"[green]✓ System prompt updated.[/green]\n")
                else:
                    console.print(f"Current system prompt:\n{session.system_prompt}\n")
                continue
            elif cmd in ("/help", "/commands"):
                console.print(
                    "Available Commands:\n"
                    "  /clear          - Reset conversation memory\n"
                    "  /save [name]    - Export session history to JSON\n"
                    "  /model [name]   - Switch Ollama model dynamically\n"
                    "  /system [prompt]- Change system persona instructions\n"
                    "  /exit           - Terminate chat session\n"
                )
                continue
            else:
                console.print(f"[red]Unknown command: {cmd}. Type /help for options.[/red]\n")
                continue

        # Normal Chat
        print("\n🦙 Assistant: ", end="")
        session.stream_chat(user_input)
        print("\n")


if __name__ == "__main__":
    main()
