🎧 Spotify DJ — Local LLM Music Recommender

A fully local music recommender that uses a TinyLlama LLM + FastAPI to turn natural-language prompts into a playlist based on a curated song dataset.

🚀 What It Does

Converts prompts like “late night chill rnb” into structured JSON

Matches JSON to a CSV of ~100 songs

Returns a recommended queue

Runs entirely local (no external APIs or keys)

📁 Project Structure
spotify_dj/
├── main.py        # FastAPI backend + song matching
├── llm.py         # TinyLlama JSON generator
├── songs.csv      # Song dataset
└── requirements.txt

▶️ Run Locally
git clone <repo-url>
cd spotify_dj
python3.11 -m venv venv311
source venv311/bin/activate
pip install -r requirements.txt
uvicorn main:app --port 62515 --reload


Test endpoint:

curl -X POST "http://127.0.0.1:62515/dj" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"late night chill rnb"}'

🧠 LLM

Uses TinyLlama/TinyLlama-1.1B-Chat-v1.0 via transformers for JSON generation.

📊 Dataset

songs.csv includes attributes:
song, artist, genre, energy, mood, tempo.
