import time
import pollinations as ai

def get_ai_synthesis(query: str, sources: list[dict], max_retries: int = 3, backoff_factor: float = 2.0) -> str:
    """
    Synthesizes a comprehensive answer using Pollinations.ai, with robust
    retry logic for transient server errors like '502 Bad Gateway'.
    """
    # 1. Build the prompt from the gathered sources
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

    # 2. Attempt to call the AI model with an exponential backoff retry strategy
    model = ai.Text(model="openai")
    for attempt in range(max_retries):
        try:
            # If the call succeeds, return the answer immediately
            return model(prompt)
        except Exception as e:
            err_str = str(e).lower()
            # Check for specific, retry-able errors (e.g., 5xx server errors)
            is_retryable = "502" in err_str or "bad gateway" in err_str or "server error" in err_str

            if is_retryable and attempt < max_retries - 1:
                # Calculate wait time with exponential backoff (e.g., 2s, 4s, 8s)
                wait_time = backoff_factor ** (attempt + 1)
                print(
                    f"Pollinations.ai server error. Retrying in {wait_time:.1f}s... "
                    f"(Attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(wait_time)
            else:
                # If it's the last attempt or a non-retryable error, fail permanently
                print(f"Pollinations.ai final error after {attempt + 1} attempts: {e}")
                break  # Exit the loop to return the failure message

    return "Could not generate an answer after multiple attempts."
