from evaluation.metrics import ndcg_at_k, recall_at_k


def test_recall_perfect():
    assert recall_at_k([1, 2, 3], [1, 2, 3], k=3) == 1.0


def test_recall_half():
    assert recall_at_k([1, 9, 8, 7], [1, 2], k=4) == 0.5


def test_recall_caps_denominator_at_k():
    # 5 targets but k=2: two hits is the best possible, so 1.0
    assert recall_at_k([1, 2], [1, 2, 3, 4, 5], k=2) == 1.0


def test_ndcg_rewards_higher_rank():
    early = ndcg_at_k([1, 9, 9], [1], k=3)
    late = ndcg_at_k([9, 9, 1], [1], k=3)
    assert early == 1.0
    assert late < early


def test_empty_targets():
    assert recall_at_k([1, 2], [], k=2) == 0.0
    assert ndcg_at_k([1, 2], [], k=2) == 0.0