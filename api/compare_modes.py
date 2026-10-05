"""
Compare the top recommendations from each method side by side, as titles.

Flask must be running first (python app.py). Then, from the api/ folder:
    python compare_modes.py "Cowboy Bebop"
"""
import json
import os
import sys
import urllib.parse
import urllib.request

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()
collection = MongoClient(os.environ["MONGODB_URI"]).anime.anime_anilist

title = sys.argv[1] if len(sys.argv) > 1 else "Cowboy Bebop"
TOP_N = 10

for mode in ["collaborative", "semantic", "hybrid"]:
    # Ask Flask for this mode's recommendations
    query = urllib.parse.urlencode({"title": title, "mode": mode})
    with urllib.request.urlopen(f"http://localhost:5000/candidates?{query}") as resp:
        data = json.load(resp)

    ids = data["candidate_ids"][:TOP_N]

    # Look up the titles for those IDs in one database query
    docs = collection.find({"mal_id": {"$in": ids}}, {"_id": 0, "mal_id": 1, "title": 1})
    titles = {d["mal_id"]: d.get("title", {}) for d in docs}

    print(f"\n{mode.upper()}  (method used: {data['method']})")
    for rank, mal_id in enumerate(ids, start=1):
        t = titles.get(mal_id, {})
        print(f"  {rank:2}. {t.get('english') or t.get('romaji') or mal_id}")
