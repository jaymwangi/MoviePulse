"""
fetch_movies.py
---------------------------
Script to fetch trending movies from TMDB and save them as JSON data.
Creates a dataset for the MoviePulse application.
"""

import json
from tqdm import tqdm
from typing import List
from service_clients.tmdb_client import tmdb_client

def get_trending_movie_ids(pages: int = 2) -> List[int]:
    """
    Fetch trending movies over multiple pages to build an ID list.
    
    Args:
        pages: Number of pages of trending movies to fetch (20 movies per page)
    
    Returns:
        List of unique movie IDs
    """
    ids = set()
    for page in range(1, pages + 1):
        movies, _ = tmdb_client.get_trending_movies(page=page)
        ids.update(m.id for m in movies)
    return list(ids)

def fetch_movie_details(movie_ids: List[int]) -> List[dict]:
    """
    Fetch complete details for each movie ID.
    
    Args:
        movie_ids: List of TMDB movie IDs to fetch
    
    Returns:
        List of movie details as dictionaries
    """
    results = []
    for movie_id in tqdm(movie_ids, desc="Fetching movie details"):
        try:
            movie_obj = tmdb_client.get_movie_details(movie_id)
            movie_dict = movie_obj.__dict__.copy()
            
            # handle nested attributes to avoid JSON serialization error
            movie_dict["genres"] = [g.__dict__ for g in movie_obj.genres]
            movie_dict["directors"] = [d.__dict__ for d in movie_obj.directors]
            movie_dict["cast"] = [c.__dict__ for c in movie_obj.cast]
            movie_dict["videos"] = [v.__dict__ for v in movie_obj.videos]
            
            results.append(movie_dict)
        except Exception as e:
            print(f"Error fetching movie {movie_id}: {e}")
    return results

def save_movies_to_json(movie_data: List[dict], output_path: str) -> None:
    """
    Save movie data to JSON file.
    
    Args:
        movie_data: List of movie dictionaries
        output_path: Path to save the JSON file
    """
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump([m for m in movie_data if m],
                  f,
                  indent=2,
                  ensure_ascii=False)

def main():
    """Main execution function."""
    print("Fetching trending movie IDs...")
    movie_ids = get_trending_movie_ids(pages=5)
    print(f"Collected {len(movie_ids)} unique movie IDs")

    movies = fetch_movie_details(movie_ids)

    output_file = "static_data/movies.json"
    save_movies_to_json(movies, output_file)
    print(f"Successfully saved {len(movies)} movies to {output_file}")

if __name__ == "__main__":
    main()
