import os
import json
import time
from urllib.parse import urlparse
from typing import AsyncGenerator, Dict, Any, List, Tuple, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from veritas.schemas.claim import VerifyRequest, VerifyResponse, SourceCitation, AgentExecutionStep
from veritas.core.graph import create_graph
from veritas.core.observability import get_observability_callbacks
from veritas.core.container import container

router = APIRouter(tags=["Verification"])

# Lazy-loaded LangGraph instance
graph_app = None

def get_graph():
    global graph_app
    if graph_app is None:
        print("Initializing LangGraph...")
        graph_app = create_graph()
        print("LangGraph Initialized.")
    return graph_app

# Comprehensive metadata for every agent in the Veritas DAG
AGENT_METADATA: Dict[str, Dict[str, Any]] = {
    "dedup_agent": {
        "name": "Semantic Deduplication & Cache",
        "role": "Check truth ledger for semantically duplicate claims to avoid redundant verification",
        "tools": ["GoogleGenerativeAIEmbeddings(text-embedding-004)", "CosineSimilarityIndex", "SHA256 Hasher"],
    },
    "source_agent": {
        "name": "Web Intelligence & Search",
        "role": "Discover authoritative web coverage, fact checks, and source documents",
        "tools": ["TavilySearchResults(max_results=5)", "Domain Filter", "Query Reformulator"],
    },
    "image_agent": {
        "name": "Multimodal Image Forensics",
        "role": "Analyze image media for JPEG compression anomalies, metadata tampering, and AI generation",
        "tools": ["Error Level Analysis (ELA 95%)", "EXIF Camera Inspector", "Laplacian Edge Variance"],
    },
    "video_agent": {
        "name": "Video Deepfake & Face Consistency",
        "role": "Detect temporal warping, facial artifacts, and synthetic video generation markers",
        "tools": ["OpenCV Temporal Differencing", "Deepfake Artifact Detector", "FFmpeg Frame Analyzer"],
    },
    "reverse_image_agent": {
        "name": "Visual Provenance & Reverse Search",
        "role": "Trace origin, timestamp of earliest publication, and recycled out-of-context images",
        "tools": ["Perceptual Hash (pHash)", "Reverse Image Engine", "Origin Timestamp Cross-Referencer"],
    },
    "fetch_agent": {
        "name": "DOM Scraper & Text Normalizer",
        "role": "Download full HTML web pages, remove scripts/ads, and segment into text chunks",
        "tools": ["requests.Session(User-Agent)", "BeautifulSoup4 (DOM Stripper)", "RecursiveCharacterTextSplitter(1000)"],
    },
    "retriever_agent": {
        "name": "Vector Store & Passage Ranking",
        "role": "Embed text chunks into high-dimensional space and rank top-k factual passages",
        "tools": ["GoogleGenerativeAIEmbeddings(text-embedding-004)", "FAISS Vector Index (faiss-cpu)", "Top-K Similarity Scorer"],
    },
    "evidence_agent": {
        "name": "NLI Evidence Classification",
        "role": "Extract textual and visual claims, classifying each into SUPPORT or REFUTE with confidence",
        "tools": ["ChatGoogleGenerativeAI(gemini-flash-latest)", "Zero-Shot NLI Classification Chain", "Cross-Modal Evidence Fuser"],
    },
    "judge_agent": {
        "name": "Cited Truth Judge & Synthesizer",
        "role": "Evaluate all cross-modal evidence and issue an authoritative verdict with inline Perplexity-style citations [1, 2]",
        "tools": ["ChatGoogleGenerativeAI(gemini-flash-latest)", "Perplexity Citation Formatter", "JsonOutputParser"],
    },
    "reputation_agent": {
        "name": "Source Credibility Auditor",
        "role": "Audit domain reputation, institutional trust, and historical veracity scores",
        "tools": ["Domain Trust Matrix", "WHOIS & TLD Authority Verifier", "Credibility Weighting Engine"],
    },
    "ledger_agent": {
        "name": "Neon Postgres & Knowledge Graph",
        "role": "Persist the complete tamper-evident audit trail into cloud Postgres and provenance graph",
        "tools": ["SQLModel / Neon Serverless Postgres Driver", "Neon S3 Object Storage (Bucket: assets)", "Neo4j Cypher Session"],
    },
    "parallel_investigation_agent": {
        "name": "Parallel Multimodal Fan-Out",
        "role": "Concurrently executes Web Retrieval, Domain Trust, Image Forensics, and Video Deepfake Analysis",
        "tools": ["DuckDuckGo Hybrid Search", "FAISS In-Memory Vector Store", "OpenCV ELA Analyzer", "Temporal Face Inconsistency Checker"],
    },
}

