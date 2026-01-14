from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import csv
from llm import generate_json

app = FastAPI()

#add CORS to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#normalizing words by removing fillers
def normalize_word(word):
    """Normalize word for comparison"""
    if not word:
        return ""
    normalized = word.lower().strip().replace("-", " ").replace("_", " ")
    # Normalize common variations
    normalized = normalized.replace("&", "and")
    # Normalize r&b variations - all become "randb" for comparison
    normalized = normalized.replace("r and b", "randb").replace("r&b", "randb").replace("rnb", "randb")
    return normalized

#load songs at startup
songs = []

with open("songs.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        songs.append(row)

#build artist database for related artist finding
artist_genres = {}  # artist -> set of genres
artist_moods = {}   # artist -> set of moods

for song in songs:
    artist = normalize_word(song["artist"])
    genre = normalize_word(song["genre"])
    mood = normalize_word(song["mood"])
    
    if artist not in artist_genres:
        artist_genres[artist] = set()
        artist_moods[artist] = set()
    
    artist_genres[artist].add(genre)
    artist_moods[artist].add(mood)


#semantic word similarity mapping
SEMANTIC_GROUPS = {
    #chill/relaxed group
    "chill": ["relaxed", "reflective", "calm", "smooth", "groovy", "laid-back", "mellow", "soulful", "dreamy", "moody"],
    "relaxed": ["chill", "calm", "smooth", "laid-back", "mellow", "reflective", "groovy"],
    "reflective": ["chill", "calm", "moody", "melancholy", "thoughtful", "sad", "romantic"],
    "calm": ["chill", "relaxed", "mellow", "peaceful", "smooth", "groovy"],
    
    #energetic/hype group
    "hype": ["energetic", "upbeat", "fast", "pumping", "aggressive", "confident"],
    "energetic": ["hype", "upbeat", "fast", "pumping", "aggressive", "rocky"],
    "upbeat": ["energetic", "happy", "feel-good", "fun", "confident"],
    
    #emotional/sad group
    "sad": ["melancholy", "emotional", "moody", "reflective", "romantic"],
    "emotional": ["sad", "melancholy", "moody", "romantic", "reflective"],
    "melancholy": ["sad", "emotional", "moody", "reflective"],
    
    #romantic/dreamy group
    "romantic": ["dreamy", "smooth", "chill", "soulful", "emotional", "calm"],
    "dreamy": ["romantic", "ethereal", "calm", "chill", "mellow", "reflective"],
    
    #late night group
    "late-night": ["chill", "moody", "smooth", "romantic", "dreamy", "reflective", "calm"],
    
    #groovy/smooth group
    "groovy": ["smooth", "chill", "relaxed", "mellow", "laid-back"],
    "smooth": ["groovy", "chill", "relaxed", "romantic", "soulful"],
}

def get_semantic_group(word):
    """Get all semantically related words for a given word"""
    normalized = normalize_word(word)
    related = set()
    
    #direct lookup
    if normalized in SEMANTIC_GROUPS:
        related.update(SEMANTIC_GROUPS[normalized])
    
    #reverse lookup (find groups that contain this word)
    for key, values in SEMANTIC_GROUPS.items():
        if normalized in values:
            related.add(key)
            related.update(values)
    
    return list(related)

#scoring function with word associations
def word_matches(value, target, associated_words):
    """Check if value matches target or any associated word with semantic similarity"""
    if not value or not target:
        return False, False
    
    normalized_value = normalize_word(value)
    normalized_target = normalize_word(target)
    
    #exact match
    if normalized_value == normalized_target:
        return True, True  # (exact_match, any_match)
    
    #check if value contains target or vice versa (partial match)
    if normalized_target and (normalized_target in normalized_value or normalized_value in normalized_target):
        return False, True
    
    #get semantic group for target word
    semantic_group = get_semantic_group(target) if target else []
    
    #check against associated words
    all_related = set(associated_words) if associated_words else set()
    all_related.update(semantic_group)
    
    for assoc_word in all_related:
        if not assoc_word:
            continue
        normalized_assoc = normalize_word(assoc_word)
        if normalized_value == normalized_assoc:
            return False, True
        if normalized_assoc in normalized_value or normalized_value in normalized_assoc:
            return False, True
    
    return False, False

def find_related_artists(target_artist, all_songs):
    """Find artists related to target artist based on genre/mood similarity"""
    target_normalized = normalize_word(target_artist)
    
    if target_normalized not in artist_genres:
        return set()
    
    target_genres = artist_genres[target_normalized]
    target_moods = artist_moods[target_normalized]
    
    related = set()
    for artist, genres in artist_genres.items():
        if artist == target_normalized:
            continue
        
        #check genre overlap
        genre_overlap = genres.intersection(target_genres)
        mood_overlap = artist_moods[artist].intersection(target_moods)
        
        #if shares genre or mood, consider related
        if genre_overlap or mood_overlap:
            related.add(artist)
    
    return related

def score_song(song, prefs, related_artists=None):
    score = 0
    associated_words = prefs.get("associated_words", [])
    related_artists = related_artists or set()
    
    #matching artist name - highest priority (10 points for exact, 5 for related)
    song_artist = normalize_word(song["artist"])
    requested_artist = normalize_word(prefs.get("artist", ""))
    
    if requested_artist:
        if song_artist == requested_artist:
            score += 10.0  # Exact artist match
        elif song_artist in related_artists:
            score += 5.0   # Related artist match
        elif requested_artist in song_artist or song_artist in requested_artist:
            score += 5.0   # Partial artist name match
    
    #word association matching - high priority (weighted more than tempo/energy)
    song_attributes = {
        "genre": normalize_word(song["genre"]),
        "mood": normalize_word(song["mood"]),
        "energy": normalize_word(song["energy"]),
        "tempo": normalize_word(song["tempo"])
    }
    
    #build comprehensive set of all related words with semantic expansion
    all_related = set(associated_words) if associated_words else set()
    
    #add semantic group for each associated word
    for assoc_word in list(all_related):
        if assoc_word:
            all_related.update(get_semantic_group(assoc_word))
    
    #add semantic groups for the requested genre/mood
    if prefs.get("genre"):
        all_related.update(get_semantic_group(prefs["genre"]))
    if prefs.get("mood"):
        all_related.update(get_semantic_group(prefs["mood"]))
    
    #check each song attribute against all related words
    genre_matched = False
    mood_matched = False
    
    for attr_type, attr_value in song_attributes.items():
        if not attr_value:
            continue
        
        #check if attribute matches any related word
        for related_word in all_related:
            if not related_word:
                continue
            normalized_related = normalize_word(related_word)
            
            if (attr_value == normalized_related or 
                normalized_related in attr_value or 
                attr_value in normalized_related):
                
                #genre associations - 4 points
                if attr_type == "genre" and not genre_matched:
                    score += 4.0
                    genre_matched = True
                    break
                
                #mood associations - 3 points
                elif attr_type == "mood" and not mood_matched:
                    score += 3.0
                    mood_matched = True
                    break
                
                #energy/Tempo associations - 1 point each (less than genre/mood)
                elif attr_type == "energy":
                    score += 1.0
                    break
                elif attr_type == "tempo":
                    score += 1.0
                    break
    
    #exact matches - medium priority (less than associations)
    # Genre exact match - 2 points (reduced from 3)
    if prefs.get("genre") and word_matches(song["genre"], prefs["genre"], [])[0]:
        score += 2.0
    
    #mood exact match - 1.5 points (reduced from 2)
    if prefs.get("mood") and word_matches(song["mood"], prefs["mood"], [])[0]:
        score += 1.5
    
    #energy exact match - 0.5 points (reduced from 1)
    if prefs.get("energy") and word_matches(song["energy"], prefs["energy"], [])[0]:
        score += 0.5
    
    #tempo exact match - 0.5 points (reduced from 1)
    if prefs.get("tempo") and word_matches(song["tempo"], prefs["tempo"], [])[0]:
        score += 0.5
    
    #bonus for multiple attribute matches with associated words
    matches_count = 0
    for attr_value in song_attributes.values():
        if not attr_value:
            continue
        for assoc_word in associated_words:
            if not assoc_word:
                continue
            normalized_assoc = normalize_word(assoc_word)
            if normalized_assoc in attr_value or attr_value in normalized_assoc:
                matches_count += 1
                break
    
    if matches_count >= 2:
        score += 1.0  # Bonus for multiple associations
    
    return round(score, 2)


#DJ endpoint
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

    #find related artists if an artist is specified
    related_artists = set()
    requested_artist = prefs.get("artist", "").strip()
    if requested_artist:
        related_artists = find_related_artists(requested_artist, songs)

    ranked = []

    for song in songs:
        score = score_song(song, prefs, related_artists)
        if score > 0:
            ranked.append({
                "song": song["song"],
                "artist": song["artist"],
                "score": score
            })

    ranked.sort(key=lambda x: x["score"], reverse=True)

    #return top 25-30 songs based on match (prioritize higher scores)
    #take top 25 by default, but extend to 30 if scores are close
    if len(ranked) == 0:
        final_queue = []
    else:
        top_score = ranked[0]["score"]
        #use a relative threshold (e.g., 50% of top score) for fractional scores
        threshold = max(0.5, top_score * 0.5)  # Include songs at least 50% of top score
        
        final_queue = [s for s in ranked if s["score"] >= threshold][:30]
        #ensure at least 20 if we have them, but cap at 30
        if len(final_queue) < 20:
            final_queue = ranked[:min(30, len(ranked))]
        else:
            final_queue = final_queue[:min(30, len(final_queue))]

    return {
        "success": True,
        "prompt": prompt,
        "preferences": prefs,
        "queue": final_queue
    }


#deliver static frontend files (must be after API routes)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
