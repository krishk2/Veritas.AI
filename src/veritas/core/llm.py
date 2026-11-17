import os
import logging
from typing import Optional, Any, Tuple, List, Dict
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("veritas.llm")

# ==============================================================================
# VERIFIED ACTIVE & PRODUCTION MODELS (Non-retired / Non-decommissioned)
# ==============================================================================
# Filtered Out (Decommissioned / Retired):
# - Groq: 'llama-3-8b-8192', 'llama-3-70b-8192', 'mixtral-8x7b-32768' (SUNSET)
# - Google: 'gemini-1.0-pro', 'gemini-pro', 'text-bison' (DECOMMISSIONED); 'gemini-2.5-flash-lite' (20 RPD CAP)
# Filtered Out (Decommissioned / Retired / Excluded):
# - Groq: 'llama-3-8b-8192', 'llama-3-70b-8192', 'mixtral-8x7b-32768' (SUNSET)
# - Google: 'gemini-1.0-pro', 'gemini-pro', 'text-bison' (DECOMMISSIONED); 'gemini-2.5-flash-lite' (20 RPD CAP)
# - Mistral: All models removed from pipeline as requested
# ==============================================================================

MODELS_CATALOG = {
    "groq": {
        "llama-3.1-8b-instant": "Groq LPU ultra-fast text (~100ms)",
        "llama-3.3-70b-versatile": "Groq LPU 70B flagship reasoning (~400ms)",
        "llama-3.2-11b-vision-preview": "Groq LPU multimodal vision",
    },
    "nvidia": {
        "meta/llama-3.2-11b-vision-instruct": "NVIDIA NIM accelerated vision & keyframe forensics with TensorRT-LLM",
        "meta/llama-3.2-90b-vision-instruct": "NVIDIA NIM flagship 90B vision & multimodal entity grounding",
        "meta/llama-3.3-70b-instruct": "NVIDIA NIM flagship 70B reasoning with TensorRT-LLM",
        "meta/llama-3.1-8b-instruct": "NVIDIA NIM accelerated fast text inference",
        "openai/gpt-oss-120b": "NVIDIA NIM containerized open-weight GPT-OSS 120B reasoning",
        "openai/gpt-oss-20b": "NVIDIA NIM containerized open-weight GPT-OSS 20B fast inference",
        "nvidia/llama-3.3-nemotron-super-49b-v1.5": "NVIDIA Nemotron 49B super-aligned reasoning",
        "nvidia/nemotron-3-nano": "NVIDIA lightweight nano model for rapid classification",
        "nvidia/nemotron-3-super-120b-a12b": "NVIDIA hybrid MoE 120B for multi-agent synthesis",
    },
    "cloudflare": {
        "@cf/meta/llama-3.1-8b-instruct": "Cloudflare Workers AI edge text",
        "llama-4-scout-17b-16e-instruct": "Cloudflare Meta multimodal MoE model",
        "gpt-oss-120b": "Cloudflare open-weight GPT for reasoning and agentic tasks",
        "nemotron-3-120b-a12b": "Cloudflare NVIDIA hybrid MoE for multi-agent systems",
        "deepseek-v4.1-flash-1017": "Cloudflare 552B MoE, long context reasoning",
        "m-moondream3.1-9B-A2B": "Cloudflare vision language model for OCR and visual artifacts",
        "glm-4.7-flash": "Cloudflare multilingual high-throughput generation",
    },
    "google": {
        "gemini-2.5-flash": "Google Gemini 2.5 Flash multimodal vision & high-throughput reasoning",
        "gemini-flash-latest": "Google Gemini Flash latest production alias",
        "gemini-2.0-flash": "Google Gemini 2.0 next-gen multimodal speed",
    },
}

# ==============================================================================
# AGENT-TO-PROVIDER SPECIALIZATION MATRIX
# Matches each agent's specific role to the best provider & model
# ==============================================================================

