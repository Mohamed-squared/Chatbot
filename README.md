# Gemini Terminal Chatbot

A professional, visually pleasing, terminal-based AI chatbot powered by the Gemini 2.5 Pro API. This chatbot supports multiple sessions, long-term hierarchical memory, semantic search, and a rich command-line interface.

![image](https://github.com/user-attachments/assets/15a3a5b3-7e6d-4d7a-8b4e-4e411b0e004a)

## Features

- **Multi-Session Management**: Start new conversations or continue previous ones. Each session is automatically titled based on the first message.
- **Advanced Memory System**:
    - **Short-Term**: Full conversation history is maintained for each session.
    - **Long-Term**: The AI automatically identifies and saves key information in a structured, hierarchical format (Category → Shell → Details).
    - **Memory Injection**: Choose to load long-term memories into a new session's context.
    - **Semantic Search**: Search your long-term memories based on meaning, not just keywords.
- **Rich Terminal UI**: A visually appealing and user-friendly interface built with `rich`.
- **Comprehensive Commands**: Manage sessions and memories with a simple command system.
- **Session Export**: Export your conversations to Markdown or JSON.
- **Cross-Platform**: Works on Windows, macOS, and Linux.

## Setup and Installation

### 1. Prerequisites
- Python 3.11+
- Git

### 2. Clone the Repository
Clone this repository to your local machine:
```bash
git clone <repository_url>
cd <repository_directory>
```

### 3. Install Dependencies
It's recommended to use a virtual environment.
```bash
# Create a virtual environment
python -m venv venv

# Activate it
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate

# Install the required packages
pip install -r requirements.txt
```

### 4. Set Up Your API Key
The chatbot requires a Google Gemini API key.

1.  Create a file named `.env` in the root of the project directory. You can do this by copying the example file:
    ```bash
    cp .env.example .env
    ```
2.  Open the `.env` file and replace the placeholder with one or more of your Gemini API keys, separated by commas.
    ```
    GEMINI_API_KEYS="AIzaSy...key1,AIzaSy...key2"
    ```

## How to Run
Once you have completed the setup, you can run the chatbot from your terminal:
```bash
python -m chatbot.main
```

## Commands

| Command | Description |
|---|---|
| `/new` | Start a new chat session. |
| `/list` | List all available sessions. |
| `/switch [id]` | Switch to a specific session by its ID. |
| `/export [md|json]` | Export the current session to a Markdown or JSON file. |
| `/mem list` | List all stored long-term memories. |
| `/mem search [query]` | Search memories using semantic search. |
| `/mem delete [id]` | Delete a memory by its ID. |
| `/mem summarize [id]`| Get an AI-generated summary of a memory. |
| `/help` | Show the list of available commands. |
| `/exit` | Quit the chatbot application. |


## Creating a Desktop Shortcut

You can create a shortcut to launch the chatbot directly from your desktop.

### Windows
1.  **Create a batch script**: Create a file named `run_chatbot.bat` in the project's root directory with the following content. Make sure to replace `<path_to_your_project>` with the absolute path to the project directory.
    ```batch
    @echo off
    cd /d "<path_to_your_project>"
    call venv\Scripts\activate
    python -m chatbot.main
    ```
2.  **Create the shortcut**:
    - Right-click on your desktop and select `New` -> `Shortcut`.
    - For the location, browse to or enter the full path to `run_chatbot.bat`.
    - Click `Next` and give your shortcut a name (e.g., "Gemini Chatbot").
    - (Optional) You can change the icon by right-clicking the shortcut, going to `Properties` -> `Change Icon`, and selecting a suitable icon.

### macOS
1.  **Create a shell script**: Create a file named `run_chatbot.sh` in the project's root directory. Make it executable (`chmod +x run_chatbot.sh`).
    ```sh
    #!/bin/bash
    cd "<path_to_your_project>"
    source venv/bin/activate
    python -m chatbot.main
    ```
2.  **Create an Automator Application**:
    - Open the `Automator` app.
    - Choose `File` -> `New` and select `Application`.
    - In the search bar, find `Run Shell Script` and drag it to the right-hand panel.
    - Paste the full path to your `run_chatbot.sh` script into the box.
    - Save the application to your Desktop or Applications folder with a name like "Gemini Chatbot".

### Linux (GNOME/KDE)
1.  **Create a shell script**: Follow step 1 from the macOS instructions to create and `chmod +x` your `run_chatbot.sh` script.
2.  **Create a `.desktop` file**: Create a file named `gemini-chatbot.desktop` on your desktop or in `~/.local/share/applications/`.
    ```ini
    [Desktop Entry]
    Version=1.0
    Name=Gemini Chatbot
    Comment=Terminal-based AI Chatbot
    Exec=gnome-terminal -- /bin/bash -c '"<path_to_your_project>/run_chatbot.sh"'
    Icon=<path_to_an_icon_file>
    Terminal=false
    Type=Application
    Categories=Utility;
    ```
    - Replace `<path_to_your_project>` with the absolute path to the project directory.
    - For `Exec`, if you are not using `gnome-terminal`, replace it with your terminal emulator of choice (e.g., `konsole -e`, `xterm -e`).
    - Make the `.desktop` file executable: `chmod +x gemini-chatbot.desktop`.
