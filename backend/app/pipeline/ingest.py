"""
Ingestion Pipeline using LlamaIndex.
Handles document chunking with true AST-based code splitting and metadata injection.
Uses BATCH embeddings for faster processing (no accuracy impact).
"""

import os
from typing import List, Dict, Any, Optional
from pathlib import Path

from llama_index.core import Document, Settings
from llama_index.core.node_parser import SentenceSplitter, CodeSplitter
from llama_index.core.schema import TextNode
from llama_index.embeddings.openai import OpenAIEmbedding
from supabase import create_client, Client

# File extension to language mapping for AST parsing
# These are tree-sitter language identifiers
EXTENSION_TO_LANGUAGE = {
    '.py': 'python',
    '.js': 'javascript',
    '.jsx': 'javascript',
    '.ts': 'typescript',
    '.tsx': 'typescript',
    '.go': 'go',
    '.java': 'java',
    '.cpp': 'cpp',
    '.c': 'c',
    '.rs': 'rust',
    '.rb': 'ruby',
    '.php': 'php',
    '.swift': 'swift',
    '.kt': 'kotlin',
    '.scala': 'scala',
}

# Extensions that are code but use sentence splitting (no tree-sitter support or simpler files)
CODE_EXTENSIONS_SIMPLE = {'.html', '.css', '.json', '.yaml', '.yml', '.toml', '.xml', '.sql'}
MARKDOWN_EXTENSIONS = {'.md', '.mdx', '.txt', '.rst'}


