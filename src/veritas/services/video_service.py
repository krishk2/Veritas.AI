import os
import io
import re
import cv2
import json
import base64
import tempfile
import logging
from typing import Dict, Any, Optional, Union, List, Tuple
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("veritas.video_service")

KNOWN_AI_VIDEO_GENERATORS = [
    "sora",
    "runway",
    "gen-2",
    "gen-3",
    "kling",
    "luma",
    "dream machine",
    "pika",
    "deforum",
    "stable video",
    "animatediff",
    "kaiber",
    "synthesia",
    "deepfake",
    "roop",
    "faceswap"
]

class OpenCVDeepfakeForensicsService:
    """Production implementation of IVideoForensicsService using OpenCV and Gemini Multimodal."""

    def __init__(self, image_forensics_service=None):
        self._image_forensics_service = image_forensics_service

    def _get_image_forensics_service(self):
        if self._image_forensics_service is None:
            from veritas.core.container import container
            self._image_forensics_service = container.get_image_forensics_service()
        return self._image_forensics_service

    def _prepare_video_file(self, video_input: Union[str, bytes]) -> Tuple[str, bool]:
        """Resolves video input to a local filesystem path, creating a temp file if needed."""
        if isinstance(video_input, bytes):
            temp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
            temp.write(video_input)
            temp.close()
            return temp.name, True

        if isinstance(video_input, str):
            # Check if base64 encoded
            if "," in video_input and "base64" in video_input.split(",")[0]:
                video_input = video_input.split(",", 1)[1]
            try:
                decoded = base64.b64decode(video_input)
                temp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
                temp.write(decoded)
                temp.close()
                return temp.name, True
            except Exception:
                # Local file path
                if os.path.exists(video_input):
                    return video_input, False
                raise ValueError(f"Video file not found: {video_input}")

        raise ValueError(f"Unsupported video input type: {type(video_input)}")

    def extract_keyframes(
        self,
        video_input: Union[str, bytes],
        max_keyframes: int = 5
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Samples evenly distributed keyframes across the video clip."""
        video_path, is_temp = self._prepare_video_file(video_input)
        temp_to_clean = video_path if is_temp else None

        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Could not open video file: {video_path}")

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = round(total_frames / fps, 2) if fps > 0 else 0.0

            metadata = {
                "width": width,
                "height": height,
                "fps": round(fps, 2),
                "total_frames": total_frames,
                "duration_seconds": duration
            }

            if total_frames <= 0:
                cap.release()
                return metadata, []

            # Determine frame indices for sampling
            sample_count = min(max_keyframes, max(1, total_frames))
            if sample_count == 1:
                indices = [0]
            else:
                step = total_frames / (sample_count + 1)
                indices = [int(step * (i + 1)) for i in range(sample_count)]

            keyframes = []
            for idx in indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if not ret or frame is None:
                    continue

                # Encode frame to JPEG
                success, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
                if success:
                    raw_bytes = buffer.tobytes()
                    b64_str = base64.b64encode(raw_bytes).decode("utf-8")
                    timestamp = round(idx / fps, 2) if fps > 0 else 0.0
                    keyframes.append({
                        "frame_index": idx,
                        "timestamp": timestamp,
                        "bytes": raw_bytes,
                        "base64": b64_str
                    })

            cap.release()
            return metadata, keyframes
        finally:
            if temp_to_clean and os.path.exists(temp_to_clean):
                try:
                    os.remove(temp_to_clean)
                except Exception:
                    pass

    def analyze(
        self,
        video_input: Union[str, bytes],
        claim_context: Optional[str] = None,
        max_keyframes: int = 5
    ) -> Dict[str, Any]:
        """
        Conducts deepfake and generative AI video forensic analysis:
        1. Container metadata & temporal keyframe sampling
        2. Per-keyframe forensic analysis (ELA compression, image tampering)
        3. Multimodal LLM AI artifact & deepfake face-swap audit
        """
        try:
            metadata, keyframes = self.extract_keyframes(video_input, max_keyframes=max_keyframes)
            
            if not keyframes:
                return {
                    "is_deepfake_or_ai": False,
                    "confidence": 0.0,
                    "ai_video_markers": [],
                    "deepfake_indicators": ["No valid frames could be decoded from video."],
                    "metadata": metadata,
                    "summary": "Video decoding failed: no frames extracted."
                }

            # 1. Per-frame forensic inspection using image forensics service
            image_service = self._get_image_forensics_service()
            frame_reports = []
            max_ela = 0.0
            tamper_alerts = []

            for kf in keyframes:
                f_analysis = image_service.analyze(kf["bytes"])
                ela = f_analysis.get("ela_score", 0.0)
                if ela > max_ela:
                    max_ela = ela
                if f_analysis.get("is_tampered_or_ai"):
                    tamper_alerts.extend(f_analysis.get("tampering_indicators", []))
                frame_reports.append({
                    "timestamp": kf["timestamp"],
                    "ela_score": ela,
                    "is_tampered_or_ai": f_analysis.get("is_tampered_or_ai", False)
                })

            # 2. Multimodal Deepfake & AI Detection via Gemini
            llm_result = self._inspect_keyframes_with_gemini(keyframes, claim_context)

            is_ai = llm_result.get("is_deepfake_or_ai", False)
            ai_markers = llm_result.get("ai_video_markers", [])
            deepfake_indicators = llm_result.get("deepfake_indicators", [])
            confidence = llm_result.get("confidence", 0.0)

            # Heuristic check if ELA is anomalously high or frame tamper alerts found
            if max_ela > 0.85:
                deepfake_indicators.append(f"High compression/splicing anomaly detected across frames (ELA: {max_ela}).")
                if confidence < 0.7:
                    confidence = 0.75
                    is_ai = True

            for alert in tamper_alerts:
                if alert not in deepfake_indicators:
                    deepfake_indicators.append(alert)

            # Build summary
            summary = llm_result.get("summary")
            if not summary:
                if is_ai:
                    summary = f"Synthetic/Deepfake video detected. Markers: {', '.join(ai_markers + deepfake_indicators)}."
                else:
                    summary = "No obvious deepfake or generative AI artifacts detected across keyframes."

            return {
                "is_deepfake_or_ai": is_ai,
                "confidence": round(confidence, 2),
                "ai_video_markers": ai_markers,
                "deepfake_indicators": deepfake_indicators,
                "max_frame_ela": max_ela,
                "metadata": metadata,
                "frames_analyzed": len(keyframes),
                "summary": summary
            }

        except Exception as e:
            logger.error(f"Error in video forensics analysis: {e}")
            return {
                "is_deepfake_or_ai": False,
                "confidence": 0.0,
                "ai_video_markers": [],
                "deepfake_indicators": [f"Forensic error: {str(e)}"],
                "summary": f"Video analysis failed: {e}"
            }

    def _inspect_keyframes_with_gemini(
        self,
        keyframes: List[Dict[str, Any]],
        claim_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calls Gemini Vision to inspect keyframes for deepfake facial anomalies and synthetic video markers."""
        try:
            from veritas.core.llm import get_agent_llm
            from langchain_core.messages import HumanMessage

            llm = get_agent_llm("video_agent", temperature=0)

            prompt_text = f"""
            You are a leading digital forensics expert specializing in AI-GENERATED VIDEO and DEEPFAKE detection.
            Examine the provided sampled keyframes from a video clip.
            
            Claim Context: {claim_context or "Not provided"}
            
            Inspect specifically for:
            1. Generative AI Video Artifacts: Sora, Runway, Kling, Luma Dream Machine, Pika hallmarks (rubber-like anatomy, morphing objects, melting textures, impossible physics, text gibberish, AI generator watermarks).
            2. Deepfake / Face-Swap Anomalies: Blurred boundary seams along jawline/hairline, mismatched facial resolution vs background, uncanny teeth/eyes, unnatural skin smoothing, lack of natural micro-saccades.
            
            Return ONLY a valid JSON object in this format:
            {{
                "is_deepfake_or_ai": true or false,
                "confidence": 0.0 to 1.0,
                "ai_video_markers": ["list of specific generative AI markers found, or empty"],
                "deepfake_indicators": ["list of face-swap or synthetic manipulation artifacts found, or empty"],
                "summary": "Brief 1-2 sentence conclusion"
            }}
            """

            # Attach up to 3 representative keyframes as base64 images
            content_parts: List[Dict[str, Any]] = [{"type": "text", "text": prompt_text}]
            for kf in keyframes[:3]:
                content_parts.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{kf['base64']}"
                    }
                })

            message = HumanMessage(content=content_parts)
            response = llm.invoke([message])
            raw_text = response.content.strip()

            # Clean markdown code block formatting
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0].strip()

            parsed = json.loads(raw_text)
            return {
                "is_deepfake_or_ai": bool(parsed.get("is_deepfake_or_ai", False)),
                "confidence": float(parsed.get("confidence", 0.0)),
                "ai_video_markers": parsed.get("ai_video_markers", []),
                "deepfake_indicators": parsed.get("deepfake_indicators", []),
                "summary": parsed.get("summary", "")
            }

        except Exception as e:
            logger.warning(f"Gemini keyframe inspection bypassed/failed: {e}")
            return {
                "is_deepfake_or_ai": False,
                "confidence": 0.0,
                "ai_video_markers": [],
                "deepfake_indicators": [],
                "summary": "LLM visual inspection skipped (offline or unconfigured)."
            }
