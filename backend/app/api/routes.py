"""
API routes for the application.
Defines endpoints for ingestion, querying, and health checks.
"""

from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    IngestRequest, IngestResponse,
    QueryRequest, QueryResponse,
    HealthResponse, ModelsResponse
)
from app.services.github_scraper import GitHubScraper
from app.pipeline.ingest import IngestPipeline
from app.pipeline.query import QueryPipeline
from app.core.llm import get_available_models

router = APIRouter()

# Initialize services
github_scraper = GitHubScraper()

# Lazy initialization of pipelines (heavy model loading)
_ingest_pipeline = None
_query_pipeline = None


def get_ingest_pipeline(user_id: str = "default") -> IngestPipeline:
    """Get or create ingestion pipeline instance."""
    global _ingest_pipeline
    if _ingest_pipeline is None:
        _ingest_pipeline = IngestPipeline(user_id=user_id)
    return _ingest_pipeline


def get_query_pipeline(user_id: str = "default") -> QueryPipeline:
    """Get or create query pipeline instance."""
    global _query_pipeline
    if _query_pipeline is None:
        _query_pipeline = QueryPipeline(user_id=user_id)
    return _query_pipeline


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint to verify API is running.
    """
    return {
        "status": "healthy",
        "message": "GitHub RAG Assistant API is running (LlamaIndex + OpenRouter)"
    }


@router.get("/models", response_model=ModelsResponse)
async def get_models():
    """
    Get available LLM models for query.
    """
    return {
        "models": get_available_models()
    }


@router.post("/ingest", response_model=IngestResponse)
async def ingest_repository(request: IngestRequest):
    """
    Ingest a GitHub repository: scrape, embed, and store in database.
    
    Steps:
    1. Scrape repository content (README, docs, code)
    2. Chunk documents with file-type aware splitting
    3. Generate Jina embeddings for each chunk
    4. Store in Supabase vector database
    """
    try:
        repo_url = request.repo_url.strip()
        user_id = request.user_id or "default"
        
        # Get ingestion pipeline
        ingest_pipeline = get_ingest_pipeline(user_id)
        
        # Check if repository already exists
        if ingest_pipeline.check_repo_exists(repo_url):
            return {
                "status": "info",
                "message": "Repository already ingested. Use query endpoint to ask questions.",
                "documents_processed": 0,
                "repo_url": repo_url
            }
        
        # Step 1: Scrape GitHub repository
        print(f"Scraping repository: {repo_url}")
        documents, all_file_paths = github_scraper.fetch_repository_content(repo_url)
        
        if not documents:
            raise HTTPException(
                status_code=404,
                detail="No content found in repository or repository is private"
            )
        
        print(f"Fetched {len(documents)} documents and {len(all_file_paths)} file paths from repository")
        
        # Step 2, 3, 4: Chunk, embed, and store (including file list metadata)
        num_stored = ingest_pipeline.process_documents(documents, repo_url, all_file_paths)
        
        return {
            "status": "success",
            "message": f"Successfully ingested repository with {num_stored} document chunks",
            "documents_processed": num_stored,
            "repo_url": repo_url
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error ingesting repository: {str(e)}"
        )


@router.post("/query", response_model=QueryResponse)
async def query_repository(request: QueryRequest):
    """
    Ask a question about a GitHub repository.
    
    Steps:
    1. Generate embedding for the question
    2. Retrieve top 10 similar document chunks
    3. Re-rank to top 3 using cross-encoder
    4. Use selected LLM to generate answer
    """
    try:
        repo_url = request.repo_url.strip()
        question = request.question.strip()
        llm_model = request.llm_model
        
        # Get query pipeline
        query_pipeline = get_query_pipeline()
        
        # Check if repository has been ingested
        if not query_pipeline.check_repo_exists(repo_url):
            raise HTTPException(
                status_code=404,
                detail="Repository not found. Please ingest the repository first using the /ingest endpoint."
            )
        
        # Query using RAG pipeline with re-ranking
        print(f"Processing question: {question}")
        print(f"LLM model: {llm_model}")
        result = query_pipeline.query(question, repo_url, llm_model)
        
        return {
            "answer": result['answer'],
            "sources": result['sources'],
            "repo_url": repo_url,
            "llm_used": result['model_used']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error querying repository: {str(e)}"
        )


@router.delete("/repository")
async def delete_repository(repo_url: str):
    """
    Delete a repository's data from the database.
    Useful for re-ingesting a repository.
    """
    try:
        ingest_pipeline = get_ingest_pipeline()
        count = ingest_pipeline.delete_repo_documents(repo_url)
        return {
            "status": "success",
            "message": f"Deleted {count} documents for repository",
            "repo_url": repo_url
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting repository: {str(e)}"
        )