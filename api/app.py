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


def reciprocal_rank_fusion(*ranked_lists, k=60, limit=50):
    """Merge ranked lists: each item scores sum(1 / (k + rank)) across lists.

    Items ranked highly by either method rise to the top, and items that
    appear in both lists get a boost. k=60 is the standard default.
    """
    scores = {}
    for ranked in ranked_lists:
        for rank, item in enumerate(ranked, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    return [item for item, _ in sorted(scores.items(), key=lambda x: x[1], reverse=True)][:limit]


@app.route("/candidates", methods=["GET"])
def candidates():
    title = request.args.get("title", "").strip()
    mode = request.args.get("mode", "hybrid")  # hybrid | collaborative | semantic
    if not title:
        return jsonify({"error": "title required"}), 400
    if mode not in ("hybrid", "collaborative", "semantic"):
        return jsonify({"error": "mode must be hybrid, collaborative, or semantic"}), 400

    anime = find_anime_by_title(title)
    if anime is None:
        return jsonify({"error": f"Anime '{title}' not found"}), 404

    collab = anime.get("collab_candidates") or []
    semantic = semantic_candidates(anime) if mode != "collaborative" else []

    if mode == "collaborative":
        candidate_ids, method = collab, "collaborative"
    elif mode == "semantic" or not collab:
        # No ratings data for this title (cold start): semantic only.
        candidate_ids, method = semantic, "semantic"
    else:
        candidate_ids, method = reciprocal_rank_fusion(collab, semantic), "hybrid"

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