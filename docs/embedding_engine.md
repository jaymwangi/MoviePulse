# Embedding Engine Documentation

## Overview

The `MovieEmbeddingEngine` provides vector-based semantic embeddings for movie metadata, enabling efficient similarity searches and recommendations. It leverages SentenceTransformers to produce embeddings from movie titles and descriptions.

---

## Model

- **Library:** `sentence-transformers`
- **Default model:** `all-MiniLM-L6-v2` (or whichever you chose)
- **Framework:** PyTorch backend

---

## Input

| Field           | Type   | Description                                |
|-----------------|--------|--------------------------------------------|
| `movie_id`      | int    | Unique identifier for the movie             |
| `title`         | string | Movie title                                |
| `description`   | string | Brief movie synopsis/overview              |
| `genres`        | list   | List of genres associated with the movie   |

---

## Output

- A dense vector (embedding) for each movie
- Shape: typically 384 dimensions for `all-MiniLM-L6-v2`

---

## Pipeline Steps

1. Load movie metadata (CSV or database).
2. Concatenate relevant text fields (title + description + genres).
3. Generate embedding with SentenceTransformer.
4. Store embedding for retrieval (e.g., pickle, JSON, or database).

---

## Performance Considerations

- Embedding generation can be batch processed.
- Consider caching results to avoid repeated computation.
- If you add performance logging, store metrics in:

```
logs/embedding_perf.log
```

Example metrics:
- time per batch
- average embedding time per movie

---

## How to Update Embeddings

- If movie metadata changes, rerun:

```bash
python ai_smart_recommender/recommender_engine/scripts/precompute_embeddings.py
```

to regenerate and store the updated vectors.

---

## Known Limitations

- Semantic embeddings may lose some nuance of genre-specific features
- Embeddings must be kept in sync with the source data

---

## Author

*Your Name / MoviePulse Team*  
*Date: 2025-07-01*
