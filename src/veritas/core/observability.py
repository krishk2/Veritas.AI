import os
import logging
from typing import List, Any

logger = logging.getLogger("veritas.observability")

def get_observability_callbacks() -> List[Any]:
    """
    Constructs active observability callbacks for Langfuse and registers trace metadata.
    LangSmith is active automatically when LANGCHAIN_TRACING_V2='true' is in the environment.
    """
    callbacks = []

    # 1. LangSmith Check
    if os.getenv("LANGCHAIN_TRACING_V2", "").lower() in ("true", "1") and os.getenv("LANGCHAIN_API_KEY"):
        project = os.getenv("LANGCHAIN_PROJECT", "veritas-ai-production")
        logger.info(f"[OBSERVABILITY] LangSmith Tracing active for project: '{project}'")

    # 2. Langfuse Callback Hook
    langfuse_public = os.getenv("LANGFUSE_PUBLIC_KEY")
    langfuse_secret = os.getenv("LANGFUSE_SECRET_KEY")
    langfuse_host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    if langfuse_public and langfuse_secret:
        try:
            try:
                from langfuse.langchain import CallbackHandler
            except ImportError:
                from langfuse.callback import CallbackHandler
                
            handler = CallbackHandler(
                public_key=langfuse_public,
                secret_key=langfuse_secret,
                host=langfuse_host
            )
            callbacks.append(handler)
            logger.info(f"[OBSERVABILITY] Langfuse CallbackHandler successfully registered (Host: {langfuse_host}).")
        except Exception as e:
            logger.warning(f"[OBSERVABILITY WARNING] Failed to initialize Langfuse callback: {e}")

    return callbacks