def build_step_summary(node_name: str, state_before: dict, update: dict, duration_ms: int) -> AgentExecutionStep:
    meta = AGENT_METADATA.get(node_name, {
        "name": node_name.replace("_", " ").title(),
        "role": "Graph execution node",
        "tools": ["Internal Tool"]
    })

    inputs = {}
    outputs = {}

    if node_name == "dedup_agent":
        inputs = {"raw_claim": state_before.get("claim", "")[:120]}
        outputs = {
            "canonical_claim": update.get("canonical_claim"),
            "is_duplicate": update.get("is_duplicate", False),
            "similarity_score": update.get("similarity_score", 0.0)
        }
    elif node_name == "source_agent":
        inputs = {"query": state_before.get("canonical_claim") or state_before.get("claim", "")}
        srcs = update.get("sources", [])
        outputs = {
            "sources_found": len(srcs),
            "top_domains": [s.get("domain") or urlparse(s.get("url", "")).netloc for s in srcs[:3]]
        }
    elif node_name == "image_agent":
        inputs = {"has_image": bool(state_before.get("image_base64"))}
        forensics = update.get("image_forensics", {})
        outputs = {
            "ai_detected": forensics.get("ai_generation_detected", False),
            "ela_score": forensics.get("ela_score", 0.0),
            "tampering_alerts": forensics.get("tampering_indicators", [])[:2]
        }
    elif node_name == "video_agent":
        inputs = {"has_video": bool(state_before.get("video_base64"))}
        vforensics = update.get("video_forensics", {})
        outputs = {
            "deepfake_detected": vforensics.get("is_deepfake_or_ai", False),
            "confidence": vforensics.get("confidence", 0.0)
        }
    elif node_name == "fetch_agent":
        inputs = {"urls_to_scrape": len(state_before.get("sources", []))}
        chunks = update.get("chunks", [])
        outputs = {"chunks_extracted": len(chunks), "avg_chunk_size": 1000}
    elif node_name == "retriever_agent":
        inputs = {"chunks_indexed": len(state_before.get("chunks", [])), "query": state_before.get("claim", "")}
        passages = update.get("retrieved_passages", [])
        outputs = {"top_passages_retrieved": len(passages)}
    elif node_name == "evidence_agent":
        inputs = {"passages_to_analyze": len(state_before.get("retrieved_passages", []))}
        ev_items = update.get("evidence", [])
        outputs = {
            "evidence_count": len(ev_items),
            "support_count": sum(1 for e in ev_items if e.get("label") == "SUPPORT"),
            "refute_count": sum(1 for e in ev_items if e.get("label") == "REFUTE")
        }
    elif node_name == "judge_agent":
        inputs = {
            "evidence_items": len(state_before.get("evidence", [])),
            "sources": len(state_before.get("sources", []))
        }
        outputs = {
            "verdict": update.get("verdict"),
            "confidence": update.get("confidence"),
            "has_citations": "[" in update.get("explanation", "")
        }
    elif node_name == "reputation_agent":
        inputs = {"domains": len(state_before.get("sources", []))}
        rep = update.get("credibility_report", [])
        outputs = {"audited_domains": len(rep)}
    elif node_name == "ledger_agent":
        inputs = {"verdict": state_before.get("verdict"), "confidence": state_before.get("confidence")}
        outputs = {
            "record_id": update.get("record_id"),
            "target": "Neon Serverless Postgres neondb",
            "table": "claim_records"
        }
    elif node_name == "parallel_investigation_agent":
        inputs = {"claim": state_before.get("claim", "")[:80]}
        outputs = {
            "sources_found": len(update.get("sources", [])),
            "passages_retrieved": len(update.get("retrieved_passages", [])),
            "has_image": bool(state_before.get("image_base64")),
            "has_video": bool(state_before.get("video_base64"))
        }
    else:
        inputs = {"keys": list(state_before.keys())[:3]}
        outputs = {"updated_keys": list(update.keys())}

    return AgentExecutionStep(
        agent_id=node_name,
        agent_name=meta["name"],
        role=meta["role"],
        tools=meta["tools"],
        inputs=inputs,
        outputs=outputs,
        duration_ms=duration_ms,
        status="completed"
    )

