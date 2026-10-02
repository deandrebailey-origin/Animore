import os
from dotenv import load_dotenv
load_dotenv()
# Fast and scalable ANN library for Python using FAISS instead of HNSWLib
# Why: MongoDB stores embeddings as lists, but numpy arrays are faster for calculations
# What numpy arrays are: n-dimensional arrays, efficient for numerical computations
# Math operations on arrays are faster than on lists
# Similarity dot products, distance calculations, etc. are good
# However, for large datasets, linear search is too slow
# ANN = Approximate Nearest Neighbors
# Instead of exact nearest neighbors, we get approximate ones much faster
# FAISS builds optimized indexes for fast similarity searches
# Searching becomes much faster (logarithmic time in some approximate modes)

import faiss
import numpy as np
from pymongo import MongoClient
import random

# -------------------------
# MongoDB setup
# -------------------------
uri = os.environ["MONGODB_URI"]
client = MongoClient(uri)
db = client.get_database("anime")
collection = db["anime_anilist"]   # collection containing embeddings

# -------------------------
# Embedding settings
# -------------------------
dim = 384  # embedding size (number of dimensions in the vector)

# Fetch documents with embeddings
docs = list(collection.find({"embedding": {"$exists": True}}, {"embedding": 1, "title": 1}))

# Convert embeddings from MongoDB lists to numpy arrays
# FAISS requires float32 arrays
embeddings = np.array([doc["embedding"] for doc in docs], dtype='float32')

# Extract titles for display
titles = [
    doc["title"].get("romaji") or doc["title"].get("english") or doc["title"].get("native")
    for doc in docs
]

# Store MongoDB IDs for later reference
ids = [doc["_id"] for doc in docs]

n_elements = len(embeddings)
print(f"Loaded {n_elements} embeddings from MongoDB.")

# -------------------------
# Initialize FAISS index
# -------------------------
# Using IndexFlatIP for cosine similarity search
# FAISS uses inner product for IndexFlatIP
# To get cosine similarity, vectors must be normalized to unit length
faiss.normalize_L2(embeddings)  # normalize embeddings so inner product = cosine similarity

# IndexFlatIP is an exact search index
index = faiss.IndexFlatIP(dim)  # Inner Product = cosine similarity if vectors normalized

# Add embeddings to the index
index.add(embeddings)
print(f"FAISS index contains {index.ntotal} vectors.")

# -------------------------
# Test query
# -------------------------
# Pick a random query embedding from the dataset
query_idx = 1
query_embedding = embeddings[query_idx].reshape(1, -1)  # FAISS expects shape (1, dim)

# Search top-k nearest neighbors
k = 10
distances, labels = index.search(query_embedding, k)  # distances are inner products (cosine similarity)

# -------------------------
# Display results
# -------------------------
print("Query:", titles[query_idx])
print("Results:")
for label, distance in zip(labels[0], distances[0]):
    print(f"Title: {titles[label]}, Score: {distance:.4f}")  
    print(f"MongoDB ID: {ids[label]}")
    print()

# You can use the MongoDB ID to fetch more details from the database if needed
# Example: Fetch full document from MongoDB
# doc = collection.find_one({"_id": ids[label]})
# print(doc)
# print(doc["description"])  # or any other field

# -------------------------
# Notes:
# - FAISS is highly optimized for large datasets
# - IndexFlatIP is exact; for millions of vectors, consider approximate indexes like IndexIVFFlat
# - Cosine similarity is computed via inner product after L2 normalization
# - FAISS can be run on GPU for even faster searches (faiss-gpu)
# - Numpy arrays are used for speed and compatibility with FAISS
