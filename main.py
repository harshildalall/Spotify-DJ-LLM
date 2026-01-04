from fastapi import FastAPI
import csv
from llm import generate_json

app = FastAPI()

# -------------------------
# Load songs at startup
# -------------------------
songs = []

with open("songs.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        songs.append(row)


# -------------------------
# Scoring function
# -------------------------
def score_song(song, prefs):
    score = 0

    if song["genre"] == prefs["genre"]:
        score += 3
    if song["mood"] == prefs["mood"]:
        score += 2
    if song["energy"] == prefs["energy"]:
        score += 1
    if song["tempo"] == prefs["tempo"]:
        score += 1

    return score


# -------------------------
# DJ endpoint
# -------------------------
@app.post("/dj")
def dj(request: dict):
    prompt = request["prompt"]

    try:
        prefs = generate_json(prompt)
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

    ranked = []

    for song in songs:
        score = score_song(song, prefs)
        if score > 0:
            ranked.append({
                "song": song["song"],
                "artist": song["artist"],
                "score": score
            })

    ranked.sort(key=lambda x: x["score"], reverse=True)

    return {
        "success": True,
        "prompt": prompt,
        "preferences": prefs,
        "queue": ranked[:10]
    }
