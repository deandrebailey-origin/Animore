import numpy as np


def split_users(ratings, test_frac=0.1, seed=42):
    """Hold out whole users, so the model never sees anything from a test user."""
    users = ratings["user_id"].unique()
    rng = np.random.default_rng(seed)
    n_test = int(len(users) * test_frac)
    test_users = set(rng.choice(users, size=n_test, replace=False))

    is_test = ratings["user_id"].isin(test_users)
    return ratings[~is_test], ratings[is_test]