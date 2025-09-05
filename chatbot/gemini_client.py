import os
import google.generativeai as genai
from dotenv import load_dotenv

class GeminiClient:
    """
    A client for interacting with the Google Gemini API.
    """
    def __init__(self, model_name="gemini-2.5-flash"):
        """
        Initializes the Gemini client.

        Args:
            model_name (str): The name of the Gemini model to use.
        """
        load_dotenv()
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in .env file.")

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model_name)
        self.embedding_model = 'models/embedding-001'

    def generate_content(self, prompt, history=None):
        """
        Generates content using the Gemini model.

        Args:
            prompt (str): The user's prompt.
            history (list, optional): The conversation history. Defaults to None.

        Returns:
            str: The generated content.
        """
        chat = self.model.start_chat(history=history or [])
        response = chat.send_message(prompt)
        return response.text

    def generate_embedding(self, text):
        """
        Generates an embedding for the given text.

        Args:
            text (str): The text to embed.

        Returns:
            list: The generated embedding.
        """
        return genai.embed_content(
            model=self.embedding_model,
            content=text,
            task_type="retrieval_document"
        )["embedding"]

    def generate_title(self, text):
        """
        Generates a concise title for a given text.

        Args:
            text (str): The text to summarize into a title.

        Returns:
            str: A concise title.
        """
        prompt = f"Generate a very short, concise, human-readable title (3-5 words) for the following user message:\n\n{text}\n\nTitle:"
        response = self.model.generate_content(prompt)
        return response.text.strip()

    def categorize_memory(self, details: str) -> dict | None:
        """
        Uses the AI to determine a category and shell for a given piece of information.

        Args:
            details (str): The text content of the memory to categorize.

        Returns:
            dict | None: A dictionary with "category" and "shell" keys, or None on failure.
        """
        import json
        system_prompt = """
        You are a memory categorization assistant. Given a piece of text, your job is to determine a suitable "category" and "shell" for it.
        - "category": A broad topic (e.g., "User Preferences", "Project Ideas", "Personal Details").
        - "shell": A mid-level summary of the information (e.g., "Favorite Subjects", "Book Recommendations").
        Please respond with ONLY a valid JSON object containing these two keys. Example: {"category": "User Preferences", "shell": "Favorite Colors"}
        """

        prompt = f"{system_prompt}\n\nText to categorize:\n{details}"

        response = self.model.generate_content(prompt)

        try:
            # The response should be a JSON string, so we parse it.
            return json.loads(response.text)
        except (json.JSONDecodeError, TypeError):
            return None


if __name__ == '__main__':
    # Example usage (requires a .env file with GEMINI_API_KEY)
    try:
        client = GeminiClient()
        # Test content generation
        # print("Testing content generation:")
        # response = client.generate_content("Hello, what can you do?")
        # print(response)

        # Test title generation
        print("\nTesting title generation:")
        title = client.generate_title("I'm trying to learn about the history of the Roman Empire.")
        print(f"Generated Title: {title}")

        # Test embedding generation
        # print("\nTesting embedding generation:")
        # embedding = client.generate_embedding("This is a test sentence.")
        # print(f"Generated embedding of size: {len(embedding)}")

    except ValueError as e:
        print(e)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
