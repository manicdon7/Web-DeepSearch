# index.py (CONVERTED TO A STREAMLIT APP)

import streamlit as st
from transformers import pipeline, set_seed
import torch

# --- Model Loading (Cached for performance) ---
@st.cache_resource
def load_model():
    print("[INFO] Loading instruction-following model...")
    return pipeline(
        "text2text-generation",
        model="google/flan-t5-small",
        torch_dtype=torch.float32
    )

st.set_page_config(layout="wide")
st.title("🤖 AI Instruction API Interface")

# --- Load Model ---
try:
    instructor = load_model()
    set_seed(42)
except Exception as e:
    st.error(f"Could not load model. Error: {e}")
    st.stop()

# --- User Interface ---
st.subheader("Provide Text and an Instruction")
instruction = st.text_input(
    "Instruction:",
    "Summarize the following text concisely."
)
text = st.text_area("Text:", height=300, placeholder="Paste text here...")

if st.button("Process Text", type="primary"):
    if text.strip():
        with st.spinner("AI is working..."):
            try:
                # This simple version doesn't include chunking, but you could add it
                prompt = f"Instruction: {instruction.strip()}\n\nContext: {text.strip()}\n\nAnswer:"
                result = instructor(prompt, max_length=256, min_length=30)[0]['generated_text']
                st.subheader("✅ Result")
                st.success(result)
            except Exception as e:
                st.error(f"An error occurred: {e}")
    else:
        st.warning("Please enter some text to process.")
