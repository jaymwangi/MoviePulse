# dev_scripts/generate_actor_similarity.py

import json
import time  # <-- you forgot this import
from pathlib import Path
from collections import defaultdict
from service_clients.tmdb_client import tmdb_client
from core_config import constants
import logging
from typing import Dict, Set, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# You referred to PERF_LOG_PREFIX but did not define it
PERF_LOG_PREFIX = "[PERF]"

@dataclass
class ActorSimilarity:
    """
    Data class to store similarity details between actors.
    """
    actor_id: int
    similarity: float
    common_movies: int


def calculate_actor_similarity(limit: int = 200) -> Dict[str, Dict]:
    """
    Generate actor similarity data based on co-appearance in movies.
    It uses Jaccard similarity on actors' movie sets.
    """
    logger.info(f"Generating actor similarity data for top {limit} actors...")

    total_start = time.perf_counter()  # measure total script runtime

    try:
        # ---------------------------------------------
        # Step 1: Fetch popular actors
        # ---------------------------------------------
        actor_fetch_start = time.perf_counter()
        actors = tmdb_client.get_popular_people(limit=limit)  # you must define this in tmdb_client
        actor_ids = [a.id for a in actors]

        logger.info(
            f"{PERF_LOG_PREFIX} Fetched {len(actors)} actors in "
            f"{time.perf_counter() - actor_fetch_start:.2f}s"
        )

        # ---------------------------------------------
        # Step 2: Build actor-to-movies mapping
        # ---------------------------------------------
        mapping_start = time.perf_counter()
        actor_movies: Dict[int, Set[int]] = defaultdict(set)
        failed_actors = 0  # count any filmography failures

        for actor_id in actor_ids:
            try:
                filmography_start = time.perf_counter()
                movies = tmdb_client.get_person_filmography(actor_id)
                actor_movies[actor_id].update(m.id for m in movies if m.id)
                logger.debug(
                    f"Processed filmography for actor {actor_id} in "
                    f"{time.perf_counter() - filmography_start:.2f}s"
                )
            except Exception as e:
                failed_actors += 1
                logger.warning(
                    f"Failed to get filmography for actor {actor_id}: {str(e)}"
                )
                continue

        logger.info(
            f"{PERF_LOG_PREFIX} Built actor-movies mapping in "
            f"{time.perf_counter() - mapping_start:.2f}s | "
            f"Failed actors: {failed_actors}/{len(actor_ids)}"
        )

        # ---------------------------------------------
        # Step 3: Calculate pairwise actor similarity
        # ---------------------------------------------
        similarity_start = time.perf_counter()
        similarity_data: Dict[str, Dict] = {}
        processed_pairs = 0

        for i, actor1 in enumerate(actor_ids):
            if actor1 not in actor_movies:
                continue  # skip if no movies for this actor

            similar_actors: List[ActorSimilarity] = []
            movies1 = actor_movies[actor1]

            for actor2 in actor_ids:
                if actor1 == actor2 or actor2 not in actor_movies:
                    continue

                movies2 = actor_movies[actor2]
                intersection = len(movies1 & movies2)
                union = len(movies1 | movies2)
                similarity = intersection / union if union > 0 else 0

                if similarity > 0.1:
                    similar_actors.append(ActorSimilarity(
                        actor_id=actor2,
                        similarity=similarity,
                        common_movies=intersection
                    ))

                processed_pairs += 1

            # sort similar actors by similarity descending
            similar_actors.sort(key=lambda x: x.similarity, reverse=True)

            # resolve the name of the main actor
            actor_name = next(a.name for a in actors if a.id == actor1)

            # store the top 20 similar actors for this actor
            similarity_data[str(actor1)] = {
                "name": actor_name,
                "similar_actors": [
                    {
                        "actor_id": sa.actor_id,
                        "similarity": sa.similarity,
                        "common_movies": sa.common_movies
                    }
                    for sa in similar_actors[:20]
                ]
            }

        logger.info(
            f"{PERF_LOG_PREFIX} Calculated similarities for {processed_pairs} pairs in "
            f"{time.perf_counter() - similarity_start:.2f}s"
        )

        # ---------------------------------------------
        # Step 4: Save to JSON file
        # ---------------------------------------------
        save_start = time.perf_counter()
        output_path = constants.RECOMMENDER_DATA_DIR / "actor_similarity.json"
        with open(output_path, "w") as f:
            json.dump(similarity_data, f, indent=2)

        total_duration = time.perf_counter() - total_start

        logger.info(
            f"{PERF_LOG_PREFIX} Saved actor similarity data for {len(similarity_data)} actors "
            f"in {total_duration:.2f}s | File: {output_path}"
        )

        return similarity_data

    except Exception as e:
        logger.error(
            f"{PERF_LOG_PREFIX} Failed to generate actor similarity data: {str(e)}"
        )
        raise


if __name__ == "__main__":
    try:
        constants.RECOMMENDER_DATA_DIR.mkdir(exist_ok=True)
        calculate_actor_similarity(limit=200)
    except Exception as e:
        logger.critical(f"Script failed: {str(e)}")
        raise