AGENT_SPECIALIZATION: Dict[str, Dict[str, Any]] = {
    "dedup_agent": {
        "role": "Canonical Query Normalization & Interrogative Stripping",
        "primary": ("groq", "llama-3.1-8b-instant"),
        "fallback": [
            ("nvidia", "meta/llama-3.1-8b-instruct"),
            ("cloudflare", "@cf/meta/llama-3.1-8b-instruct"),
            ("google", "gemini-2.5-flash")
        ],
        "rationale": "Requires sub-100ms response time on LPU hardware so user searches feel instant."
    },
    "evidence_agent": {
        "role": "Zero-Shot NLI & Fine-Grained Sentence Extraction",
        "primary": ("nvidia", "meta/llama-3.1-8b-instruct"),
        "fallback": [
            ("nvidia", "nvidia/nemotron-3-nano"),
            ("groq", "llama-3.1-8b-instant"),
            ("cloudflare", "@cf/meta/llama-3.1-8b-instruct"),
            ("google", "gemini-2.5-flash")
        ],
        "rationale": "NVIDIA NIM TensorRT-accelerated inference provides fast, deterministic sentence classification and NLI."
    },
    "image_agent": {
        "role": "Visual Context, Entity Alignment & Image OCR",
        "primary": ("nvidia", "meta/llama-3.2-11b-vision-instruct"),
        "fallback": [
            ("cloudflare", "m-moondream3.1-9B-A2B"),
            ("groq", "llama-3.2-11b-vision-preview"),
            ("google", "gemini-2.5-flash")
        ],
        "rationale": "NVIDIA NIM containerized vision models provide GPU-optimized image forensic inspection and visual OCR."
    },
    "video_agent": {
        "role": "Temporal Deepfake Forensics & Keyframe Glitch Analysis",
        "primary": ("nvidia", "meta/llama-3.2-11b-vision-instruct"),
        "fallback": [
            ("cloudflare", "m-moondream3.1-9B-A2B"),
            ("groq", "llama-3.2-11b-vision-preview"),
            ("google", "gemini-2.5-flash")
        ],
        "rationale": "NVIDIA NIM TensorRT-accelerated CV models excel at high-throughput keyframe artifact detection."
    },
    "judge_agent": {
        "role": "Multimodal Synthesis, Verdict Determination & Perplexity Citations [1, 2]",
        "primary": ("groq", "llama-3.3-70b-versatile"),
        "fallback": [
            ("nvidia", "meta/llama-3.3-70b-instruct"),
            ("nvidia", "openai/gpt-oss-120b"),
            ("cloudflare", "gpt-oss-120b"),
            ("google", "gemini-2.5-flash")
        ],
        "rationale": "Requires flagship 70B+ / 120B weights to arbitrate conflicting sources, structure paragraphs, and insert exact citations."
    },
    "reputation_agent": {
        "role": "Domain Trust Scoring & Institutional Veracity Verification",
        "primary": ("cloudflare", "@cf/meta/llama-3.1-8b-instruct"),
        "fallback": [
            ("nvidia", "nvidia/nemotron-3-nano"),
            ("groq", "llama-3.1-8b-instant"),
            ("google", "gemini-2.5-flash")
        ],
        "rationale": "Lightweight lookup, fast execution on Cloudflare global edge network or NVIDIA Nemotron Nano."
    }
}

# Cache of verified dead/invalid providers to avoid wasting latency on every agent
DISABLED_PROVIDERS = set()

