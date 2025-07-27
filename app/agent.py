import time
import pollinations as ai
from huggingface_hub import InferenceClient
from .config import settings

def huggingface_fallback(prompt: str) -> str | None:
    """
    Uses the Hugging Face Inference API as a fallback if Pollinations fails.
    """
    print("Pollinations failed. Falling back to Hugging Face Inference API...")
    try:
        # Initialize the client with your token from the settings
        client = InferenceClient(token=settings.huggingface_token)
        
        # Call a powerful, open-source model like Mistral-7B
        response = client.chat_completion(
            messages=[
                {"role": "user", "content": prompt}
            ],
            model="mistralai/Mistral-7B-Instruct-v0.2",
            max_tokens=512,  # Maximum number of tokens to generate in the response
        )
        print(response.choices[0].message.content.strip())
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Hugging Face fallback also failed: {e}")
        return None # Return None on failure

def get_ai_synthesis(query: str, sources: list[dict], max_retries: int = 5, backoff_factor: float = 2.0) -> str:
    """
    Synthesizes an answer using Pollinations.ai, with a fallback to Hugging Face.
    """
    context = ""
    for i, source in enumerate(sources, start=1):
        context += f"--- Source {i} (from {source['url']}) ---\n"
        context += source["main_content"][:2000] + "\n\n"

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

    # --- Attempt 1: Pollinations.ai with retries ---
    model = ai.Text(model="openai")
    for attempt in range(max_retries):
        try:
            return model(prompt)
        except Exception as e:
            err_str = str(e).lower()
            is_retryable = "502" in err_str or "bad gateway" in err_str or "server error" in err_str
            if is_retryable and attempt < max_retries - 1:
                wait_time = backoff_factor ** (attempt + 1)
                print(f"Pollinations.ai server error. Retrying in {wait_time:.1f}s...")
                time.sleep(wait_time)
            else:
                break # Exit loop if error is not retryable or retries are exhausted

    # --- Attempt 2: Hugging Face Fallback ---
    answer = huggingface_fallback(prompt)
    if answer:
        return answer

    # If all services fail
    return "Could not generate an answer after multiple attempts from all available services."
