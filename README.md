Spotify DJ+ - Improved Spotify DJ Feature

Spotify DJ is a local-first music recommendation engine that uses a TinyLlama LLM + FastAPI backend to convert any natural-language vibe (“late night chill rnb”) into structured JSON, then matches it to a curated catalog of 100+ songs.

Run Locally:

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
