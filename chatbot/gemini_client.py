import os
import time
import json
import google.generativeai as genai
from dotenv import load_dotenv
# It's good practice to handle potential API errors gracefully.
from google.api_core import exceptions as google_exceptions

class GeminiClient:
    """
    A client for interacting with the Google Gemini API, with support for multiple API keys,
    rate limiting, and automatic key rotation on failure.
    """
    def __init__(self, model_name="gemini-2.5-flash", rate_limit_delay: int = 1):
        """
        Initializes the Gemini client.

        Args:
            model_name (str): The name of the Gemini model to use.
            rate_limit_delay (int): Seconds to wait between API calls.
        """
        load_dotenv()
        api_keys_str = os.getenv("GEMINI_API_KEYS")
        if not api_keys_str:
            raise ValueError("GEMINI_API_KEYS not found in .env file.")

        self.api_keys = [key.strip() for key in api_keys_str.split(',') if key.strip()]
        if not self.api_keys:
            raise ValueError("No valid API keys found in GEMINI_API_KEYS.")

        self.current_key_index = 0
        self.model_name = model_name
        self.embedding_model = 'models/embedding-001'
        self.rate_limit_delay = rate_limit_delay
        self.last_call_time = 0

        # Configure with the first key initially
        genai.configure(api_key=self.api_keys[self.current_key_index])
        self.model = genai.GenerativeModel(self.model_name)

    def _apply_rate_limit(self):
        """Ensures a minimum delay between consecutive API calls."""
        elapsed_time = time.time() - self.last_call_time
        if elapsed_time < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed_time)
        self.last_call_time = time.time()

    def _rotate_key(self):
        """
        Rotates to the next API key and returns True if successful, False otherwise.
        """
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        # If we have looped through all keys, it means all have failed.
        if self.current_key_index == 0:
            return False

        genai.configure(api_key=self.api_keys[self.current_key_index])
        self.model = genai.GenerativeModel(self.model_name)
        return True

    def _execute_api_call(self, api_function, *args, **kwargs):
        """
        A robust wrapper for making API calls that handles rate limiting and key rotation.

        Args:
            api_function (callable): The function to call (e.g., self.model.generate_content).
            *args: Positional arguments for the api_function.
            **kwargs: Keyword arguments for the api_function.

        Returns:
            The result of the API function call.

        Raises:
            google_exceptions.PermissionDenied: If all API keys are invalid or exhausted.
        """
        initial_key_index = self.current_key_index
        while True:
            self._apply_rate_limit()
            try:
                return api_function(*args, **kwargs)
            # NOTE: We catch PermissionDenied and ResourceExhausted as these are common
            # indicators of an invalid/deactivated key or exceeding quota.
            except (google_exceptions.PermissionDenied, google_exceptions.ResourceExhausted) as e:
                print(f"API key {self.current_key_index} failed. Rotating to the next key. Error: {e}")
                if not self._rotate_key():
                    raise google_exceptions.PermissionDenied("All API keys failed.") from e
                # If we are back to the initial key, it means we tried all keys.
                if self.current_key_index == initial_key_index:
                    raise google_exceptions.PermissionDenied("All API keys failed after a full rotation.") from e

    def generate_content(self, prompt, history=None):
        """Generates content using the Gemini model."""
        chat = self.model.start_chat(history=history or [])
        response = self._execute_api_call(chat.send_message, prompt)
        return response.text

    def generate_embedding(self, text):
        """Generates an embedding for the given text."""
        return self._execute_api_call(
            genai.embed_content,
            model=self.embedding_model,
            content=text,
            task_type="retrieval_document"
        )["embedding"]

    def generate_title(self, text):
        """Generates a concise title for a given text."""
        prompt = f"Generate a very short, concise, human-readable title (3-5 words) for the following user message:\n\n{text}\n\nTitle:"
        response = self._execute_api_call(self.model.generate_content, prompt)
        return response.text.strip()

    def categorize_memory(self, details: str) -> dict | None:
        """Uses the AI to determine a category and shell for a given piece of information."""
        system_prompt = """
        You are a memory categorization assistant. Given a piece of text, your job is to determine a suitable "category" and "shell" for it.
        - "category": A broad topic (e.g., "User Preferences", "Project Ideas", "Personal Details").
        - "shell": A mid-level summary of the information (e.g., "Favorite Subjects", "Book Recommendations").
        Please respond with ONLY a valid JSON object containing these two keys. Example: {"category": "User Preferences", "shell": "Favorite Colors"}
        """
        prompt = f"{system_prompt}\n\nText to categorize:\n{details}"
        response = self._execute_api_call(self.model.generate_content, prompt)
        try:
            return json.loads(response.text)
        except (json.JSONDecodeError, TypeError):
            return None

if __name__ == '__main__':
    # Example usage (requires a .env file with GEMINI_API_KEYS)
    try:
        client = GeminiClient()
        print("Testing title generation with key rotation and rate limiting...")
        # This will cycle through keys if one fails
        title = client.generate_title("I'm trying to learn about the history of the Roman Empire.")
        print(f"Generated Title: {title}")
    except (ValueError, google_exceptions.PermissionDenied) as e:
        print(e)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
