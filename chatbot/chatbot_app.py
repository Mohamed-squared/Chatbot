import os
import json
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from .database import initialize_database
from .gemini_client import GeminiClient
from .session_manager import SessionManager
from .memory_manager import MemoryManager
from .utils import count_tokens, format_memories_for_prompt

class ChatbotApp:
    """The main application class for the terminal-based chatbot."""

    def __init__(self):
        """Initializes the chatbot application."""
        self.console = Console()
        try:
            self.gemini_client = GeminiClient()
        except ValueError as e:
            self.console.print(f"[bold red]Error: {e}[/bold red]")
            self.console.print("Please create a .env file with your GEMINI_API_KEYS.")
            exit()

        self.session_manager = SessionManager()
        self.memory_manager = MemoryManager()
        self.active_session_id = None
        self.load_last_session()

    def load_last_session(self):
        """Loads the most recent session to start."""
        sessions = self.session_manager.list_sessions()
        if sessions:
            self.active_session_id = sessions[0]['id']
        else:
            self.start_new_session(is_first_launch=True)

    def run(self):
        """The main loop of the application."""
        self.display_welcome_message()
        while True:
            self.display_header()
            prompt_text = Text(f"({self.active_session_id}) > ", style="bold cyan")
            user_input = Prompt.ask(prompt_text)

            if user_input.startswith('/'):
                self.handle_command(user_input)
            else:
                self.handle_chat_message(user_input)

    def handle_command(self, command: str):
        """Handles user commands."""
        parts = command.split()
        cmd = parts[0]
        args = parts[1:]

        if cmd == '/new':
            self.start_new_session()
        elif cmd == '/list':
            self.list_sessions()
        elif cmd == '/switch':
            if args:
                try:
                    session_id = int(args[0])
                    self.switch_session(session_id)
                except ValueError:
                    self.console.print("[bold red]Invalid session ID.[/bold red]")
            else:
                self.console.print("[bold red]Usage: /switch [id][/bold red]")
        elif cmd == '/export':
            self.export_session(args[0] if args else "md")
        elif cmd == '/remember':
            self.handle_remember_command(command)
        elif cmd == '/mem':
            self.handle_memory_command(args)
        elif cmd == '/help':
            self.display_help()
        elif cmd == '/exit':
            self.console.print("[bold blue]Goodbye![/bold blue]")
            exit()
        else:
            self.console.print(f"[bold red]Unknown command: {cmd}[/bold red]")

    def handle_chat_message(self, user_input: str, custom_history: list = None):
        """
        Handles a regular chat message from the user.
        Can be provided with a custom history for the first message of a session.
        """
        if not self.active_session_id:
            self.console.print("[bold red]No active session. Start one with /new.[/bold red]")
            return

        # Add user message to history DB
        self.session_manager.add_message_to_history(self.active_session_id, 'user', user_input)

        # Get history and generate response
        history = custom_history or self.session_manager.get_session_history(self.active_session_id, max_tokens=1000000)

        with self.console.status("[bold green]Thinking...[/bold green]"):
            response = self.gemini_client.generate_content(user_input, history)

        self.console.print(Panel(response, title="[bold green]Gemini[/bold green]", border_style="green"))

        # Add model response to history DB
        self.session_manager.add_message_to_history(self.active_session_id, 'model', response)

        # Analyze for memory storage and display confirmation
        stored_memory = self.memory_manager.analyze_and_store_memory(user_input, response)
        if stored_memory:
            mem_panel = Panel(
                f"[bold magenta]Category:[/bold magenta] {stored_memory['category']}\n"
                f"[bold yellow]Shell:[/bold yellow] {stored_memory['shell']}\n"
                f"[bold green]Details:[/bold green] {stored_memory['details']}",
                title="[bold blue]📝 Memory Stored[/bold blue]",
                border_style="blue"
            )
            self.console.print(mem_panel)


    def start_new_session(self, is_first_launch=False):
        """Starts a new chat session."""
        custom_history = None
        all_memories = self.memory_manager.get_all_memories()
        if all_memories:
            include_mem = Prompt.ask("Include long-term memory in this session?", choices=["y", "n"], default="y")
            if include_mem == 'y':
                memories_to_include = all_memories
                formatted_memories = format_memories_for_prompt(all_memories)
                token_count = count_tokens(formatted_memories)

                if token_count > 100000:
                    self.console.print(f"[bold yellow]Warning: Memory size ({token_count} tokens) is large.[/bold yellow]")
                    categories = self.memory_manager.get_unique_categories()

                    table = Table(title="Select Memory Categories to Include")
                    table.add_column("Number", style="cyan")
                    table.add_column("Category", style="magenta")
                    for i, cat in enumerate(categories):
                        table.add_row(str(i + 1), cat)
                    self.console.print(table)

                    selection = Prompt.ask("Enter category numbers (e.g., 1,3,4), or 'all'")

                    if selection.lower() != 'all':
                        try:
                            selected_indices = [int(i.strip()) - 1 for i in selection.split(',')]
                            selected_categories = [categories[i] for i in selected_indices if 0 <= i < len(categories)]
                            if selected_categories:
                                memories_to_include = self.memory_manager.get_memories_by_categories(selected_categories)
                        except ValueError:
                            self.console.print("[bold red]Invalid selection. Including all memories.[/bold red]")

                formatted_memories = format_memories_for_prompt(memories_to_include)
                final_token_count = count_tokens(formatted_memories)

                system_prompt = (
                    "I have some long-term memories to provide context for this conversation. "
                    "Please acknowledge them and use them to inform your responses.\n\n"
                    f"--- Memories ---\n{formatted_memories}\n--- End of Memories ---"
                )
                custom_history = [
                    {'role': 'user', 'parts': [system_prompt]},
                    {'role': 'model', 'parts': ["Understood. I will use this information to inform my responses."]}
                ]
                self.console.print(f"[blue]Long-term memory ({final_token_count} tokens) has been included in this session.[/blue]")

        if is_first_launch:
            self.console.print("Starting your first session.")
            first_message = Prompt.ask("[bold yellow]What's on your mind?[/bold yellow]")
        else:
            first_message = Prompt.ask("[bold yellow]Enter the first message for the new session[/bold yellow]")

        with self.console.status("[bold green]Creating title...[/bold green]"):
            title = self.gemini_client.generate_title(first_message)

        session_id = self.session_manager.create_session(title)
        self.active_session_id = session_id
        self.console.print(f"[bold green]New session started: '{title}' (ID: {session_id})[/bold green]")
        self.handle_chat_message(first_message, custom_history=custom_history)


    def list_sessions(self):
        """Displays a table of all sessions."""
        sessions = self.session_manager.list_sessions()
        if not sessions:
            self.console.print("[yellow]No sessions found. Start one with /new.[/yellow]")
            return

        table = Table(title="Available Chat Sessions")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Title", style="magenta")
        table.add_column("Created At", style="green")

        for session in sessions:
            table.add_row(str(session['id']), session['title'], str(session['created_at']))

        self.console.print(table)

    def switch_session(self, session_id: int):
        """Switches to a different session."""
        title = self.session_manager.get_session_title(session_id)
        if title:
            self.active_session_id = session_id
            self.console.print(f"Switched to session: '[bold magenta]{title}[/bold magenta]' (ID: {session_id})")
            self.display_conversation_history()
        else:
            self.console.print(f"[bold red]Session with ID {session_id} not found.[/bold red]")

    def display_welcome_message(self):
        """Displays a welcome message when the app starts."""
        self.console.print(Panel(
            "[bold green]Welcome to the Gemini Terminal Chatbot![/bold green]\nType `/help` for a list of commands.",
            title="[bold blue]Chatbot[/bold blue]",
            border_style="blue"
        ))

    def display_header(self):
        """Displays the header with session info."""
        if self.active_session_id:
            title = self.session_manager.get_session_title(self.active_session_id)
            header_text = f"Session: [bold magenta]{title}[/bold magenta] (ID: {self.active_session_id})"
            self.console.print(Panel(header_text, style="bold blue"))

    def display_conversation_history(self):
        """Displays the full conversation history for the active session."""
        if not self.active_session_id:
            return

        history = self.session_manager.get_session_history(self.active_session_id)
        self.console.print(f"\n--- Conversation History for Session {self.active_session_id} ---")
        for message in history:
            role = message['role']
            content = message['parts'][0]
            if role == 'user':
                self.console.print(Panel(content, title="[bold cyan]You[/bold cyan]", border_style="cyan"))
            else:
                self.console.print(Panel(content, title="[bold green]Gemini[/bold green]", border_style="green"))
        self.console.print("--- End of History ---\n")

    def display_help(self):
        """Displays the help message with available commands."""
        table = Table(title="Available Commands")
        table.add_column("Command", style="cyan")
        table.add_column("Description", style="magenta")

        commands = {
            "/new": "Start a new chat session.",
            "/list": "List all available sessions.",
            "/switch [id]": "Switch to a specific session by its ID.",
            "/remember [text]": "Tell the chatbot to remember a specific piece of information.",
            "/export [md|json]": "Export the current session to a file.",
            "/mem list": "List all stored long-term memories.",
            "/mem add \"cat\" \"shell\" \"details\"": "Manually add a new memory.",
            "/mem search [query]": "Search memories using semantic search.",
            "/mem delete [id]": "Delete a memory by its ID.",
            "/mem summarize [id]": "Get an AI-generated summary of a memory.",
            "/help": "Show this help message.",
            "/exit": "Quit the chatbot."
        }
        for cmd, desc in commands.items():
            table.add_row(cmd, desc)

        self.console.print(table)

    def handle_remember_command(self, user_input: str):
        """Handles the /remember command to explicitly store a memory."""
        # The command is '/remember', so the text is everything after that
        details_to_remember = user_input.partition(' ')[2].strip()

        if not details_to_remember:
            self.console.print("[bold red]Usage: /remember [text to remember][/bold red]")
            return

        with self.console.status("[bold blue]Categorizing and storing memory...[/bold blue]"):
            try:
                # Use the AI to generate a category and shell
                memory_structure = self.gemini_client.categorize_memory(details_to_remember)

                if memory_structure and all(k in memory_structure for k in ["category", "shell"]):
                    self.memory_manager.add_memory(
                        memory_structure["category"],
                        memory_structure["shell"],
                        details_to_remember
                    )
                    mem_panel = Panel(
                        f"[bold magenta]Category:[/bold magenta] {memory_structure['category']}\n"
                        f"[bold yellow]Shell:[/bold yellow] {memory_structure['shell']}\n"
                        f"[bold green]Details:[/bold green] {details_to_remember}",
                        title="[bold blue]📝 Memory Stored[/bold blue]",
                        border_style="blue"
                    )
                    self.console.print(mem_panel)
                else:
                    # Fallback if the AI fails to structure the data
                    self.console.print("[bold red]Failed to categorize memory automatically. Storing without category.[/bold red]")
                    self.memory_manager.add_memory("Uncategorized", "User Directed", details_to_remember)

            except Exception as e:
                self.console.print(f"[bold red]An error occurred while storing the memory: {e}[/bold red]")
                self.memory_manager.add_memory("Uncategorized", "User Directed (Error)", details_to_remember)


    def handle_memory_command(self, args: list):
        """Handles memory management subcommands."""
        if not args:
            self.console.print("[bold red]Usage: /mem [list|add|search|delete|summarize][/bold red]")
            return

        sub_cmd = args[0]
        sub_args = args[1:]

        if sub_cmd == 'list':
            self.list_memories()
        elif sub_cmd == 'add':
            full_input = " ".join(sub_args)
            parts = [p.strip() for p in full_input.split('"') if p.strip()]
            if len(parts) == 3:
                category, shell, details = parts
                self.memory_manager.add_memory(category, shell, details)
                self.console.print("[bold green]Memory added successfully.[/bold green]")
            else:
                self.console.print("[bold red]Usage: /mem add \"<category>\" \"<shell>\" \"<details>\"[/bold red]")
        elif sub_cmd == 'search':
            if not sub_args:
                self.console.print("[bold red]Usage: /mem search [query][/bold red]")
            else:
                self.search_memories(" ".join(sub_args))
        elif sub_cmd == 'delete':
            if not sub_args:
                self.console.print("[bold red]Usage: /mem delete [id][/bold red]")
            else:
                try:
                    mem_id = int(sub_args[0])
                    self.delete_memory(mem_id)
                except ValueError:
                    self.console.print("[bold red]Invalid memory ID.[/bold red]")
        elif sub_cmd == 'summarize':
            if not sub_args:
                self.console.print("[bold red]Usage: /mem summarize [id][/bold red]")
            else:
                try:
                    mem_id = int(sub_args[0])
                    self.summarize_memory(mem_id)
                except ValueError:
                    self.console.print("[bold red]Invalid memory ID.[/bold red]")
        else:
            self.console.print(f"[bold red]Unknown memory command: {sub_cmd}[/bold red]")

    def list_memories(self):
        """Displays a table of all stored memories."""
        memories = self.memory_manager.get_all_memories()
        if not memories:
            self.console.print("[yellow]No memories found.[/yellow]")
            return

        table = Table(title="Stored Memories")
        table.add_column("ID", style="cyan")
        table.add_column("Category", style="magenta")
        table.add_column("Shell", style="yellow")
        table.add_column("Details", style="green")

        for mem in memories:
            table.add_row(str(mem['id']), mem['category'], mem['shell'], mem['details'])

        self.console.print(table)

    def search_memories(self, query: str):
        """Searches memories and displays the results."""
        with self.console.status("[bold green]Searching memories...[/bold green]"):
            results = self.memory_manager.search_memories(query)

        if not results:
            self.console.print("[yellow]No relevant memories found.[/yellow]")
            return

        table = Table(title=f"Memory Search Results for '{query}'")
        table.add_column("ID", style="cyan")
        table.add_column("Category", style="magenta")
        table.add_column("Shell", style="yellow")
        table.add_column("Details", style="green")

        for res in results:
            table.add_row(str(res['id']), res['category'], res['shell'], res['details'])

        self.console.print(table)

    def delete_memory(self, memory_id: int):
        """Deletes a memory."""
        self.memory_manager.delete_memory(memory_id)
        self.console.print(f"[bold green]Memory with ID {memory_id} deleted.[/bold green]")

    def summarize_memory(self, memory_id: int):
        """Summarizes a memory."""
        with self.console.status("[bold green]Summarizing memory...[/bold green]"):
            summary = self.memory_manager.summarize_memory(memory_id)

        self.console.print(Panel(summary, title=f"Summary for Memory ID {memory_id}", border_style="yellow"))

    def export_session(self, format: str = "md"):
        """Exports the current session to a file."""
        if not self.active_session_id:
            self.console.print("[bold red]No active session to export.[/bold red]")
            return

        if format not in ["md", "json"]:
            self.console.print("[bold red]Invalid export format. Use 'md' or 'json'.[/bold red]")
            return

        title = self.session_manager.get_session_title(self.active_session_id)
        history = self.session_manager.get_session_history(self.active_session_id)

        # Sanitize title for filename
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '_')).rstrip()
        filename = f"{safe_title}.{format}"

        try:
            with open(filename, "w", encoding="utf-8") as f:
                if format == "md":
                    f.write(f"# Chat Session: {title}\n\n")
                    for message in history:
                        role = "You" if message['role'] == 'user' else "Gemini"
                        content = message['parts'][0]
                        f.write(f"**{role}:**\n\n{content}\n\n---\n\n")
                elif format == "json":
                    export_data = {
                        "title": title,
                        "session_id": self.active_session_id,
                        "history": history
                    }
                    json.dump(export_data, f, indent=2)

            self.console.print(f"[bold green]Session exported successfully to '{filename}'[/bold green]")

        except Exception as e:
            self.console.print(f"[bold red]Error exporting session: {e}[/bold red]")
