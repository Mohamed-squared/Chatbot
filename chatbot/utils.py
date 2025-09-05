def count_tokens(text: str) -> int:
    """
    A simple approximation of token counting.
    A common heuristic is ~4 characters per token.
    """
    return len(text) // 4

def format_memories_for_prompt(memories: list) -> str:
    """Formats a list of memory records into a single string for a prompt."""
    return "\n".join([f"- {m['category']} -> {m['shell']}: {m['details']}" for m in memories])

if __name__ == '__main__':
    test_text = "This is a sample sentence for token counting."
    print(f"Text: '{test_text}'")
    print(f"Approximate tokens: {count_tokens(test_text)}")
