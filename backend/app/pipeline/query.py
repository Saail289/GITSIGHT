"""
Query Pipeline using LlamaIndex for embeddings and OpenRouter for LLM.
Implements semantic retrieval and answer generation.
"""

import os
from typing import List, Dict, Any, Optional

from llama_index.core import Settings
from llama_index.embeddings.openai import OpenAIEmbedding
from supabase import create_client, Client

from app.core.llm import generate_answer


class QueryPipeline:
    """
    Query pipeline with semantic retrieval.
    Retrieves top-k documents and synthesizes answer using Nemotron.
    """
    
    def __init__(self, user_id: Optional[str] = None):
        """
        Initialize the query pipeline.
        
        Args:
            user_id: Optional user ID for RLS filtering
        """
        self.user_id = user_id or "default"
        
        # Initialize OpenAI embedding model via OpenRouter (must match ingest pipeline!)
        print("Initializing OpenAI embeddings via OpenRouter for query...")
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY is required for embeddings")
        
        self.embed_model = OpenAIEmbedding(
            model="text-embedding-3-small",
            api_key=openrouter_api_key,
            api_base="https://openrouter.ai/api/v1"
        )
        Settings.embed_model = self.embed_model
        
        # Initialize Supabase client
        self._init_supabase()
    
    def _init_supabase(self):
        """Initialize Supabase client."""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY are required")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
    
    def _search_similar(self, query_embedding: List[float], repo_url: str, top_k: int = 10, threshold: float = 0.15) -> List[Dict]:
        """Search for similar documents using Supabase RPC."""
        try:
            response = self.supabase.rpc(
                'match_documents',
                {
                    'query_embedding': query_embedding,
                    'match_repo_url': repo_url,
                    'match_threshold': threshold,  # Lower threshold to get more results
                    'match_count': top_k
                }
            ).execute()
            return response.data or []
        except Exception as e:
            print(f"Error searching documents: {e}")
            return []
    
    def _extract_filename_from_question(self, question: str) -> Optional[str]:
        """
        Extract a filename from the question if the user is asking about a specific file.
        Returns the filename (e.g., 'app.py') or None if no specific file is mentioned.
        """
        import re
        question_lower = question.lower()
        
        # Patterns that indicate file-specific questions
        file_patterns = [
            r'explain\s+(?:the\s+)?(?:code\s+in\s+)?["\']?(\w+\.\w+)["\']?',
            r'what\s+(?:does|is)\s+["\']?(\w+\.\w+)["\']?',
            r'describe\s+["\']?(\w+\.\w+)["\']?',
            r'analyze\s+["\']?(\w+\.\w+)["\']?',
            r'show\s+(?:me\s+)?["\']?(\w+\.\w+)["\']?',
            r'about\s+["\']?(\w+\.\w+)["\']?',
            r'in\s+["\']?(\w+\.\w+)["\']?',
            r'["\']?(\w+\.(?:py|js|ts|java|go|rs|rb|cpp|c|html|css))["\']?',  # Direct file reference
        ]
        
        for pattern in file_patterns:
            match = re.search(pattern, question_lower)
            if match:
                return match.group(1)
        
        return None
    
    def _get_file_chunks(self, repo_url: str, filename: str) -> List[Dict]:
        """
        Get ALL chunks for a specific file.
        This ensures complete file coverage when user asks about a specific file.
        """
        try:
            # Search for chunks where file_path contains the filename
            response = self.supabase.table('documents')\
                .select('id, repo_url, file_path, content, file_type')\
                .eq('repo_url', repo_url)\
                .ilike('file_path', f'%{filename}%')\
                .order('file_path')\
                .execute()
            
            # Add similarity score and sort by chunk index
            docs = []
            for doc in response.data or []:
                doc['similarity'] = 1.0  # High score since it's an exact file match
                docs.append(doc)
            
            # Sort by chunk index to maintain order
            docs.sort(key=lambda x: x['file_path'])
            
            print(f"Found {len(docs)} chunks for file '{filename}'")
            return docs
        except Exception as e:
            print(f"Error getting file chunks: {e}")
            return []
    
    def _get_all_documents(self, repo_url: str, limit: int = 10) -> List[Dict]:
        """Fallback: Get all documents for a repo when semantic search fails."""
        try:
            response = self.supabase.table('documents')\
                .select('id, repo_url, file_path, content, file_type')\
                .eq('repo_url', repo_url)\
                .limit(limit)\
                .execute()
            
            # Add a default similarity score
            docs = []
            for doc in response.data or []:
                doc['similarity'] = 0.5  # Default score for fallback
                docs.append(doc)
            return docs
        except Exception as e:
            print(f"Error getting documents: {e}")
            return []
    
    def _get_file_list(self, repo_url: str) -> str:
        """Retrieve the file list metadata for a repository."""
        try:
            response = self.supabase.table('documents')\
                .select('content')\
                .eq('repo_url', repo_url)\
                .eq('file_path', '__FILE_LIST__')\
                .limit(1)\
                .execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]['content']
            return None
        except Exception as e:
            print(f"Error getting file list: {e}")
            return None
    
    def query(
        self,
        question: str,
        repo_url: str,
        model_preference: str = "nemotron"
    ) -> Dict[str, Any]:
        """
        Execute a RAG query: retrieve and generate answer.
        
        Args:
            question: User's question
            repo_url: Repository URL to search in
            model_preference: Model to use (currently only nemotron)
            
        Returns:
            Dict containing answer and source documents
        """
        print(f"Processing query: {question}")
        
        # Check if question is about a specific file
        target_file = self._extract_filename_from_question(question)
        
        if target_file:
            # File-focused retrieval: get ALL chunks from the specific file
            print(f"Detected file-specific question for: {target_file}")
            documents = self._get_file_chunks(repo_url, target_file)
        else:
            # General semantic search
            query_embedding = self.embed_model.get_query_embedding(question)
            documents = self._search_similar(query_embedding, repo_url, top_k=10, threshold=0.15)
        
        # Fallback: if no matches, get documents directly
        if not documents:
            print("No semantic matches found, using fallback...")
            documents = self._get_all_documents(repo_url, limit=5)
        
        if not documents:
            return {
                "answer": "I couldn't find any documents for this repository. The repository might not have been ingested yet.",
                "sources": [],
                "model_used": "nemotron"
            }
        
        print(f"Retrieved {len(documents)} documents")
        
        # Get file list metadata (always include for complete file awareness)
        file_list = self._get_file_list(repo_url)
        
        # Take top 10 for more comprehensive context
        top_docs = documents[:10]
        
        # Build context from documents
        context_parts = []
        
        # Always include file list first if available
        if file_list:
            context_parts.append(f"[COMPLETE FILE LIST]\n{file_list}\n")
        
        for i, doc in enumerate(top_docs, 1):
            file_path = doc['file_path'].split('#')[0]
            if file_path == '__FILE_LIST__':
                continue  # Skip file list doc, already included
            content = doc['content']
            context_parts.append(f"[Document {i} - {file_path}]\n{content}\n")
        
        context = "\n---\n".join(context_parts)
        
        # Build prompt with comprehensive explanation instructions
        prompt = f"""You are a helpful AI assistant that explains GitHub repositories in a clear, structured, and comprehensive way.

FORMATTING RULES:
- Use ### for main section headers
- Use **bold** for important terms, file names, and function names
- Use bullet points (- ) for lists
- For code, use triple backticks with the language: ```python, ```javascript, etc.
- Keep paragraphs short and readable
- Use `backticks` for inline code references

EXPLANATION GUIDELINES:
When explaining code, be COMPREHENSIVE and THOROUGH:
1. **Libraries & Imports**: Explain ALL imported libraries and their purpose
2. **Configuration/Constants**: Explain any configuration variables, constants, or settings
3. **Functions & Classes**: Explain EACH function/class - what it does, parameters, return values
4. **Main Logic**: Explain the main execution flow step by step
5. **Relationships**: Show how different parts of the code connect together

For each code section, show the relevant code snippet followed by a clear explanation.
Structure your response in logical sections (e.g., "### 1. Imports & Dependencies", "### 2. Configuration", "### 3. Helper Functions", etc.)

Context from the repository:
{context}

Question: {question}

Provide a well-structured, comprehensive answer. If asked about code, explain it thoroughly in organized sections:"""
        
        # Generate answer using selected model via OpenRouter
        try:
            answer = generate_answer(prompt, enable_reasoning=True, model_key=model_preference)
        except Exception as e:
            print(f"LLM error: {e}")
            answer = f"Error generating answer: {str(e)}"
        
        # Format sources
        sources = []
        for doc in top_docs:
            file_path = doc['file_path'].split('#')[0]
            sources.append({
                "file_path": file_path,
                "similarity": round(doc.get('similarity', 0), 3),
                "preview": doc['content'][:200] + "..." if len(doc['content']) > 200 else doc['content'],
                "file_type": doc.get('file_type', 'unknown')
            })
        
        return {
            "answer": answer,
            "sources": sources,
            "model_used": model_preference or "nemotron"
        }
    
    def check_repo_exists(self, repo_url: str) -> bool:
        """
        Check if a repository has been ingested.
        
        Args:
            repo_url: Repository URL to check
            
        Returns:
            True if documents exist
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
