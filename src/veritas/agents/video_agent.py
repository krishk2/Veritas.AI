from typing import Dict, Any
from veritas.core.state import AgentState
from veritas.core.container import container

def video_agent(state: AgentState) -> Dict[str, Any]:
    """
    VideoAgent: Detects deepfakes, synthetic AI-generated video (Sora, Runway, Kling),
    face-swapping artifacts, and container metadata anomalies across keyframes.
    """
    print("---VideoAgent---")
    video_base64 = state.get("video_base64")
    video_url = state.get("video_url")
    claim = state.get("claim", "")

    if not video_base64 and not video_url:
        print("No video provided. Skipping video deepfake analysis.")
        return {
            "video_forensics": {
                "has_video": False,
                "is_deepfake_or_ai": False,
                "ai_video_markers": [],
                "deepfake_indicators": [],
                "summary": "No video provided for analysis."
            }
        }

    video_service = container.get_video_forensics_service()
    target_input = video_base64 if video_base64 else video_url

    try:
        print(f"Running deepfake & AI video forensic examination on video input...")
        analysis = video_service.analyze(
            video_input=target_input,
            claim_context=claim,
            max_keyframes=5
        )

        analysis["has_video"] = True

        if analysis.get("is_deepfake_or_ai"):
            print(f"[!] Deepfake/AI Video Alert: {analysis.get('summary')}")
        else:
            print("[OK] Video keyframes passed initial deepfake & AI generation inspection.")

        return {
            "video_forensics": analysis
        }

    except Exception as e:
        print(f"Error in VideoAgent: {e}")
        return {
            "video_forensics": {
                "has_video": True,
                "is_deepfake_or_ai": False,
                "ai_video_markers": [],
                "deepfake_indicators": [f"Video analysis error: {str(e)}"],
                "summary": f"Video analysis failed: {e}"
            }
        }
