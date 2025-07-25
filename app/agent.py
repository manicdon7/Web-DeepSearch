import pollinations as ai

def get_ai_synthesis(query: str, sources: list[dict]):
    """
    Synthesizes a comprehensive answer from multiple sources using an AI model.
    """
    # Combine the content from all sources into a single context string.
    context = ""
    for i, source in enumerate(sources):
        context += f"--- Source {i+1} (from {source['url']}) ---\n"
        # Truncate content of each source to keep the prompt manageable
        context += source['content'][:2000]
        context += "\n\n"

    # A more advanced prompt for synthesis.
    prompt = (
        f"You are a helpful research assistant. Your goal is to provide a single, comprehensive answer to the user's question by synthesizing information from the multiple sources provided below.\n\n"
        f"User's Question: \"{query}\"\n\n"
        f"--- Provided Sources ---\n"
        f"{context}"
        f"--- End of Sources ---\n\n"
        f"Based on all the information above, please provide a single, well-structured answer to the user's question:"
    )

    try:
        model = ai.Text(model="openai")
        answer = model(prompt)
        return answer
    except Exception as e:
        print(f"Error communicating with Pollinations.ai: {e}")
        return "Could not generate an answer."
