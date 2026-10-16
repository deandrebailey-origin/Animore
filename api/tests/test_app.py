import pytest

import app as app_module
from app import app, reciprocal_rank_fusion


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()

def test_rrf_single_list_keeps_order():
    assert reciprocal_rank_fusion([1,2,3]) == [1,2,3]

def test_rrf_item_in_both_lists_rans_first():
    assert reciprocal_rank_fusion([1, 3, 4], [9, 3, 5])[0] == 3

def test_rrf_respects_limit():
    assert len(reciprocal_rank_fusion(list(range(100)), limit=10)) == 10


def test_rrf_empty_lists():
    assert reciprocal_rank_fusion([], []) == []

FAKE_ANIME = {"mal_id": 1, "collab_candidates": [10, 20, 30], "embedding": [0.1] * 384}

def fake_semantic(anime, k=50):
    return [20, 40]

def test_health(client):
    r = client.get("/health")

    # default return 200 when calling the enfpoint
    assert r.status_code == 200

    # json returned by the body
    assert r.get_json() == {"status": "ok"}

def test_missing_titl_returns_400(client):
    
    assert client.get("/candidates").status_code == 400

def test_bad_mode_returns_400(client):
    r = client.get("/candidates", query_string={"title": "Naruto", "mode": "magic"})
    assert r.status_code == 400

def test_unknown_title_returns_404(client, monkeypatch):
    monkeypatch.setattr(app_module, "find_anime_by_title", lambda title: None)
    # make swap in app file
    # which nae to replace
    # replace with none - short way to write a funtion lambda title: None 
    # takes title and returns none

    r = client.get("/candidates", query_string = {"title": "Not a real Anime"})
    assert r.status_code == 404

 
def test_hybrid_ranks_shared_candidates_first(client, monkeypatch):
    monkeypatch.setattr(app_module, "find_anime_by_title", lambda title: FAKE_ANIME)
    monkeypatch.setattr(app_module, "semantic_candidates", fake_semantic)

    data = client.get("/candidates", query_string={"title": "Cowboy Bebop"}).get_json()

    assert data["method"] == "hybrid"
    assert data["candidate_ids"][0] == 20

def test_cold_start_falls_back_to_semantic(client, monkeypatch):
    no_ratings = {**FAKE_ANIME, "collab_candidates": []}
    monkeypatch.setattr(app_module, "find_anime_by_title", lambda title: no_ratings)
    monkeypatch.setattr(app_module, "semantic_candidates", fake_semantic)

    data = client.get("/candidates", query_string={"title": "New Show"}).get_json()

    assert data["method"] == "semantic"
    assert data["candidate_ids"] == [20, 40] 

def test_collaborative_mode_skips_vector_search(client, monkeypatch):
    def should_not_run(*args, **kwargs):
        raise AssertionError("semantic search should not run in collaborative mode")

    monkeypatch.setattr(app_module, "find_anime_by_title", lambda title: FAKE_ANIME)
    monkeypatch.setattr(app_module, "semantic_candidates", should_not_run)

    r = client.get(
        "/candidates", query_string={"title": "Cowboy Bebop", "mode": "collaborative"}
    )

    assert r.status_code == 200
    assert r.get_json()["candidate_ids"] == [10, 20, 30]
