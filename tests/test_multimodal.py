import io
import base64
import pytest
from PIL import Image, PngImagePlugin
from veritas.services.image_service import (
    PillowImageForensicsService,
    WebReverseImageProvider,
    compute_dhash,
    compute_ela_score
)
from veritas.agents.image_agent import image_agent
from veritas.agents.reverse_image_agent import reverse_image_agent
from veritas.agents.evidence_agent import evidence_agent
from veritas.agents.judge_agent import judge_agent
from veritas.core.container import container
from veritas.core.interfaces import ISearchProvider

def create_test_image_base64(format="PNG", text_info=None) -> str:
    """Helper to generate an in-memory base64 encoded image."""
    img = Image.new("RGB", (100, 100), color=(73, 109, 137))
    buffer = io.BytesIO()
    
    if format == "PNG" and text_info:
        pnginfo = PngImagePlugin.PngInfo()
        for k, v in text_info.items():
            pnginfo.add_text(k, v)
        img.save(buffer, format=format, pnginfo=pnginfo)
    else:
        img.save(buffer, format=format)
        
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

def test_image_forensics_basic():
    service = PillowImageForensicsService()
    img_b64 = create_test_image_base64()
    
    analysis = service.analyze(img_b64)
    assert analysis["format"] == "PNG"
    assert analysis["dimensions"]["width"] == 100
    assert analysis["dimensions"]["height"] == 100
    assert "dhash" in analysis["hashes"]
    assert "md5" in analysis["hashes"]
    assert analysis["is_tampered_or_ai"] is False

def test_image_forensics_ai_generation_markers():
    service = PillowImageForensicsService()
    # Simulate Stable Diffusion generation metadata embedded in PNG
    ai_metadata = {
        "parameters": "photorealistic portrait, 8k, Steps: 20, Sampler: DPM++ 2M, Model: Stable Diffusion XL"
    }
    img_b64 = create_test_image_base64(format="PNG", text_info=ai_metadata)
    
    analysis = service.analyze(img_b64)
    assert analysis["ai_generation_detected"] is True
    assert analysis["is_tampered_or_ai"] is True
    assert any("stable diffusion" in marker.lower() for marker in analysis["ai_markers"])

def test_image_forensics_photoshop_tampering():
    service = PillowImageForensicsService()
    # Simulate Photoshop software signature
    software_metadata = {
        "Software": "Adobe Photoshop 2024 (Windows)"
    }
    img_b64 = create_test_image_base64(format="PNG", text_info=software_metadata)
    
    analysis = service.analyze(img_b64)
    assert analysis["is_tampered_or_ai"] is True
    assert any("Adobe Photoshop" in indicator for indicator in analysis["tampering_indicators"])

def test_perceptual_hash_stability():
    img1 = Image.new("RGB", (64, 64), color="red")
    img2 = Image.new("RGB", (64, 64), color="red")
    img3 = Image.new("RGB", (64, 64), color="blue")
    
    hash1 = compute_dhash(img1)
    hash2 = compute_dhash(img2)
    hash3 = compute_dhash(img3)
    
    assert hash1 == hash2
    assert len(hash1) == 16

def test_ela_score():
    img = Image.new("RGB", (100, 100), color="green")
    score = compute_ela_score(img)
    assert 0.0 <= score <= 1.0

class MockRecyclingSearchProvider(ISearchProvider):
    def search(self, query: str, max_results: int = 5):
        return [
            {
                "url": "https://archive.org/news/2017/old-protest-rally.html",
                "title": "Mass protest in Madrid (2017)",
                "content": "Archived photos from the 2017 rally in central Madrid."
            }
        ]

def test_reverse_image_recycling_detection():
    provider = WebReverseImageProvider(search_provider=MockRecyclingSearchProvider())
    result = provider.search(
        claim="Breaking news: massive protest breaks out today in 2026",
        image_url="https://example.com/protest.jpg"
    )
    
    assert result["is_recycled"] is True
    assert result["earliest_year"] == 2017
    assert "suggesting image recycling" in result["recycled_reason"]
    assert len(result["matched_sources"]) == 1

def test_image_agent_no_image():
    state = {"claim": "A text only claim"}
    result = image_agent(state)
    assert result["image_forensics"]["has_image"] is False
    assert result["image_forensics"]["is_tampered_or_ai"] is False

def test_image_agent_with_image():
    img_b64 = create_test_image_base64()
    state = {
        "claim": "Testing image claim",
        "image_base64": img_b64
    }
    result = image_agent(state)
    assert result["image_forensics"]["has_image"] is True
    assert "dimensions" in result["image_metadata"]

def test_reverse_image_agent_pass_through():
    state = {"claim": "A claim without image"}
    result = reverse_image_agent(state)
    assert result["visual_evidence"] == []

def test_reverse_image_agent_with_recycling():
    # Substitute mock reverse provider via container
    container.set_reverse_image_provider(WebReverseImageProvider(MockRecyclingSearchProvider()))
    
    state = {
        "claim": "Unprecedented riot today",
        "image_base64": create_test_image_base64(),
        "sources": []
    }
    result = reverse_image_agent(state)
    assert len(result["visual_evidence"]) > 0
    assert result["visual_evidence"][0]["label"] == "REFUTE"
    assert "archive.org" in result["sources"][0]["url"]

def test_evidence_agent_multimodal_synthesis():
    state = {
        "claim": "Test claim with tampered image",
        "retrieved_passages": [],
        "visual_evidence": [
            {
                "sentence": "Image was published in 2017.",
                "label": "REFUTE",
                "score": 0.88,
                "source": "reverse_image_provenance"
            }
        ],
        "image_forensics": {
            "has_image": True,
            "ai_generation_detected": True,
            "ai_markers": ["Stable Diffusion"],
            "tampering_indicators": ["Photoshop detected"],
            "is_tampered_or_ai": True
        }
    }
    result = evidence_agent(state)
    evidences = result["evidence"]
    assert len(evidences) == 3
    labels = [e["label"] for e in evidences]
    assert all(l == "REFUTE" for l in labels)

def test_judge_agent_forensic_fallback():
    # When LLM is bypassed/fails, judge agent falls back using forensic indicators
    state = {
        "claim": "Fake visual event",
        "evidence": [
            {"sentence": "Image is AI generated", "label": "REFUTE", "score": 0.95}
        ],
        "image_forensics": {
            "has_image": True,
            "is_tampered_or_ai": True,
            "summary": "AI Generation markers detected"
        }
    }
    # Invoke judge_agent (if API key not set or fails, it triggers the fallback)
    result = judge_agent(state)
    assert result["verdict"] in ["FALSE", "UNCLEAR"]
