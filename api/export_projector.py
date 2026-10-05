"""
Export anime embeddings for the TensorFlow Embedding Projector
(projector.tensorflow.org).

Creates two files:
  vectors.tsv   one row per anime, 384 tab-separated numbers, no header
  metadata.tsv  one row per anime (same order), with a header row

Run from the api/ folder:
    python export_projector.py --limit 5000
"""
import argparse
import os

from dotenv import load_dotenv
from pymongo import MongoClient


def clean(text):
    """Tabs and newlines would break the TSV format, so replace them."""
    return str(text).replace("\t", " ").replace("\n", " ").strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5000, help="most popular N anime; 0 = all")
    args = parser.parse_args()

    load_dotenv()
    collection = MongoClient(os.environ["MONGODB_URI"]).anime.anime_anilist

    cursor = collection.find(
        {"embedding": {"$exists": True}},
        {"_id": 0, "embedding": 1, "title": 1, "genres": 1, "popularity": 1, "seasonYear": 1},
    ).sort("popularity", -1)  # most popular first
    if args.limit:
        cursor = cursor.limit(args.limit)

    count = 0
    with open("vectors.tsv", "w") as vec_file, open("metadata.tsv", "w") as meta_file:
        meta_file.write("title\tprimary_genre\tgenres\tpopularity\tyear\n")
        for doc in cursor:
            title = doc.get("title") or {}
            genres = doc.get("genres") or []
            vec_file.write("\t".join(f"{x:.5f}" for x in doc["embedding"]) + "\n")
            meta_file.write("\t".join([
                clean(title.get("english") or title.get("romaji") or "Unknown"),
                clean(genres[0] if genres else "None"),
                clean(", ".join(genres)),
                str(doc.get("popularity") or 0),
                str(doc.get("seasonYear") or ""),
            ]) + "\n")
            count += 1

    print(f"Wrote {count:,} anime to vectors.tsv and metadata.tsv")


if __name__ == "__main__":
    main()
