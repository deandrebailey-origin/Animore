import pandas as pd
import argparse
import random
import time
import numpy as np
from build_collab_candidates import compute_neighbors
from evaluation.metrics import recall_at_k, ndcg_at_k
from evaluation.split import split_users

LIKED_THRESHOLD = 8

def load_ratings(path, nrows):
    return pd.read_csv(path,
                 usecols=["user_id", "anime_id", "rating"],
                 dtype={"user_id": "int32", "anime_id": "int32", "rating": "int8"},
                 nrows=nrows,
                )

def build_test_cases(test, known_items, like_threshold=8, min_liked=5, seed=42):
    rng = np.random.default_rng(seed)
    cases = []

    is_liked = test["rating"] >= like_threshold
    is_known = test["anime_id"].isin(known_items)

    liked = test[is_liked & is_known]

    for user_id, group in liked.groupby("user_id"):
        liked_ids = group["anime_id"].to_numpy()

        if len(liked_ids) < min_liked: continue

        seed_anime = int(rng.choice(liked_ids))
        targets = set(liked_ids.tolist()) - {seed_anime}

        cases.append((seed_anime, targets))

    return cases 

def make_collab_recommender(neighbors):
    def recommend(seed):
        return neighbors.get(seed, [])
    return recommend

def make_popularity_recommender(train, n=50):
    top =  train["anime_id"].value_counts().index[: n + 1].tolist()
    # value_counts on train's anime_id → .index → first n+1 → .tolist()
    def recommend(seed):
        return [anime_id for anime_id in top if anime_id != seed][:n]   
    # the items in top that aren't the seed, first n of them
    return recommend

def evaluate(cases, recommend, n_items, ks=(10, 50)):
    scores = {}
    s = set()

    for k in ks:
        scores[f"recall@{k}"] = []
        scores[f"ndcg@{k}"] = []

    for seed, targets in cases:
        recs = recommend(seed) # once per case
        s.update(recs[:10])
        for k in ks:
            # score recs at k (next)
            scores[f"recall@{k}"].append(recall_at_k(recs, targets, k))
            scores[f"ndcg@{k}"].append(ndcg_at_k(recs, targets, k))
            

    results = {name: float(np.mean(values)) for name, values in scores.items()}
    results["coverage@10"] = len(s) / n_items
    return results

def main():
    parser = argparse.ArgumentParser(description="Evaluate Animore recommenders")
    parser.add_argument("--data", default = "rating_complete.csv")
    parser.add_argument("--rows", type = int, default = 5_000_000)
    parser.add_argument("--seed", type = int, default=42)
    parser.add_argument("--test-frac", type=float, default=0.1)
    args = parser.parse_args()

    df = load_ratings(args.data, nrows=args.rows)
    train, test = split_users(df, test_frac=args.test_frac, seed=args.seed)

    neighbors = compute_neighbors(train, k=50, min_ratings=5)
    known_items = set(neighbors.keys())
    cases = build_test_cases(test, known_items, seed=args.seed)

    collab = make_collab_recommender(neighbors)
    popular = make_popularity_recommender(train)

    print("collab: ", evaluate(cases, collab, len(known_items)))
    print("popular:", evaluate(cases, popular, len(known_items)))

if __name__ == "__main__":
    main()


