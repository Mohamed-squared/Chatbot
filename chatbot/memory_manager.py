import numpy as np
import json
from .database import get_db_connection
from .gemini_client import GeminiClient

class MemoryManager:
    """Manages the chatbot's long-term memory."""

    def __init__(self):
        """Initializes the MemoryManager."""
        self.conn = get_db_connection()
        try:
            self.gemini_client = GeminiClient()
        except ValueError:
            # This allows the app to run without an API key for some features
            self.gemini_client = None

    def add_memory(self, category: str, shell: str, details: str, store_embedding: bool = True):
        """
        Adds a new memory to the database.

        Args:
            category (str): The broad topic.
            shell (str): A mid-level summary.
            details (str): The specific facts.
            store_embedding (bool): Whether to generate and store an embedding.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO memories (category, shell, details) VALUES (?, ?, ?)",
            (category, shell, details),
        )
        memory_id = cursor.lastrowid
        self.conn.commit()

        if store_embedding and self.gemini_client:
            embedding = self.gemini_client.generate_embedding(f"{category}: {shell} - {details}")
            cursor.execute(
                "INSERT INTO memory_embeddings (memory_id, embedding) VALUES (?, ?)",
                (memory_id, np.array(embedding).tobytes()),
            )
            self.conn.commit()

    def get_all_memories(self) -> list:
        """Retrieves all memories, formatted for display."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, category, shell, details, created_at FROM memories ORDER BY category, shell")
        return cursor.fetchall()

    def get_unique_categories(self) -> list[str]:
        """Retrieves a list of unique memory categories."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT DISTINCT category FROM memories ORDER BY category")
        return [row['category'] for row in cursor.fetchall()]

    def get_memories_by_categories(self, categories: list[str]) -> list:
        """Retrieves memories from a list of specified categories."""
        cursor = self.conn.cursor()
        query = "SELECT id, category, shell, details, created_at FROM memories WHERE category IN ({}) ORDER BY category, shell".format(','.join('?' for _ in categories))
        cursor.execute(query, categories)
        return cursor.fetchall()

    def search_memories(self, query: str, top_k: int = 5) -> list:
        """
        Performs semantic search for memories.

        Args:
            query (str): The search query.
            top_k (int): The number of top results to return.

        Returns:
            list: A list of the most relevant memory records.
        """
        if not self.gemini_client:
            return []

        query_embedding = np.array(self.gemini_client.generate_embedding(query))

        cursor = self.conn.cursor()
        cursor.execute("SELECT m.id, m.category, m.shell, m.details, me.embedding FROM memories m JOIN memory_embeddings me ON m.id = me.memory_id")

        all_memories = cursor.fetchall()
        if not all_memories:
            return []

        # Calculate cosine similarity
        similarities = []
        for row in all_memories:
            db_embedding = np.frombuffer(row['embedding'], dtype=np.float32)
            # Cosine similarity calculation
            cos_sim = np.dot(query_embedding, db_embedding) / (np.linalg.norm(query_embedding) * np.linalg.norm(db_embedding))
            similarities.append((cos_sim, row))

        # Sort by similarity and get top_k
        similarities.sort(key=lambda x: x[0], reverse=True)

        # Return the memory part of the tuple
        return [row for _, row in similarities[:top_k]]

    def delete_memory(self, memory_id: int):
        """Deletes a memory and its embedding."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM memory_embeddings WHERE memory_id = ?", (memory_id,))
        cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self.conn.commit()

    def summarize_memory(self, memory_id: int) -> str:
        """Generates a summary for a specific memory."""
        if not self.gemini_client:
            return "Cannot summarize memory without Gemini API access."

        cursor = self.conn.cursor()
        cursor.execute("SELECT category, shell, details FROM memories WHERE id = ?", (memory_id,))
        row = cursor.fetchone()
        if not row:
            return "Memory not found."

        text_to_summarize = f"Category: {row['category']}\nShell: {row['shell']}\nDetails: {row['details']}"
        prompt = f"Provide a brief, one-sentence summary of the following memory:\n\n{text_to_summarize}"
        return self.gemini_client.generate_content(prompt)

    def analyze_and_store_memory(self, user_prompt: str, model_response: str) -> dict | None:
        """
        Analyzes a conversation turn and decides if something is worth remembering.
        If a memory is stored, it returns the stored memory data.
        """
        if not self.gemini_client:
            return None

        system_prompt = """
        Your task is to analyze a conversation and identify facts, preferences, or key information that should be saved to a long-term memory.
        Pay close attention to explicit instructions. If the user says "remember that...", "don't forget...", or similar phrases, you MUST treat this as a directive to store the information.
        If you find something worth remembering, extract it and format it as a JSON object with three keys: "category", "shell", and "details".
        - "category": A broad topic (e.g., "User Preferences", "Project Ideas", "Personal Details").
        - "shell": A mid-level summary of the information (e.g., "Favorite Subjects", "Book Recommendations").
        - "details": The specific, detailed fact (e.g., "User enjoys studying abstract algebra and number theory.").
        If nothing noteworthy is found, or the user explicitly says not to remember, respond with "None".
        Analyze the following interaction:
        """

        conversation = f"User: {user_prompt}\nAI: {model_response}"
        prompt = f"{system_prompt}\n\n{conversation}"

        response = self.gemini_client.generate_content(prompt)

        if response.strip().lower() != "none":
            try:
                memory_data = json.loads(response)
                if all(k in memory_data for k in ["category", "shell", "details"]):
                    self.add_memory(
                        memory_data["category"],
                        memory_data["shell"],
                        memory_data["details"]
                    )
                    return memory_data
            except (json.JSONDecodeError, TypeError):
                # The response was not a valid JSON object
                pass
        return None

    def __del__(self):
        """Closes the database connection when the object is destroyed."""
        self.conn.close()

if __name__ == '__main__':
    from .database import initialize_database
    initialize_database()

    mm = MemoryManager()
    if mm.gemini_client:
        # Add a memory
        mm.add_memory("User Preferences", "Favorite Colors", "User likes deep blue and forest green.")
        print("Memory added.")

        # Get all memories
        memories = mm.get_all_memories()
        print("\nAll memories:")
        for mem in memories:
            print(f"- ID {mem['id']}: {mem['category']} -> {mem['shell']} -> {mem['details']}")

        # Search memories
        search_results = mm.search_memories("What colors does the user like?")
        print("\nSearch results for 'What colors does the user like?':")
        for res in search_results:
            print(f"- {res['details']}")

        # Delete memory
        if memories:
            mem_id_to_delete = memories[0]['id']
            mm.delete_memory(mem_id_to_delete)
            print(f"\nDeleted memory with ID {mem_id_to_delete}")
            # Verify deletion
            memories_after_delete = mm.get_all_memories()
            print(f"Memories remaining: {len(memories_after_delete)}")
    else:
        print("Cannot run full MemoryManager test without GEMINI_API_KEYS.")
