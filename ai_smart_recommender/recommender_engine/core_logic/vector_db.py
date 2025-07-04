"""
FAISS-based Vector Database for Movie Embeddings
-----------------------------------------------
Provides efficient storage and similarity search for movie embeddings.
"""

import faiss
import numpy as np
from typing import List, Tuple, Optional
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorDB:
    """
    FAISS-based vector database for movie embeddings with ID tracking.
    
    Features:
    - Build and manage FAISS indices
    - Persistent storage/loading
    - Similarity search with score thresholds
    - Index statistics
    """
    
    def __init__(self, index: Optional[faiss.Index] = None):
        """
        Initialize VectorDB with an optional pre-built FAISS index.
        
        Args:
            index: Optional pre-existing FAISS index
        """
        self.index = index
        self.embedding_dim = None
        if index is not None:
            self.embedding_dim = index.d

    @classmethod
    def build_index(cls, 
                   embeddings: np.ndarray, 
                   ids: List[int], 
                   use_gpu: bool = False) -> 'VectorDB':
        """
        Build a new FAISS index from embeddings and IDs.
        
        Args:
            embeddings: numpy array of shape (n_samples, dim)
            ids: list of integer movie IDs
            use_gpu: whether to use GPU acceleration
            
        Returns:
            VectorDB instance with the built index
        """
        if embeddings.ndim != 2:
            raise ValueError("Embeddings must be 2D array")
            
        if len(ids) != embeddings.shape[0]:
            raise ValueError("Number of IDs must match number of embeddings")
            
        dim = embeddings.shape[1]
        
        # Initialize index
        index = faiss.IndexFlatIP(dim)  # Inner product (cosine similarity)
        if use_gpu:
            res = faiss.StandardGpuResources()
            index = faiss.index_cpu_to_gpu(res, 0, index)
            
        # Add ID mapping
        index = faiss.IndexIDMap(index)
        
        # Convert IDs to int64 array
        id_array = np.array(ids, dtype=np.int64)
        
        # Add embeddings to index
        index.add_with_ids(embeddings, id_array)
        
        logger.info(f"Built FAISS index with {index.ntotal} vectors (dim={dim})")
        return cls(index)

    def save_index(self, path: str) -> None:
        """
        Save the FAISS index to disk.
        
        Args:
            path: file path to save index
        """
        if self.index is None:
            raise ValueError("No index to save")
            
        dir_path = os.path.dirname(path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)
            
        faiss.write_index(self.index, path)
        logger.info(f"Saved index to {path}")

    @classmethod
    def load_index(cls, path: str) -> 'VectorDB':
        """
        Load a FAISS index from disk.
        
        Args:
            path: file path to load index from
            
        Returns:
            VectorDB instance with loaded index
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Index file not found: {path}")
            
        index = faiss.read_index(path)
        logger.info(f"Loaded index from {path} with {index.ntotal} vectors")
        return cls(index)

    def search(self, 
              query_embedding: np.ndarray, 
              top_k: int = 5,
              min_similarity: float = 0.0) -> Tuple[List[int], List[float]]:
        """
        Perform similarity search on the index.
        
        Args:
            query_embedding: numpy array of shape (dim,)
            top_k: number of results to return
            min_similarity: minimum similarity score threshold
            
        Returns:
            Tuple of (list of movie IDs, list of similarity scores)
        """
        if self.index is None:
            raise ValueError("Index not initialized")
            
        if query_embedding.ndim != 1:
            raise ValueError("Query embedding must be 1D array")
            
        if self.embedding_dim and len(query_embedding) != self.embedding_dim:
            raise ValueError(f"Query dimension mismatch. Expected {self.embedding_dim}, got {len(query_embedding)}")
            
        # Reshape for FAISS
        query = query_embedding.reshape(1, -1).astype(np.float32)
        
        # Search
        distances, ids = self.index.search(query, top_k)
        
        # Convert to Python types and filter by similarity
        results = []
        scores = []
        for i in range(len(ids[0])):
            if ids[0][i] == -1:  # FAISS returns -1 for empty slots
                continue
            similarity = 1 - distances[0][i]  # Convert distance to similarity
            if similarity >= min_similarity:
                results.append(int(ids[0][i]))
                scores.append(float(similarity))
                
        return results, scores

    def get_stats(self) -> dict:
        """
        Get statistics about the index.
        
        Returns:
            Dictionary containing index statistics
        """
        if self.index is None:
            return {}
            
        return {
            "num_vectors": self.index.ntotal,
            "embedding_dim": self.index.d,
            "is_trained": self.index.is_trained
        }

    def __len__(self) -> int:
        """Return number of vectors in the index."""
        return self.index.ntotal if self.index else 0
