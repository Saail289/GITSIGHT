"""
Configuration settings for the application.
Loads environment variables and provides configuration objects.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class Settings:
    """Application settings loaded from environment variables"""
    
    # Supabase settings
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_DB_URL: str = os.getenv("SUPABASE_DB_URL", "")
    
    # GitHub settings
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    
    # OpenRouter API settings
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    
    # Model settings (for reference)
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536
    RERANK_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    
    # LLM settings
    LLM_MODELS = {
        "high_reasoning": "openai/gpt-oss-120b:free",
        "fast": "nvidia/nemotron-3-nano-30b-a3b:free"
    }
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 1024
    
    # RAG settings
    RETRIEVAL_TOP_K: int = 10
    RERANK_TOP_K: int = 3
    
    # API settings - Use FRONTEND_URL env var for production
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    
    @property
    def CORS_ORIGINS(self) -> list:
        """Dynamic CORS origins based on environment"""
        origins = [
            "http://localhost:5173",  # Vue dev server
            "http://localhost:3000",
        ]
        # Add production frontend URL if set
        if self.FRONTEND_URL and self.FRONTEND_URL not in origins:
            origins.append(self.FRONTEND_URL)
        return origins
    
    def validate(self) -> bool:
        """Validate that required settings are present"""
        if not self.SUPABASE_URL or not self.SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")
        
        if not self.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY must be set in .env file")
        
        return True


# Global settings instance
settings = Settings()