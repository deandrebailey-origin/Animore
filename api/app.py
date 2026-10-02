"""
Lightweight Flask API for Animore.

Instead of loading the 1M-row ratings CSV and refitting KNN on every request,
this reads the collaborative-filtering neighbors that offline_candidates_save.py
already precomputed and stored on each anime document as `collab_candidates`.

Run from the api/ folder:  python app.py
"""
import os
import re

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient

load_dotenv()

collection = MongoClient(os.environ["MONGODB_URI"]).get_database("anime").anime_anilist

app = Flask(__name__)
CORS(app)


def find_anime_by_title(title):
    """Exact, case-insensitive match on the English or romaji title."""
    pattern = re.compile(f"^{re.escape(title)}$", re.IGNORECASE)
    return collection.find_one(
        {"$or": [{"title.english": pattern}, {"title.romaji": pattern}]},
        {"_id": 0, "mal_id": 1, "collab_candidates": 1, "embedding": 1},
    )


def semantic_candidates(anime, k=50):
    """Fallback: nearest neighbors by embedding via Atlas Vector Search."""
    if not anime.get("embedding"):
        return []
    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index",
                "path": "embedding",
                "queryVector": anime["embedding"],
                "numCandidates": 200,
                "limit": k + 1,
            }
        },
        {"$project": {"_id": 0, "mal_id": 1}},
    ]
    ids = [doc.get("mal_id") for doc in collection.aggregate(pipeline)]
    return [i for i in ids if i is not None and i != anime.get("mal_id")][:k]


@app.route("/candidates", methods=["GET"])
def candidates():
    title = request.args.get("title", "").strip()
    if not title:
        return jsonify({"error": "title required"}), 400

    anime = find_anime_by_title(title)
    if anime is None:
        return jsonify({"error": f"Anime '{title}' not found"}), 404

    # Prefer collaborative filtering; fall back to semantic search when a title
    # has no precomputed neighbors (the cold-start problem).
    candidate_ids = anime.get("collab_candidates") or []
    method = "collaborative"
    if not candidate_ids:
        candidate_ids = semantic_candidates(anime)
        method = "semantic"

    return jsonify({
        "source_id": anime.get("mal_id"),
        "candidate_ids": candidate_ids,
        "method": method,
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_DEBUG") == "1")
