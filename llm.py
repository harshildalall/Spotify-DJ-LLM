import json
import re
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

#model setup (cpu only)
MODEL_ID = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    dtype="float32",        # FIXED (no torch_dtype)
    device_map="cpu"        # Uses accelerate internally
)

#important: no device argument here
generator = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer
)

#extracting json
def extract_json(text: str):
    #remove markdown code blocks if present
    text = text.strip()
    
    #remove ```json or ``` at the start
    if text.startswith("```"):
        lines = text.split("\n")
        #remove first line if it's just ``` or ```json
        if lines[0].strip() in ["```", "```json", "```JSON"]:
            lines = lines[1:]
        #remove last line if it's just ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    
    #find JSON object in text
    match = re.search(r"\{[\s\S]*?\}", text)
    if not match:
        raise ValueError("No JSON found in LLM output:\n" + text)
    
    json_str = match.group()
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in LLM output:\n{json_str}\nError: {str(e)}")


#calling LLM
def generate_json(user_prompt: str):
    prompt = f"""
Return ONLY valid JSON.
No explanations.
No markdown.
No extra text.

Keys:
- genre: main genre (string, empty if not specified)
- mood: main mood (string, empty if not specified)
- energy: "low", "medium", or "high" (empty string if not specified)
- tempo: "slow", "medium", or "fast" (empty string if not specified)
- artist: artist name if mentioned in prompt (empty string if not specified)
- associated_words: array of related words/synonyms for genre, mood, energy, and tempo that capture similar vibes. Include semantic relationships like "chill" -> ["relaxed", "reflective", "calm", "smooth", "laid-back"]

Important:
- CRITICAL: If prompt mentions an artist name (e.g., "travis scott rap mix", "frank ocean mix", "drake songs"), you MUST extract the artist name in the "artist" field. Look for names like: travis scott, frank ocean, drake, taylor swift, the weeknd, etc.
- Generate extensive associated_words list capturing semantic relationships, but avoid duplicates
- For "late night rnb", associated_words should include: ["chill", "smooth", "relaxed", "reflective", "calm", "groovy", "laid-back", "mellow", "romantic", "soulful"]
- Keep associated_words unique - do not repeat the same word multiple times

Examples:
- "travis scott rap mix" -> {{"genre":"rap","mood":"","energy":"","tempo":"","artist":"travis scott","associated_words":["hype","energetic","aggressive","confident","dark","hype"]}}
- "frank ocean mix" -> {{"genre":"r&b","mood":"","energy":"","tempo":"","artist":"frank ocean","associated_words":["chill","reflective","smooth","dreamy","romantic"]}}
- "late night chill rnb" -> {{"genre":"r&b","mood":"chill","energy":"low","tempo":"slow","artist":"","associated_words":["relaxed","reflective","smooth","calm","groovy","laid-back","mellow","romantic","soulful","dreamy","moody"]}}

User request: {user_prompt}

JSON:
"""

    output = generator(
        prompt,
        max_new_tokens=200,
        do_sample=True,
        temperature=0.7,
        return_full_text=False
    )[0]["generated_text"]

    result = extract_json(output)
    
    #ensure all fields exist with defaults
    if "associated_words" not in result:
        result["associated_words"] = []
    else:
        #deduplicate and clean associated words
        seen = set()
        cleaned_words = []
        for word in result["associated_words"]:
            if word and isinstance(word, str):
                word_clean = word.strip().lower()
                if word_clean and word_clean not in seen:
                    seen.add(word_clean)
                    cleaned_words.append(word_clean)
        result["associated_words"] = cleaned_words
    
    if "artist" not in result:
        result["artist"] = ""
    else:
        #clean artist name
        result["artist"] = result["artist"].strip()
    
    #try to extract artist from prompt if LLM didn't catch
    if not result["artist"] and user_prompt:
        #common artist name patterns in prompts
        import re
        #look for patterns like "artist name mix", "artist name songs", etc.
        prompt_lower = user_prompt.lower()
        #list of known artists (extracted from common patterns) -- improve algorithm for this
        known_artists = [
            "travis scott", "frank ocean", "drake", "taylor swift", "the weeknd",
            "kanye west", "kendrick lamar", "arctic monkeys", "childish gambino",
            "brent faiyaz", "bryson tiller", "juice wrld", "post malone",
            "sza", "khalid", "tame impala", "the 1975", "mgmt", "bon iver"
        ]
        for artist in known_artists:
            if artist in prompt_lower:
                #extract full artist name from prompt
                pattern = rf"\b{re.escape(artist)}\b"
                match = re.search(pattern, user_prompt, re.IGNORECASE)
                if match:
                    result["artist"] = match.group().strip()
                    break
    
    if "genre" not in result:
        result["genre"] = ""
    if "mood" not in result:
        result["mood"] = ""
    if "energy" not in result:
        result["energy"] = ""
    if "tempo" not in result:
        result["tempo"] = ""
    
    return result
    
