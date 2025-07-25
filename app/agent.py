import pollinations as ai

# --- MONKEY PATCH TO FIX LIBRARY BUG ---
# The pollinations.ai library has a bug in its version checker that crashes
# the app. We disable the faulty function by replacing it with one that
# does nothing. This must be done immediately after the import.
ai.get_latest = lambda: None
# --- END OF PATCH ---

def get_ai_synthesis(query: str, sources: list[dict]):
    """
    Synthesizes a comprehensive answer from multiple sources using an AI model.
    """
    context = ""
    for i, source in enumerate(sources):
        context += f"--- Source {i+1} (from {source['url']}) ---\n"
        context += source['content'][:2000]
        context += "\n\n"

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
