# ��� Similarity Logic & Hybrid Recommender — MoviePulse v2.1

## 1️⃣ Introduction

The MoviePulse recommendation engine uses a **vector-based similarity search** powered by *cosine similarity* on movie embeddings to identify semantically similar movies. This approach goes beyond surface-level genre matching and uncovers deeper patterns in a movie’s metadata.

When there are sparse or missing embeddings (e.g., for new or obscure movies), the system blends a **hybrid fallback strategy** combining genre and mood information to maintain robust recommendations.

---

## 2️⃣ Cosine Similarity Explained

Cosine similarity measures how closely two vectors point in the same direction, regardless of their magnitude. It is defined as:

\`\`\`
cosine_similarity(A, B) = (A ⋅ B) / (||A|| * ||B||)
\`\`\`

Where:

- \`A\` and \`B\` are vector representations (embeddings) of two movies
- the dot product measures their alignment
- the norms scale them to unit length

**Interpretation:**

- 1 → identical
- 0 → unrelated
- -1 → opposite

The MoviePulse recommender:

- normalizes all embeddings
- uses \`sklearn.metrics.pairwise.cosine_similarity\` for efficient matrix comparisons
- retrieves the top-K matches above a minimum similarity threshold (default 0.3)

---

## 3️⃣ Hybrid Fallback Strategy

If the semantic (vector) recommendations are insufficient — for example, if:

- a movie has no embedding
- or too few top-K results exceed the similarity threshold

→ then a fallback system blends in:

- **genre-based recommendations** (from \`genres.json\`)
- **mood-based recommendations** (from \`moods.json\`)

A tunable weighting system merges these fallback results with the semantic results. By default, MoviePulse weights semantic similarity at **70%** and fallback recommendations at **30%**.

---

## 4️⃣ JSON Fallback Definitions

The fallback rules are stored in JSON files:

**\`genres.json\`**
\`\`\`json
{
  "action": [101, 102, 103],
  "comedy": [201, 202, 203]
}
\`\`\`

**\`moods.json\`**
\`\`\`json
{
  "uplifting": ["comedy", "family"],
  "dark": ["thriller", "horror"]
}
\`\`\`

- \`genres.json\` maps a genre to movie IDs that can be recommended if semantic data is missing.
- \`moods.json\` maps moods to genres, which then use \`genres.json\` to identify movies.

---

## 5️⃣ Extending or Tuning the Rules

✅ **Add new genres or moods**  
Edit the JSON files and reload them. The recommender will pick up the new rules automatically.

✅ **Change weighting**  
Modify the hybrid weighting ratio in \`HybridRecommender\`, for example from 70:30 to 80:20.

✅ **Adjust similarity thresholds**  
Update the \`min_similarity\` parameter in \`SimilaritySearch.find_similar\`.

---

## 6️⃣ Development Notes

- Embeddings are stored in \`static_data/test_embeddings.pkl\`
- Logs for similarity search operations are saved in \`logs/similarity_search.log\`
- Unit tests validate:
  - cosine similarity
  - fallback merging
  - top-K ranking correctness
- The recommender is modular and easy to extend to other strategies (like collaborative filtering) in the future.

---

## 7️⃣ Summary

MoviePulse’s recommender provides:

✅ powerful semantic vector search  
✅ robust genre/mood fallback  
✅ human-like hybrid explainability  

for a trustworthy and engaging movie recommendation experience.

---

**END OF DOCUMENTATION**