def _create_client(provider: str, model_name: str, temperature: float = 0.0) -> Optional[Any]:
    """Instantiates a provider client safely, returning None if API key or package is missing."""
    if provider in DISABLED_PROVIDERS:
        return None

    try:
        if provider == "groq":
            groq_key = os.getenv("GROQ_API_KEY", "").strip()
            if not groq_key:
                return None
            from langchain_groq import ChatGroq
            return ChatGroq(
                model=model_name,
                temperature=temperature,
                groq_api_key=groq_key,
                max_retries=1,
                timeout=8
            )

        elif provider == "nvidia":
            nvidia_key = (os.getenv("NVIDIA_API_KEY") or os.getenv("NVIDIA_NIM_API_KEY", "")).strip()
            if not nvidia_key:
                return None
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=model_name,
                temperature=temperature,
                api_key=nvidia_key,
                base_url="https://integrate.api.nvidia.com/v1",
                max_retries=1,
                timeout=8
            )

        elif provider == "cloudflare":
            cf_token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
            cf_account = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
            if not cf_token or not cf_account:
                return None
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=model_name,
                temperature=temperature,
                api_key=cf_token,
                base_url=f"https://api.cloudflare.com/client/v4/accounts/{cf_account}/ai/v1",
                max_retries=1,
                timeout=8
            )

        elif provider == "google":
            gemini_key = (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY", "")).strip()
            if not gemini_key:
                return None
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=model_name,
                temperature=temperature,
                google_api_key=gemini_key,
                max_retries=2,
                request_timeout=30
            )

    except Exception as e:
        logger.warning(f"Error creating client for {provider}/{model_name}: {e}")
        return None

    return None

def get_agent_llm(agent_name: str, temperature: float = 0.0) -> Any:
    """
    Returns the optimal, bespoke LLM client for a specific agent across providers.
    Supports user env overrides (e.g. JUDGE_AGENT_PROVIDER=mistral, JUDGE_AGENT_MODEL=mistral-large-latest).
    Falls back gracefully to other active provider keys if the primary provider key is unset.
    """
    spec = AGENT_SPECIALIZATION.get(agent_name, AGENT_SPECIALIZATION["judge_agent"])

    # 1. Check for explicit per-agent environment override
    env_prefix = agent_name.upper()
    override_provider = os.getenv(f"{env_prefix}_PROVIDER", "").lower().strip()
    override_model = os.getenv(f"{env_prefix}_MODEL", "").strip()

    candidate_chain: List[Tuple[str, str]] = []

    if override_provider:
        # User specified custom provider for this agent
        default_model_for_prov = list(MODELS_CATALOG.get(override_provider, {}).keys())[0] if override_provider in MODELS_CATALOG else "default"
        candidate_chain.append((override_provider, override_model or default_model_for_prov))

    # Add primary specialized provider/model
    candidate_chain.append(spec["primary"])

    # Add fallback cascade
    for fb in spec["fallback"]:
        candidate_chain.append(fb)

    # Collect all available clients in candidate order to enable automatic runtime fallback
    active_clients = []
    seen = set()

    for provider, model_name in candidate_chain:
        pair_key = f"{provider}:{model_name}"
        if pair_key in seen:
            continue
        seen.add(pair_key)
        client = _create_client(provider, model_name, temperature=temperature)
        if client:
            active_clients.append(client)

    if not active_clients:
        raise RuntimeError(
            f"Unable to initialize LLM for agent '{agent_name}'. "
            f"Attempted candidates: {candidate_chain}. Please add active keys in .env for "
            f"GROQ_API_KEY, NVIDIA_API_KEY, CLOUDFLARE_API_TOKEN, or GOOGLE_API_KEY."
        )

    primary = active_clients[0]
    if len(active_clients) > 1:
        # Wrap primary with graceful runtime fallbacks (handles 401, 404, 429 automatically!)
        logger.info(f"[Agent Model Router] {agent_name} -> primary={type(primary).__name__} with {len(active_clients)-1} fallback(s)")
        return primary.with_fallbacks(active_clients[1:])

    logger.info(f"[Agent Model Router] {agent_name} -> primary={type(primary).__name__}")
    return primary

# ==============================================================================
# CONVENIENCE HELPERS FOR BACKWARD COMPATIBILITY
# ==============================================================================

def get_fast_llm(temperature: float = 0.0) -> Any:
    return get_agent_llm("dedup_agent", temperature=temperature)

def get_reasoning_llm(temperature: float = 0.0) -> Any:
    return get_agent_llm("judge_agent", temperature=temperature)

def get_vision_llm(temperature: float = 0.0) -> Any:
    return get_agent_llm("image_agent", temperature=temperature)

def get_chat_llm(temperature: float = 0.0, model: Optional[str] = None) -> Any:
    return get_agent_llm("judge_agent", temperature=temperature)
