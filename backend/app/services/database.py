"""
Database service for interacting with Supabase.
Handles storage and retrieval of document embeddings.
Updated for OpenAI embeddings (1536 dimensions) and LlamaIndex integration.
"""

from supabase import create_client, Client
from typing import List, Dict, Any
from app.config.settings import settings


class DatabaseService:
    """Service for database operations"""
    
    def __init__(self):
        """Initialize Supabase client"""
        self.client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY
        )
    
    def store_documents(self, documents: List[Dict[str, Any]]) -> int:
        """
        Store documents with embeddings in the database.
        
        Args:
            documents: List of documents with content, embeddings, and metadata
            
        Returns:
            Number of documents stored
        """
        try:
            # Prepare documents for insertion
            records = []
            for doc in documents:
                record = {
                    'repo_url': doc['repo_url'],
                    'file_path': doc['file_path'],
                    'content': doc['content'],
                    'embedding': doc['embedding'],
                    'metadata': doc.get('metadata', {}),
                    'user_id': doc.get('user_id', 'default'),
                    'file_type': doc.get('file_type', 'text')
                }
                records.append(record)
            
            # Insert documents in batches
            batch_size = 100
            total_inserted = 0
            
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                response = self.client.table('documents').insert(batch).execute()
                total_inserted += len(batch)
            
            return total_inserted
            
        except Exception as e:
            raise Exception(f"Error storing documents: {str(e)}")
    
    def search_similar_documents(
        self,
        query_embedding: List[float],
        repo_url: str,
        top_k: int = 10,
        threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents using vector similarity.
        
        Args:
            query_embedding: Query vector embedding (1536 dimensions for OpenAI)
            repo_url: Repository URL to filter by
            top_k: Number of results to return
            threshold: Minimum similarity threshold
            
        Returns:
            List of similar documents with content and metadata
        """
        try:
            # Call the match_documents function
            response = self.client.rpc(
                'match_documents',
                {
                    'query_embedding': query_embedding,
                    'match_repo_url': repo_url,
                    'match_threshold': threshold,
                    'match_count': top_k
                }
            ).execute()
            
            return response.data
            
        except Exception as e:
            print(f"Error searching documents: {str(e)}")
            raise Exception(f"Error searching documents: {str(e)}")
    
    def hybrid_search(
        self,
        query_embedding: List[float],
        query_text: str,
        repo_url: str,
        top_k: int = 10,
        threshold: float = 0.3,
        vector_weight: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining vector similarity and keyword matching.
        
        Args:
            query_embedding: Query vector embedding
            query_text: Query text for keyword matching
            repo_url: Repository URL to filter by
            top_k: Number of results to return
            threshold: Minimum similarity threshold
            vector_weight: Weight for vector similarity (0-1)
            
        Returns:
            List of documents with combined scores
        """
        try:
            response = self.client.rpc(
                'hybrid_search',
                {
                    'query_embedding': query_embedding,
                    'query_text': query_text,
                    'match_repo_url': repo_url,
                    'match_threshold': threshold,
                    'match_count': top_k,
                    'vector_weight': vector_weight
                }
            ).execute()
            
            return response.data
            
        except Exception as e:
            print(f"Error in hybrid search: {str(e)}")
            raise Exception(f"Error in hybrid search: {str(e)}")
    
    def delete_repo_documents(self, repo_url: str) -> int:
        """
        Delete all documents for a specific repository.
        
        Args:
            repo_url: Repository URL
            
        Returns:
            Number of documents deleted
        """
        try:
            response = self.client.table('documents')\
                .delete()\
                .eq('repo_url', repo_url)\
                .execute()
            
            return len(response.data) if response.data else 0
            
        except Exception as e:
            raise Exception(f"Error deleting documents: {str(e)}")
    
    def check_repo_exists(self, repo_url: str) -> bool:
        """
        Check if repository documents already exist in database.
        
        Args:
            repo_url: Repository URL
            
        Returns:
            True if documents exist, False otherwise
        """
        try:
            response = self.client.table('documents')\
                .select('id')\
                .eq('repo_url', repo_url)\
                .limit(1)\
                .execute()
            
            return len(response.data) > 0
            
        except Exception as e:
            raise Exception(f"Error checking repository: {str(e)}")