class IngestPipeline:
    """
    Ingestion pipeline that processes documents with AST-aware code chunking.
    Uses CodeSplitter for supported languages, SentenceSplitter for others.
    Uses OpenAI embeddings via API for low memory footprint.
    """
    
    def __init__(self, user_id: Optional[str] = None):
        """
        Initialize the ingestion pipeline.
        
        Args:
            user_id: Optional user ID for RLS (Row Level Security) in Supabase
        """
        self.user_id = user_id or "default"
        
        # Initialize OpenAI embedding model via OpenRouter
        # Uses text-embedding-3-small: $0.02/1M tokens, 1536 dimensions
        print("Initializing OpenAI embeddings via OpenRouter...")
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY is required for embeddings")
        
        self.embed_model = OpenAIEmbedding(
            model="text-embedding-3-small",
            api_key=openrouter_api_key,
            api_base="https://openrouter.ai/api/v1"
        )
        Settings.embed_model = self.embed_model
        
        # Initialize text splitter for non-code files
        self.text_splitter = SentenceSplitter(
            chunk_size=1024,
            chunk_overlap=200
        )
        
        # Cache for code splitters (created per language as needed)
        self._code_splitters = {}
        
        # Initialize Supabase client
        self._init_supabase()
    
    def _get_code_splitter(self, language: str) -> CodeSplitter:
        """Get or create a CodeSplitter for the given language."""
        if language not in self._code_splitters:
            self._code_splitters[language] = CodeSplitter(
                language=language,
                chunk_lines=60,  # ~60 lines per chunk (keeps functions together)
                chunk_lines_overlap=10,  # 10 lines overlap for context
                max_chars=3000  # Max chars per chunk to avoid too-large chunks
            )
        return self._code_splitters[language]
    
    def _init_supabase(self):
        """Initialize Supabase client."""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY are required")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
    
    def _get_file_extension(self, file_path: str) -> str:
        """Extract file extension from path."""
        return Path(file_path).suffix.lower()
    
    def _get_file_type(self, file_path: str) -> str:
        """Determine file type based on extension."""
        ext = self._get_file_extension(file_path)
        if ext in EXTENSION_TO_LANGUAGE or ext in CODE_EXTENSIONS_SIMPLE:
            return "code"
        elif ext in MARKDOWN_EXTENSIONS:
            return "markdown"
        else:
            return "text"
    
    def _get_language_for_extension(self, file_path: str) -> Optional[str]:
        """Get the tree-sitter language for a file extension."""
        ext = self._get_file_extension(file_path)
        return EXTENSION_TO_LANGUAGE.get(ext)
    
    def _batch_embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch - MUCH faster.
        No accuracy loss, same embeddings as sequential processing.
        """
        if not texts:
            return []
        
        print(f"Batch embedding {len(texts)} chunks (this is fast!)...")
        # FastEmbed supports efficient batch embedding
        embeddings = list(self.embed_model._model.embed(texts))
        # Convert numpy float32 to Python float for JSON serialization
        return [[float(x) for x in e] for e in embeddings]
    
    def process_documents(
        self,
        documents: List[Dict[str, Any]],
        repo_url: str,
        all_file_paths: List[str] = None
    ) -> int:
        """
        Process and ingest documents into the vector store.
        Uses BATCH embedding for faster processing without accuracy loss.
        
        Args:
            documents: List of documents from GitHub scraper
            repo_url: Repository URL
            all_file_paths: Optional list of ALL file paths in the repo
            
        Returns:
            Number of nodes ingested
        """
        # Collect all texts for batch embedding
        texts_to_embed = []
        text_metadata = []  # Store metadata for each text
        
        # First, prepare file list if available
        if all_file_paths:
            file_list_content = "## Repository File Structure\n\nThis repository contains the following files:\n\n"
            for fp in all_file_paths:
                file_list_content += f"- {fp}\n"
            file_list_content += f"\n**Total files: {len(all_file_paths)}**"
            
            texts_to_embed.append(file_list_content)
            text_metadata.append({
                'repo_url': repo_url,
                'file_path': '__FILE_LIST__',
                'content': file_list_content,
                'metadata': {
                    'type': 'file_list',
                    'total_files': len(all_file_paths),
                    'file_paths': all_file_paths[:100]
                },
                'user_id': self.user_id,
                'file_type': 'metadata'
            })
            print(f"Prepared file list with {len(all_file_paths)} files")
        
        # Process all documents and collect texts
        for doc in documents:
            file_path = doc.get("file_path", "unknown")
            content = doc.get("content", "")
            
            if not content.strip():
                continue
            
            file_type = self._get_file_type(file_path)
            language = self._get_language_for_extension(file_path)
            
            # Create LlamaIndex document
            llama_doc = Document(text=content)
            
            # Choose splitter based on file type
            if language:
                # Use AST-aware CodeSplitter for supported languages
                try:
                    splitter = self._get_code_splitter(language)
                    nodes = splitter.get_nodes_from_documents([llama_doc])
                    print(f"  AST-chunked {file_path} ({language}): {len(nodes)} chunks")
                except Exception as e:
                    # Fallback to sentence splitter if AST parsing fails
                    print(f"  AST parsing failed for {file_path}, using fallback: {e}")
                    nodes = self.text_splitter.get_nodes_from_documents([llama_doc])
            else:
                # Use sentence splitter for text, markdown, and unsupported code files
                nodes = self.text_splitter.get_nodes_from_documents([llama_doc])
            
            # Collect each chunk
            for i, node in enumerate(nodes):
                texts_to_embed.append(node.text)
                text_metadata.append({
                    'repo_url': repo_url,
                    'file_path': f"{file_path}#chunk_{i}",
                    'content': node.text,
                    'metadata': {
                        'chunk_index': i,
                        'total_chunks': len(nodes),
                        'original_file': file_path,
                        'language': language,
                        'chunking_method': 'ast' if language else 'sentence'
                    },
                    'user_id': self.user_id,
                    'file_type': file_type
                })
        
        if not texts_to_embed:
            return 0
        
        print(f"Processing {len(texts_to_embed)} total chunks...")
        
        # Generate ALL embeddings in one batch - MUCH faster!
        embeddings = self._batch_embed(texts_to_embed)
        
        # Combine embeddings with metadata
        all_records = []
        for i, embedding in enumerate(embeddings):
            record = text_metadata[i].copy()
            record['embedding'] = embedding
            all_records.append(record)
        
        print(f"Storing {len(all_records)} chunks in database...")
        
        # Insert in batches
        batch_size = 50
        total_inserted = 0
        
        for i in range(0, len(all_records), batch_size):
            batch = all_records[i:i + batch_size]
            try:
                self.supabase.table('documents').insert(batch).execute()
                total_inserted += len(batch)
                print(f"Inserted batch {i//batch_size + 1}: {len(batch)} records")
            except Exception as e:
                print(f"Error inserting batch: {e}")
                raise
        
        return total_inserted
    
    def check_repo_exists(self, repo_url: str) -> bool:
        """
        Check if a repository has already been ingested.
        
        Args:
            repo_url: Repository URL to check
            
        Returns:
            True if documents exist for this repo
        """
        try:
            response = self.supabase.table('documents')\
                .select('id')\
                .eq('repo_url', repo_url)\
                .limit(1)\
                .execute()
            return len(response.data) > 0
        except Exception:
            return False
    
    def delete_repo_documents(self, repo_url: str) -> int:
        """
        Delete all documents for a repository.
        
        Args:
            repo_url: Repository URL
            
        Returns:
            Number of documents deleted
        """
        try:
            response = self.supabase.table('documents')\
                .delete()\
                .eq('repo_url', repo_url)\
                .execute()
            return len(response.data) if response.data else 0
        except Exception as e:
            print(f"Error deleting documents: {e}")
            return 0
