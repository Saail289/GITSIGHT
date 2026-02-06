"""
RAG (Retrieval Augmented Generation) service.
Handles the complete RAG pipeline: retrieve relevant docs + generate answer.
"""

from typing import List, Dict, Any
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate
from app.services.database import DatabaseService
from app.services.embeddings import EmbeddingService
from app.config.settings import settings


class RAGService:
    """Service for RAG pipeline"""
    
    def __init__(self):
        """Initialize RAG components"""
        self.db = DatabaseService()
        self.embeddings = EmbeddingService()
        
        # Initialize LLM
        self.llm = ChatGroq(
            model=settings.LLM_MODEL,
            api_key=settings.GROQ_API_KEY,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS
        )
        
        # Create prompt template
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful AI assistant that answers questions about GitHub repositories based on their documentation and code.

Your task is to provide accurate, helpful answers based ONLY on the provided context from the repository.

Guidelines:
1. Answer based on the context provided
2. If the context doesn't contain enough information, say so
3. Be concise but thorough
4. Include code examples from the context when relevant
5. Mention which files the information comes from

Context from repository:
{context}
"""),
            ("human", "{question}")
        ])
    
    def retrieve_relevant_documents(
        self,
        question: str,
        repo_url: str
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents for a question.
        
        Args:
            question: User's question
            repo_url: Repository URL to search in
            
        Returns:
            List of relevant documents
        """
        # Generate embedding for the question
        query_embedding = self.embeddings.generate_embedding(question)
        
        # Search for similar documents
        results = self.db.search_similar_documents(
            query_embedding=query_embedding,
            repo_url=repo_url,
            top_k=settings.TOP_K_RESULTS,
            threshold=settings.SIMILARITY_THRESHOLD
        )
        
        return results
    
    def generate_answer(
        self,
        question: str,
        context_docs: List[Dict[str, Any]]
    ) -> str:
        """
        Generate answer using LLM based on retrieved context.
        
        Args:
            question: User's question
            context_docs: Retrieved relevant documents
            
        Returns:
            Generated answer
        """
        # Format context from retrieved documents
        context_parts = []
        for i, doc in enumerate(context_docs, 1):
            file_path = doc['file_path'].split('#')[0]  # Remove chunk index
            content = doc['content']
            similarity = doc.get('similarity', 0)
            
            context_parts.append(
                f"[Document {i} - {file_path} (relevance: {similarity:.2f})]\n{content}\n"
            )
        
        context = "\n---\n".join(context_parts)
        
        # Generate answer using LLM
        messages = self.prompt_template.format_messages(
            context=context,
            question=question
        )
        
        response = self.llm.invoke(messages)
        return response.content
    
    def query(self, question: str, repo_url: str) -> Dict[str, Any]:
        """
        Complete RAG pipeline: retrieve + generate.
        
        Args:
            question: User's question
            repo_url: Repository URL
            
        Returns:
            Dict with answer and sources
        """
        # Retrieve relevant documents
        relevant_docs = self.retrieve_relevant_documents(question, repo_url)
        
        if not relevant_docs:
            return {
                'answer': "I couldn't find relevant information in this repository to answer your question. The repository might not have been ingested yet, or the question might be outside the scope of the available documentation.",
                'sources': []
            }
        
        # Generate answer
        answer = self.generate_answer(question, relevant_docs)
        
        # Format sources
        sources = []
        for doc in relevant_docs:
            file_path = doc['file_path'].split('#')[0]
            sources.append({
                'file_path': file_path,
                'similarity': round(doc.get('similarity', 0), 3),
                'preview': doc['content'][:200] + "..." if len(doc['content']) > 200 else doc['content']
            })
        
        return {
            'answer': answer,
            'sources': sources
        }