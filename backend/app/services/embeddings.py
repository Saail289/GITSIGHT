"""
Embedding service for generating vector embeddings from text.
Uses sentence-transformers for local embedding generation.
"""

from sentence_transformers import SentenceTransformer
from typing import List
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.config.settings import settings


class EmbeddingService:
    """Service for generating text embeddings"""
    
    def __init__(self):
        """Initialize embedding model"""
        # Load the embedding model (downloads on first use, ~90MB)
        print(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
        
        # Initialize text splitter for chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for a single text.
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector as list of floats
        """
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (more efficient).
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embedding vectors
        """
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
    
    def chunk_documents(self, documents: List[dict]) -> List[dict]:
        """
        Split documents into smaller chunks for better retrieval.
        
        Args:
            documents: List of documents with content
            
        Returns:
            List of chunked documents
        """
        chunked_docs = []
        
        for doc in documents:
            content = doc['content']
            chunks = self.text_splitter.split_text(content)
            
            for i, chunk in enumerate(chunks):
                chunked_doc = {
                    'repo_url': doc['repo_url'],
                    'file_path': f"{doc['file_path']}#chunk_{i}",
                    'content': chunk,
                    'metadata': {
                        **doc.get('metadata', {}),
                        'chunk_index': i,
                        'total_chunks': len(chunks)
                    }
                }
                chunked_docs.append(chunked_doc)
        
        return chunked_docs
    
    def embed_documents(self, documents: List[dict]) -> List[dict]:
        """
        Chunk documents and generate embeddings for all chunks.
        
        Args:
            documents: List of documents
            
        Returns:
            List of documents with embeddings
        """
        # Chunk documents
        print(f"Chunking {len(documents)} documents...")
        chunked_docs = self.chunk_documents(documents)
        print(f"Created {len(chunked_docs)} chunks")
        
        # Extract text content
        texts = [doc['content'] for doc in chunked_docs]
        
        # Generate embeddings in batch
        print("Generating embeddings...")
        embeddings = self.generate_embeddings_batch(texts)
        
        # Add embeddings to documents
        for doc, embedding in zip(chunked_docs, embeddings):
            doc['embedding'] = embedding
        
        return chunked_docs