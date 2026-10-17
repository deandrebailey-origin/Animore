import math


def recall_at_k(recommended, targets, k):
    if not targets:
        return 0.0
    hits = len(set(recommended[:k]) & set(targets))
    return hits / min(len(targets), k)

# of the anime the user liked
# what fraction of them actually appeared in the recommendations
# use min of the amount of recommendation vs the number
# of the users 

def position_weight(rank):
    """How much a hit is worth at this position (rank 0 = top of the list)."""
    return 1 / math.log2(rank + 2)


def ndcg_at_k(recommended, targets, k):
    targets = set(targets)

    # actual score based on the weight of every hit
    actual_score = 0.0
    for rank, item in enumerate(recommended[:k]):
        if item in targets:
            actual_score += position_weight(rank)

    # score a perfect list with every possible hit
    possible_hits = min(len(targets), k)
    best_score = 0.0
    for rank in range(possible_hits):
        best_score += position_weight(rank)

    if best_score == 0:
        return 0.0
    return actual_score / best_score

 