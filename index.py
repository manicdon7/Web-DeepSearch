# index.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import pipeline, set_seed
import torch
import uvicorn

# --- App and Model Initialization ---
app = FastAPI()

# Initialize the single, powerful, and LIGHTWEIGHT instruction-following model
print("[INFO] Loading instruction-following model: google/flan-t5-small...")
instructor = pipeline(
    "text2text-generation",
    model="google/flan-t5-small", # <-- THE FIX IS HERE! Swapped to a smaller model.
    torch_dtype=torch.float32 # Use float32 for CPU, bfloat16 is better for modern GPUs
)
set_seed(42)
print("[INFO] Model loaded successfully!")

# --- Pydantic Request Model ---
class InstructRequest(BaseModel):
    text: str
    instruction: str = "Summarize the following text concisely."
    max_length: int = 256
    min_length: int = 30

# --- Helper Function for Chunking ---
def get_chunks(text: str, max_words: int):
    words = text.split()
    for i in range(0, len(words), max_words):
        yield ' '.join(words[i:i+max_words])

# --- API Endpoints ---
@app.get("/")
def read_root():
    return {"message": "AI Instruction API is running! Use the /instruct endpoint."}

@app.get("/healthz")
def health_check():
    return {"status": "ok"}

@app.post("/instruct")
def process_instruction(request: InstructRequest):
    """
    A single, powerful endpoint that follows an instruction on a given text.
    """
    try:
        if not request.text.strip():
            raise HTTPException(status_code=400, detail="Input text cannot be empty.")
        words = request.text.split()
        input_length = len(words)
        print(f"[INFO] Received request. Instruction: '{request.instruction}', Input length: {input_length} words.")
        prompt = f"Instruction: {request.instruction.strip()}\n\nContext: {request.text.strip()}\n\nAnswer:"
        max_chunk_size = 400 # Safe chunk size for t5-small
        if input_length > max_chunk_size:
            print(f"[INFO] Text is long. Applying map-reduce strategy...")
            chunks = list(get_chunks(request.text, max_chunk_size))
            chunk_prompts = [f"Instruction: {request.instruction.strip()}\n\nContext: {chunk}\n\nAnswer:" for chunk in chunks]
            chunk_summaries = instructor(chunk_prompts, max_length=150, min_length=40, truncation=True)
            combined_summary_text = ' '.join([s['generated_text'] for s in chunk_summaries])
            final_prompt = f"Instruction: {request.instruction.strip()}\n\nContext: {combined_summary_text}\n\nAnswer:"
            final_result = instructor(final_prompt, max_length=request.max_length, min_length=request.min_length)[0]['generated_text']
            return {"result": final_result}
        else:
            result = instructor(prompt, max_length=request.max_length, min_length=request.min_length)[0]['generated_text']
            return {"result": result}
    except Exception as e:
        print(f"[ERROR] An exception occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)