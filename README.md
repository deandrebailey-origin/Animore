# Animore

[![CI](https://github.com/deandrebailey-origin/Animore/actions/workflows/ci.yml/badge.svg)](https://github.com/deandrebailey-origin/Animore/actions/workflows/ci.yml)

**Animore** is an anime recommendation app. Type in an anime you like and get recommendations that blend *what similar viewers enjoyed* (collaborative filtering) with *what's similar in content* (semantic vector search).

**Live demo:** [your Vercel URL]

---

## How it works

| Mode | How it recommends | Strength |
|---|---|---|
| **Collaborative** | Item–item cosine similarity over ~[N]M user ratings ("people who liked this also liked…") | Captures real viewer taste |
| **Semantic** | Vector search over [384]-dimensional anime embeddings in MongoDB Atlas | Works for anime with few ratings |
| **Hybrid** (default) | Merges both ranked lists with **Reciprocal Rank Fusion (RRF)** | Best of both |

- **Cold start:** if a title has no collaborative neighbors, the API falls back to semantic search.
- **RRF** scores each item as `Σ 1 / (k + rank)` across lists, so titles ranked highly by *both* methods rise to the top.

### Architecture

```
Next.js (Vercel)  ──►  Flask API (Render, gunicorn)  ──►  MongoDB Atlas
  ani-app/              api/app.py                        anime metadata,
  search, explore,      /candidates, /health              collab neighbors,
  map pages                                               vector index
```

---

## Evaluation

I built an offline evaluation harness (`api/evaluation/`) to measure recommendation quality instead of judging by eye.

**Method**
- **Data:** ~4.5M ratings (11,680 anime × 24,146 users) from [the Kaggle *Anime Recommendation Database 2020*, `rating_complete.csv`].
- **User-level holdout:** 10% of users are held out entirely, and neighbors are built on training users only, so there is no leakage.
- **Test cases:** for each test user, one liked anime (rating ≥ 8) is the seed. Their other liked anime are the hidden targets.
- **Metrics:**
  - **Recall@K:** how many hidden favorites were found.
  - **NDCG@K:** whether they were ranked near the top.
  - **Catalog coverage:** the share of all anime that ever get recommended.
- **Reproducibility:** results use a fixed random seed.

**Results** (K = 10)

| Recommender | Recall@10 | NDCG@10 | Coverage@10 |
|---|---|---|---|
| Popularity baseline | 0.384 | 0.407 | 0.09% |
| Collaborative (cosine) | 0.337 | 0.364 | 28.3% |
| Collaborative (mean-centered) | 0.289 | 0.318 | 33.8% |
| **Hybrid (collab + popularity, RRF)** | **0.415** | **0.439** | **17.9%** |

**Takeaways**
- **Popularity is a strong baseline:** it beats pure collaborative filtering on accuracy, but recommends the same ~11 titles to everyone.
- **The RRF hybrid wins on accuracy:** +23% Recall@10 over collaborative and +8% over popularity, while recommending ~190× more distinct titles than the baseline.
- **Mean-centering ratings** increased diversity but reduced accuracy, a clear accuracy-vs-diversity trade-off. Raw cosine stays the default.
- **Caveat:** test seeds are limited to anime the collaborative model knows, which slightly favors collaborative methods.

**Reproduce**
```bash
cd api
python -m evaluation.run_eval --data rating_complete.csv
python -m evaluation.run_eval --rows 200000   # quick run
```

---

## Engineering

- **Testing:** pytest unit tests for the ranking logic (RRF) and metrics, plus API endpoint tests using test doubles. No database or secrets are needed to run them.
- **CI (GitHub Actions):** every pull request runs `ruff` + `pytest` on the API, ESLint + a production build on the web app, and a Docker image build.
  - Branch protection requires CI to pass before merging.
- **Docker:** a production API image on `python:3.12-slim`:
  - runs as a non-root user under gunicorn
  - includes a health check
  - uses `.dockerignore`, so tests, caches and secrets stay out of the image
- **Security:**
  - User search input is regex-escaped to prevent ReDoS / regex injection.
  - Database connections are created lazily.
  - The app uses a least-privilege read/write database user.

---

## Run locally

**Prerequisites:** Python 3.12, Node 22, and a MongoDB Atlas connection string.

**API**
```bash
cd api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
echo 'MONGODB_URI=your-connection-string' > .env
[flask --app app run --port 5000]
```

**Web app**
```bash
cd ani-app
npm ci
# create .env.local with MONGODB_URI=... [and the API URL variable your app uses]
npm run dev
```

**With Docker**
```bash
docker compose up --build
```

**Tests**
```bash
cd api && ruff check . && python -m pytest -v
cd ani-app && npm run lint && npm run build
```

---

## Project structure

```
api/
  app.py                     Flask API: /candidates, /health, RRF
  build_collab_candidates.py Builds item–item neighbors from ratings
  evaluation/                Offline eval: metrics, user split, run_eval
  tests/                     pytest suite
  Dockerfile
ani-app/                     Next.js frontend (search, explore, map)
.github/workflows/ci.yml     CI pipeline
docker-compose.yml
```

---

## Roadmap

- Semantic and semantic+collaborative hybrids in the evaluation harness
- MMR re-ranking for diversity, and de-duplicating franchises (sequels and movies of the seed)
- 3D map visualization of the anime embedding space