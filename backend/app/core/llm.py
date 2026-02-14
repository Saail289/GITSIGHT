"""
OpenRouter LLM Integration.
Uses native OpenAI client for multiple models via OpenRouter.
"""

import os
from openai import OpenAI


# OpenRouter configuration
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Available models registry
MODELS = {
    "nemotron": {
        "id": "nvidia/nemotron-3-nano-30b-a3b:free",
        "name": "Nemotron 30B (Free)",
        "description": "NVIDIA Nemotron with reasoning capabilities",
        "supports_reasoning": True,
        "max_tokens": 4096,
    },
    "gpt-oss": {
        "id": "openai/gpt-oss-120b:free",
        "name": "GPT-OSS 120B (Free)",
        "description": "OpenAI's open-source 120B parameter model",
        "supports_reasoning": False,
        "max_tokens": 4096,
    },
}

DEFAULT_MODEL = "nemotron"


def get_openai_client() -> OpenAI:
    """Get OpenAI client configured for OpenRouter."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable is required")
    
    return OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=api_key,
        default_headers={
            "HTTP-Referer": "https://gitsight-ivory.vercel.app",
            "X-Title": "GitSight",
        }
    )


def generate_answer(prompt: str, enable_reasoning: bool = True, model_key: str = None) -> str:
    """
    Generate an answer using selected model via OpenRouter.
    
    Args:
        prompt: The prompt to send to the model
        enable_reasoning: Whether to enable reasoning mode (Nemotron only)
        model_key: Key from MODELS dict (e.g., 'nemotron', 'gpt-oss')
        
    Returns:
        Generated text response
    """
    model_key = model_key or DEFAULT_MODEL
    model_config = MODELS.get(model_key, MODELS[DEFAULT_MODEL])
    
    client = get_openai_client()
    
    try:
        extra_body = {}
        if enable_reasoning and model_config.get("supports_reasoning"):
            extra_body["reasoning"] = {"enabled": True}
        
        response = client.chat.completions.create(
            model=model_config["id"],
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            extra_body=extra_body if extra_body else None,
            max_tokens=model_config["max_tokens"],
            temperature=0.1,
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"Error calling OpenRouter API with {model_config['id']}: {e}")
        raise


def get_available_models() -> dict:
    """Return available model options for frontend display."""
    return {
        key: {
            "name": config["name"],
            "description": config["description"]
        }
        for key, config in MODELS.items()
    }