def build_sources_citation(result: dict) -> list[SourceCitation]:
    credibility_map = {}
    for cred in result.get("credibility_report", []):
        if "url" in cred:
            credibility_map[cred["url"]] = cred
        if "domain" in cred:
            credibility_map[cred["domain"]] = cred

    sources_out: list[SourceCitation] = []
    for idx, src in enumerate(result.get("sources", []), start=1):
        url = src.get("url", "")
        domain = "web.source"
        if url:
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.replace("www.", "") if parsed.netloc else "web.source"
            except Exception:
                domain = "web.source"
        
        cred = credibility_map.get(url) or credibility_map.get(domain) or {}
        favicon = f"https://www.google.com/s2/favicons?domain={domain}&sz=64"
        sources_out.append(SourceCitation(
            citation_id=idx,
            title=src.get("title") or domain,
            url=url,
            domain=domain,
            favicon_url=favicon,
            credibility_status=cred.get("status", "Neutral"),
            credibility_score=float(cred.get("score", 0.5)),
            snippet=src.get("content", "")[:300] if src.get("content") else None
        ))
    return sources_out

def build_provenance_graph(record_id: str, current_state: dict, sources: list) -> Tuple[bool, Dict[str, Any]]:
    graph_repo = container.get_graph_repository()
    neo4j_online = graph_repo.is_available()
    subgraph = None
    if neo4j_online and record_id and not current_state.get("is_duplicate"):
        try:
            subgraph = graph_repo.get_subgraph(record_id)
        except Exception:
            subgraph = None

    if subgraph and subgraph.get("nodes") and len(subgraph["nodes"]) > 0:
        return True, subgraph

    # In-memory graph synthesis
    nodes = []
    edges = []
    
    # 1. Claim Node (Center)
    claim_id = f"claim_{record_id or 'latest'}"
    verdict = current_state.get("verdict", "UNKNOWN")
    nodes.append({
        "id": claim_id,
        "label": "Claim",
        "type": "claim",
        "title": current_state.get("claim", "")[:100],
        "verdict": verdict,
        "confidence": current_state.get("adjusted_confidence", current_state.get("confidence", 0.0))
    })

    # 2. Evidence Nodes
    for idx, ev in enumerate(current_state.get("evidence", [])[:6]):
        ev_id = f"evidence_{idx}"
        label = ev.get("label", "INFO")
        nodes.append({
            "id": ev_id,
            "label": f"Evidence ({label})",
            "type": "evidence",
            "title": ev.get("sentence", "")[:90] + "...",
            "score": ev.get("score", 0.8),
            "verdict": label
        })
        edges.append({
            "source": claim_id,
            "target": ev_id,
            "label": f"HAS_EVIDENCE [{label}]"
        })

    # 3. Source Nodes
    for idx, s in enumerate(sources[:6]):
        s_id = f"source_{getattr(s, 'citation_id', idx)}"
        nodes.append({
            "id": s_id,
            "label": "Source",
            "type": "source",
            "domain": getattr(s, "domain", ""),
            "title": getattr(s, "title", ""),
            "url": getattr(s, "url", ""),
            "credibility_status": getattr(s, "credibility_status", "Neutral")
        })
        edges.append({
            "source": claim_id,
            "target": s_id,
            "label": "INVESTIGATED_SOURCE"
        })

    # 4. Forensics Node (if image or video)
    if current_state.get("image_forensics", {}).get("has_image"):
        f_id = "node_image_forensics"
        im_f = current_state.get("image_forensics", {})
        nodes.append({
            "id": f_id,
            "label": "Image Forensics",
            "type": "forensics",
            "title": im_f.get("summary", "Vision & ELA checked")[:80],
            "is_tampered": im_f.get("is_tampered_or_ai", False)
        })
        edges.append({
            "source": claim_id,
            "target": f_id,
            "label": "IMAGE_FORENSICS"
        })

    return neo4j_online, {
        "connected": neo4j_online,
        "claim_id": record_id,
        "nodes": nodes,
        "edges": edges
    }

