import time
import pollinations as ai

def get_ai_synthesis(query: str, sources: list[dict], max_retries: int = 5, backoff_factor: float = 5.0) -> str:
    """
    Synthesizes a comprehensive answer from multiple sources using Pollinations.ai,
    with retry logic for transient errors (e.g., HTTP 5xx).
    """
    # Build the combined context from all sources
    context = ""
    for i, source in enumerate(sources, start=1):
        context += f"--- Source {i} (from {source['url']}) ---\n"
        context += source["content"][:2000] + "\n\n"

    prompt = (
        "You are a helpful research assistant. Your goal is to provide a single, "
        "comprehensive answer to the user's question by synthesizing information from "
        "the multiple sources provided below.\n\n"
        f"User's Question: \"{query}\"\n\n"
        "--- Provided Sources ---\n"
        f"{context}"
        "--- End of Sources ---\n\n"
        "Based on all the information above, please provide a single, well-structured "
        "answer to the user's question:"
    )

    model = ai.Text(model="openai")
    attempt = 0
    while attempt < max_retries:
        try:
            return model(prompt)
        except Exception as e:
            attempt += 1
            err_str = str(e)
            # Retry only on server-side errors (5xx) or network timeouts
            if attempt < max_retries and ("502" in err_str or "5" == err_str[:1] or "timeout" in err_str.lower()):
                wait_time = backoff_factor ** attempt
                print(f"Pollinations.ai retry {attempt}/{max_retries} in {wait_time}s due to error: {e}")
                time.sleep(wait_time)
                continue
            print(f"Pollinations.ai final error on attempt {attempt}: {e}")
            break

    return "Could not generate an answer."
