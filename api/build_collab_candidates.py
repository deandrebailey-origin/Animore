import argparse
import os
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne
from scipy.sparse import csr_matrix
from sklearn.neighbors import NearestNeighbors

def compute_neighbors(ratings, k=50, min_ratings=5):
    counts = ratings["anime_id"].value_counts()
    ratings = ratings[ratings["anime_id"].isin(counts[counts >= min_ratings].index)]

    anime_ids = np.sort(ratings["anime_id"].unique())
    user_ids = np.sort(ratings["user_id"].unique())
    rows = np.searchsorted(anime_ids, ratings["anime_id"].to_numpy())
    cols = np.searchsorted(user_ids, ratings["user_id"].to_numpy())

    X = csr_matrix(
        (ratings["rating"].astype(np.float32).to_numpy(), (rows, cols)),
        shape=(len(anime_ids), len(user_ids)),
    )

    print(f"Matrix: {X.shape[0]:,} anime x {X.shape[1]:,} users, {X.nnz:,} ratings")

    n_neighbors = min(k + 1, len(anime_ids))  # +1 because each anime matches itself
    knn = NearestNeighbors(n_neighbors=n_neighbors, metric="cosine", algorithm="brute")
    knn.fit(X)  # fit once
    _, neighbors = knn.kneighbors(X)  # query every anime at once
 
    result = {}
    for row, anime_id in enumerate(anime_ids):
        similar = [int(anime_ids[j]) for j in neighbors[row] if j != row][:k]
        result[int(anime_id)] = similar
    return result
 
 
def save_to_mongo(collection, neighbors, batch_size=1000):
    ops, matched = [], 0
    for anime_id, candidates in neighbors.items():
        ops.append(UpdateOne({"mal_id": anime_id}, {"$set": {"collab_candidates": candidates}}))
        if len(ops) >= batch_size:
            matched += collection.bulk_write(ops, ordered=False).matched_count
            print(f"Wrote {matched:,} documents so far...")
            ops = []
    if ops:  # write the final partial batch, once, after the loop
        matched += collection.bulk_write(ops, ordered=False).matched_count
    return matched
 
 
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="user-filtered.csv")
    parser.add_argument("--rows", type=int, default=1_000_000, help="rows to read; 0 = all")
    parser.add_argument("--k", type=int, default=50)
    parser.add_argument("--min-ratings", type=int, default=5)
    args = parser.parse_args()
 
    load_dotenv()
    collection = MongoClient(os.environ["MONGODB_URI"]).anime.anime_anilist
 
    ratings = pd.read_csv(
        args.csv,
        nrows=args.rows or None,
        usecols=["user_id", "anime_id", "rating"],
        dtype={"user_id": "int32", "anime_id": "int32", "rating": "int8"},
    )
    print(f"Loaded {len(ratings):,} ratings")
 
    neighbors = compute_neighbors(ratings, k=args.k, min_ratings=args.min_ratings)
    print(f"Computed neighbors for {len(neighbors):,} anime")
 
    matched = save_to_mongo(collection, neighbors)
    print(f"Done. Updated {matched:,} MongoDB documents "
          f"({len(neighbors) - matched:,} anime IDs had no matching document).")
 
 
if __name__ == "__main__":
    main()
 

