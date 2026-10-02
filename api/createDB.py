import os
from dotenv import load_dotenv
load_dotenv()
import requests
import time
from pymongo import MongoClient

# MongoDB connection
uri = os.environ["MONGODB_URI"]
client = MongoClient(uri)
db = client["anime"]
collection = db["anime_anilist"]

# Wipe old collection
collection.drop()

# GraphQL query
query = """
query ($page: Int, $perPage: Int) {
  Page(page: $page, perPage: $perPage) {
    media(type: ANIME) {
      id
      idMal
      title {
        romaji
        english
        native
      }
      description
      episodes
      status
      season
      seasonYear
      genres
      tags {
        name
        rank
        isAdult
      }
      averageScore
      popularity
    }
  }
}
"""

url = "https://graphql.anilist.co"

page = 1
perPage = 50  # AniList max = 50

while True:
    variables = {"page": page, "perPage": perPage}
    response = requests.post(url, json={"query": query, "variables": variables})
    data = response.json()

    if "errors" in data:
        print(f"❌ Error on page {page}:", data["errors"])
        break

    page_data = data.get("data", {}).get("Page", {})
    media = page_data.get("media", [])

    if not media:
        print("✅ No more anime found, stopping.")
        break

    for anime in media:
        doc = {
            "anilist_id": anime["id"],
            "mal_id": anime.get("idMal"),
            "title": anime.get("title"),
            "description": anime.get("description"),
            "episodes": anime.get("episodes"),
            "status": anime.get("status"),
            "season": anime.get("season"),
            "seasonYear": anime.get("seasonYear"),
            "genres": anime.get("genres"),
            "tags": anime.get("tags"),
            "averageScore": anime.get("averageScore"),
            "popularity": anime.get("popularity")
        }
        collection.insert_one(doc)

    print(f"✅ Inserted page {page} ({len(media)} anime)")
    page += 1
    time.sleep(0.5)  # prevent rate limit