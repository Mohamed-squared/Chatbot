from .chatbot_app import ChatbotApp
from .database import initialize_database

def main():
    """
    Initializes the database and runs the chatbot application.
    """
    print("Initializing database...")
    initialize_database()
    print("Starting chatbot...")
    app = ChatbotApp()
    app.run()

if __name__ == "__main__":
    main()
