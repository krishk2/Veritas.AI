import os
import cv2
import base64
import tempfile
import numpy as np
import pytest
from veritas.services.video_service import OpenCVDeepfakeForensicsService
from veritas.agents.video_agent import video_agent
from veritas.agents.evidence_agent import evidence_agent
from veritas.agents.judge_agent import judge_agent
from veritas.core.container import container

def create_synthetic_video_bytes(num_frames=15, width=64, height=64, fps=10.0) -> bytes:
    """Helper to generate a lightweight in-memory synthetic MP4 video clip."""
    temp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    temp.close()
    temp_path = temp.name

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(temp_path, fourcc, fps, (width, height))

    for i in range(num_frames):
        # Create a simple colored frame with varying intensity
        color_val = int((i / num_frames) * 255)
        frame = np.full((height, width, 3), color_val, dtype=np.uint8)
        out.write(frame)

    out.release()

    with open(temp_path, "rb") as f:
        video_bytes = f.read()

    os.remove(temp_path)
    return video_bytes

def test_video_metadata_and_keyframe_extraction():
    service = OpenCVDeepfakeForensicsService()
    video_bytes = create_synthetic_video_bytes(num_frames=20, width=80, height=80, fps=10.0)
    
    metadata, keyframes = service.extract_keyframes(video_bytes, max_keyframes=4)
    
    assert metadata["width"] == 80
    assert metadata["height"] == 80
    assert metadata["total_frames"] == 20
    assert metadata["duration_seconds"] == 2.0
    assert len(keyframes) == 4
    for kf in keyframes:
        assert "base64" in kf
        assert "bytes" in kf
        assert "timestamp" in kf

def test_video_agent_no_video_pass_through():
    state = {"claim": "Text claim without any video"}
    result = video_agent(state)
    assert result["video_forensics"]["has_video"] is False
    assert result["video_forensics"]["is_deepfake_or_ai"] is False

def test_video_agent_with_video():
    video_bytes = create_synthetic_video_bytes(num_frames=10)
    b64_video = base64.b64encode(video_bytes).decode("utf-8")
    
    state = {
        "claim": "Testing video agent with real MP4 input",
        "video_base64": b64_video
    }
    result = video_agent(state)
    forensics = result["video_forensics"]
    assert forensics["has_video"] is True
    assert "metadata" in forensics
    assert forensics["metadata"]["width"] == 64

def test_evidence_agent_with_deepfake_findings():
    state = {
        "claim": "Official speech announcement",
        "retrieved_passages": [],
        "video_forensics": {
            "has_video": True,
            "is_deepfake_or_ai": True,
            "confidence": 0.94,
            "ai_video_markers": ["Sora synthetic motion geometry", "Runway Gen-3 watermark"],
            "deepfake_indicators": ["Face-swap mask boundary mismatch along jawline"],
            "summary": "AI Generated video detected"
        }
    }
    result = evidence_agent(state)
    evidences = result["evidence"]
    assert len(evidences) == 3
    for ev in evidences:
        assert ev["label"] == "REFUTE"
        assert ev["score"] == 0.94
        assert ev["source"] == "video_deepfake_forensics"

def test_judge_agent_deepfake_fallback():
    state = {
        "claim": "President announcing secret policy",
        "evidence": [
            {
                "sentence": "Synthetic AI video generator marker detected: Sora.",
                "label": "REFUTE",
                "score": 0.95,
                "source": "video_deepfake_forensics"
            }
        ],
        "video_forensics": {
            "has_video": True,
            "is_deepfake_or_ai": True,
            "confidence": 0.95,
            "ai_video_markers": ["Sora"],
            "summary": "Deepfake video generated with Sora"
        }
    }
    result = judge_agent(state)
    assert result["verdict"] in ["FALSE", "UNCLEAR"]
    assert result["confidence"] >= 0.85
