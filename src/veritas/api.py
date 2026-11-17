from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from veritas.db import init_db
from veritas.services.neo4j_service import is_neo4j_available
from veritas.routers import verify_router, claims_router, graph_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure database tables are ready on startup and warm up deduplication index."""
    init_db()
    try:
        from veritas.core.container import container
        dedup = container.get_claim_dedup_service()
        if hasattr(dedup, "hydrate_from_ledger"):
            count = dedup.hydrate_from_ledger()
            print(f"[STARTUP] Warmed semantic deduplication index with {count} verified claims from Truth Ledger.")
    except Exception as e:
        print(f"[STARTUP WARNING] Deduplication index hydration skipped: {e}")
    yield

app = FastAPI(
    title="Veritas.AI Verification API",
    description="Multi-agent verification platform with Dynamic Truth Ledger & Trace-the-Source Graph",
    version="0.1.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Modular Routers
app.include_router(verify_router)
app.include_router(claims_router)
app.include_router(graph_router)

@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint reporting API and Neo4j connectivity status."""
    return {
        "status": "ok",
        "service": "Veritas.AI",
        "neo4j_connected": is_neo4j_available()
    }

def main():
    uvicorn.run("veritas.api:app", host="0.0.0.0", port=8001, reload=True)

if __name__ == "__main__":
    main()