@router.post("/verify", response_model=VerifyResponse)
def verify_claim(request: VerifyRequest):
    """
    Submits a claim through the Veritas.AI multi-agent verification pipeline
    and returns full result along with agent execution trace and tool telemetry.
    """
    claim_text = (request.claim or "").strip()
    has_image = bool(request.image_base64)
    has_video = bool(request.video_base64)
    
    if not claim_text and has_image:
        claim_text = "Verify the authenticity and origin of this image."
    elif not claim_text and has_video:
        claim_text = "Verify whether this video is an AI-generated synthetic creation or deepfake."
    elif not claim_text and not has_image and not has_video:
        raise HTTPException(status_code=400, detail="Either a text claim, an image, or a video must be provided.")

    try:
        initial_state = {
            "claim": claim_text,
            "image_base64": request.image_base64,
            "video_base64": request.video_base64
        }
        
        config = {}
        callbacks = get_observability_callbacks()
        if callbacks:
            config["callbacks"] = callbacks

        active_graph = get_graph()
        
        # Stream the graph step-by-step to capture exact tool usage, data-flow, and timing
        current_state = dict(initial_state)
        execution_trace: List[AgentExecutionStep] = []

        step_t0 = time.time()
        for event in active_graph.stream(initial_state, config=config if config else None, stream_mode="updates"):
            step_duration = int((time.time() - step_t0) * 1000)
            for node_name, node_update in event.items():
                trace_step = build_step_summary(node_name, current_state, node_update, step_duration)
                execution_trace.append(trace_step)
                current_state.update(node_update)
            step_t0 = time.time()

        sources_out = build_sources_citation(current_state)
        neo4j_online, prov_graph = build_provenance_graph(
            current_state.get("record_id", ""),
            current_state,
            sources_out
        )

        return VerifyResponse(
            record_id=current_state.get("record_id"),
            status=current_state.get("status", "VERIFIED"),
            verdict=current_state.get("verdict", "UNKNOWN"),
            confidence=current_state.get("adjusted_confidence", current_state.get("confidence", 0.0)),
            explanation=current_state.get("explanation", "No explanation provided."),
            evidence=current_state.get("evidence", []),
            credibility_report=current_state.get("credibility_report", []),
            sources=sources_out,
            has_image=has_image,
            has_video=has_video,
            canonical_claim=current_state.get("canonical_claim"),
            is_duplicate=bool(current_state.get("is_duplicate", False)),
            image_forensics=current_state.get("image_forensics"),
            image_metadata=current_state.get("image_metadata"),
            video_forensics=current_state.get("video_forensics"),
            execution_trace=execution_trace,
            neo4j_connected=neo4j_online,
            provenance_graph=prov_graph
        )

    except Exception as e:
        print(f"Error processing claim: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _stream_verification(initial_claim: str, image_base64: Optional[str] = None, video_base64: Optional[str] = None):
    """Core generator yielding Server-Sent Events (SSE) as each agent executes."""
    claim_text = (initial_claim or "").strip()
    has_image = bool(image_base64)
    has_video = bool(video_base64)

    if not claim_text and has_image:
        claim_text = "Verify the authenticity and origin of this image."
    elif not claim_text and has_video:
        claim_text = "Verify whether this video is an AI-generated synthetic creation or deepfake."

    def event_generator():
        initial_state = {
            "claim": claim_text,
            "image_base64": image_base64,
            "video_base64": video_base64
        }

        active_graph = get_graph()
        current_state = dict(initial_state)
        step_number = 1
        step_t0 = time.time()
        execution_trace = []

        yield f"event: start\ndata: {json.dumps({'message': 'Multi-agent LangGraph workflow initiated', 'claim': claim_text})}\n\n"

        try:
            for event in active_graph.stream(initial_state, stream_mode="updates"):
                step_duration = int((time.time() - step_t0) * 1000)
                for node_name, node_update in event.items():
                    step_meta = build_step_summary(node_name, current_state, node_update, step_duration)
                    execution_trace.append(step_meta)
                    current_state.update(node_update)

                    payload = {
                        "step": step_number,
                        "agent_id": step_meta.agent_id,
                        "agent_name": step_meta.agent_name,
                        "role": step_meta.role,
                        "tools": step_meta.tools,
                        "inputs": step_meta.inputs,
                        "outputs": step_meta.outputs,
                        "duration_ms": step_meta.duration_ms,
                        "status": "completed"
                    }
                    yield f"event: agent_step\ndata: {json.dumps(payload)}\n\n"
                    step_number += 1
                step_t0 = time.time()

            sources_out = build_sources_citation(current_state)
            sources_dicts = [s.model_dump() for s in sources_out]
            neo4j_online, prov_graph = build_provenance_graph(
                current_state.get("record_id", ""),
                current_state,
                sources_out
            )

            final_payload = {
                "record_id": current_state.get("record_id"),
                "status": current_state.get("status", "VERIFIED"),
                "verdict": current_state.get("verdict", "UNKNOWN"),
                "confidence": current_state.get("adjusted_confidence", current_state.get("confidence", 0.0)),
                "explanation": current_state.get("explanation", ""),
                "sources": sources_dicts,
                "evidence": current_state.get("evidence", []),
                "credibility_report": current_state.get("credibility_report", []),
                "has_image": has_image,
                "has_video": has_video,
                "canonical_claim": current_state.get("canonical_claim"),
                "is_duplicate": bool(current_state.get("is_duplicate", False)),
                "image_forensics": current_state.get("image_forensics"),
                "image_metadata": current_state.get("image_metadata"),
                "video_forensics": current_state.get("video_forensics"),
                "execution_trace": [t.model_dump() for t in execution_trace],
                "neo4j_connected": neo4j_online,
                "provenance_graph": prov_graph
            }
            yield f"event: complete\ndata: {json.dumps(final_payload)}\n\n"

        except Exception as e:
            print(f"Error in streaming graph: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.post("/verify/stream")
def verify_claim_stream_post(request: VerifyRequest):
    """
    POST Server-Sent Events (SSE) endpoint streaming real-time agent execution events,
    tool calls, input-output data flow, and final verdict as each node in the LangGraph completes.
    """
    return _stream_verification(
        initial_claim=request.claim or "",
        image_base64=request.image_base64,
        video_base64=request.video_base64
    )

@router.get("/verify/stream")
def verify_claim_stream_get(
    claim: str = Query(..., description="The claim to verify in real-time streaming mode")
):
    """GET Server-Sent Events (SSE) endpoint for quick browser testing."""
    return _stream_verification(initial_claim=claim)
