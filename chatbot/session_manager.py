from .database import get_db_connection

class SessionManager:
    """Manages chat sessions."""

    def __init__(self):
        """Initializes the SessionManager."""
        self.conn = get_db_connection()

    def create_session(self, title: str) -> int:
        """
        Creates a new session in the database.

        Args:
            title (str): The title of the session.

        Returns:
            int: The ID of the newly created session.
        """
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO sessions (title) VALUES (?)", (title,))
        self.conn.commit()
        return cursor.lastrowid

    def list_sessions(self) -> list:
        """
        Lists all available sessions.

        Returns:
            list: A list of session records.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, title, created_at FROM sessions ORDER BY created_at DESC")
        return cursor.fetchall()

    def get_session_history(self, session_id: int, max_tokens: int = 1000000) -> list:
        """
        Retrieves the conversation history for a given session, with token limit management.

        Args:
            session_id (int): The ID of the session.
            max_tokens (int): The maximum number of tokens for the history.

        Returns:
            list: A list of message records (dicts), potentially truncated.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY timestamp ASC",
            (session_id,),
        )

        messages = cursor.fetchall()
        history = []
        current_tokens = 0

        # A common heuristic is ~4 characters per token
        def count_tokens(text: str) -> int:
            return len(text) // 4

        # Handle the special case of injected memory prompt
        system_prompt_messages = []
        if len(messages) >= 2 and "I have some long-term memories" in messages[0]['content']:
            system_prompt_user = messages[0]
            system_prompt_model = messages[1]
            system_prompt_messages = [
                {"role": system_prompt_user["role"], "parts": [system_prompt_user["content"]]},
                {"role": system_prompt_model["role"], "parts": [system_prompt_model["content"]]}
            ]
            prompt_tokens = count_tokens(system_prompt_user["content"]) + count_tokens(system_prompt_model["content"])

            # If the prompt itself exceeds the limit, we can't do much
            if prompt_tokens > max_tokens:
                return []

            current_tokens += prompt_tokens
            messages = messages[2:] # Process the rest of the messages

        # Process messages from newest to oldest
        temp_history = []
        for row in reversed(messages):
            content = row["content"]
            message_tokens = count_tokens(content)

            if current_tokens + message_tokens > max_tokens:
                break

            current_tokens += message_tokens
            temp_history.append({"role": row["role"], "parts": [content]})

        # The history is reversed, so we reverse it back
        history = list(reversed(temp_history))

        # Prepend the system prompt messages if they exist
        if system_prompt_messages:
            history = system_prompt_messages + history

        return history

    def add_message_to_history(self, session_id: int, role: str, content: str):
        """
        Adds a message to the conversation history of a session.

        Args:
            session_id (int): The ID of the session.
            role (str): The role of the message sender ('user' or 'model').
            content (str): The content of the message.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content),
        )
        self.conn.commit()

    def get_session_title(self, session_id: int) -> str:
        """
        Retrieves the title of a specific session.

        Args:
            session_id (int): The ID of the session.

        Returns:
            str: The title of the session, or an empty string if not found.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT title FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        return row['title'] if row else ""

    def __del__(self):
        """Closes the database connection when the object is destroyed."""
        self.conn.close()

if __name__ == '__main__':
    # This is for testing purposes.
    # It requires the database to be initialized first.
    from .database import initialize_database
    initialize_database()

    sm = SessionManager()

    # Create a new session
    session_id = sm.create_session("Test Session")
    print(f"Created session with ID: {session_id}")

    # Add messages
    sm.add_message_to_history(session_id, "user", "Hello, world!")
    sm.add_message_to_history(session_id, "model", "Hello! How can I help you today?")
    print("Added messages to session.")

    # List sessions
    sessions = sm.list_sessions()
    print("\nAvailable sessions:")
    for session in sessions:
        print(f"- ID: {session['id']}, Title: {session['title']}")

    # Get history
    history = sm.get_session_history(session_id)
    print(f"\nHistory for session {session_id}:")
    print(history)

    # Get title
    title = sm.get_session_title(session_id)
    print(f"\nTitle for session {session_id}: {title}")
