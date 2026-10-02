import os
from dotenv import load_dotenv
load_dotenv()
# embed_anilist.py
from sentence_transformers import SentenceTransformer
from pymongo import MongoClient
import re
import time
import numpy as np

uri = os.environ["MONGODB_URI"]
client = MongoClient(uri)
db = client.get_database("anime")
collection = db["anime_anilist"]   # use your new AniList-based collection

# downloads & loads the minLM model from huggingface
# outputs embeddings of size 384 turns text into vectors of floats that computers can understand
model = SentenceTransformer('all-MiniLM-L6-v2')

# cleans the AniList desctiption text
def clean_text(s:str) -> str:
    """Remove HTML tags and special characters from text."""
    s = re.sub(r'<br\s*/?>', ' ', s)  # Replace <br> tags with space
    s = re.sub(r'<.*?>', '', s)        # Remove other HTML tags
    s = re.sub(r'\s+', ' ', s)         # Replace multiple spaces with single space
    return s.strip()

batch_size = 64
cursor = collection.find({"embedding": {"$exists": False}})  # only fetch docs without embeddings

docs, ids = [], []
for doc in cursor:
    title = ( doc.get("title", {}).get("romaji", "")  # get romaji title
        or doc.get("title", {}).get("english", "")  # or english title
        or doc.get("title", {}).get("native", "")   # or native title
        or "" 
    )

    description = clean_text(doc.get("description", "") or "")
    genres = ", ".join(doc.get("genres", []) * 3) # repeat genres 3 to give them more weight
    tags = [t.get("name") for t in (doc.get("tags") or []) * 2] # repeat tags 2 to give them more weight

    # combines all text fields into one string for embedding

    combined = " ".join([p for p in [title, description, genres, ", ".join(tags)] if p])
    docs.append(combined)
    ids.append(doc["_id"])

    if len(docs) >= batch_size:
        embeddings = model.encode(docs, show_progress_bar=False, batch_size=32)
        for _id, emb in zip(ids, embeddings):
            collection.update_one({"_id": _id}, {"$set": {"embedding": emb.tolist()}})
        print(f"Processed {len(ids)} documents...")
        
        # Reset for next batch

        docs, ids = [], []
        time.sleep(0.2)  # to avoid rate limiting

if docs:
    embeddings = model.encode(docs, show_progress_bar=False, batch_size=32)
    for _id, emb in zip(ids, embeddings):
        collection.update_one({"_id": _id}, {"$set": {"embedding": emb.tolist()}})
    print(f"Processed {len(ids)} documents...")
    