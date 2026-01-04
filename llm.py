import json
import re
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

# -------------------------
# Model setup (CPU only)
# -------------------------
MODEL_ID = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    dtype="float32",        # FIXED (no torch_dtype)
    device_map="cpu"        # Uses accelerate internally
)

# IMPORTANT: no `device` argument here
generator = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer
)

# -------------------------
# JSON extraction
# -------------------------
def extract_json(text: str):
    match = re.search(r"\{[\s\S]*?\}", text)
    if not match:
        raise ValueError("No JSON found in LLM output:\n" + text)
    return json.loads(match.group())


# -------------------------
# LLM call
# -------------------------
def generate_json(user_prompt: str):
    prompt = f"""
Return ONLY valid JSON.
No explanations.
No markdown.
No extra text.

Keys:
- genre
- mood
- energy ("low", "medium", "high")
- tempo ("slow", "medium", "fast")

Example:
{{"genre":"rnb","mood":"chill","energy":"low","tempo":"medium"}}

User request: {user_prompt}

JSON:
"""

    output = generator(
        prompt,
        max_new_tokens=150,
        do_sample=True,
        temperature=0.7,
        return_full_text=False
    )[0]["generated_text"]

    return extract_json(output)
