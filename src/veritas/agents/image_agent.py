from typing import Dict, Any, List
import json
import re
from dotenv import load_dotenv
from veritas.core.llm import get_agent_llm
from langchain_core.messages import HumanMessage
from veritas.core.state import AgentState
from veritas.core.container import container

load_dotenv()

def image_agent(state: AgentState) -> Dict[str, Any]:
    """
    ImageAgent: Combines Gemini 2.5 Flash Multimodal Vision for semantic claim-image
    verification with local Error Level Analysis (ELA) and EXIF camera metadata inspection.
    """
    print("---ImageAgent---")
    claim = state.get("claim", "")
    image_base64 = state.get("image_base64")
    image_url = state.get("image_url")

    if not image_base64 and not image_url:
        print("No image provided. Skipping image forensic analysis.")
        return {
            "image_metadata": {},
            "image_forensics": {
                "has_image": False,
                "is_tampered_or_ai": False,
                "tampering_indicators": [],
                "summary": "No image provided for forensic analysis."
            },
            "visual_evidence": []
        }

    forensics_service = container.get_image_forensics_service()
    target_input = image_base64 if image_base64 else image_url

    try:
        print("Running forensic metadata and tampering analysis...")
        analysis = forensics_service.analyze(target_input)
        
        image_metadata = {
            "has_exif": analysis.get("has_exif", False),
            "format": analysis.get("format"),
            "dimensions": analysis.get("dimensions"),
            "exif": analysis.get("exif", {}),
            "gps": analysis.get("gps"),
            "hashes": analysis.get("hashes", {})
        }

        image_forensics = {
            "has_image": True,
            "ela_score": analysis.get("ela_score", 0.0),
            "ai_generation_detected": analysis.get("ai_generation_detected", False),
            "ai_markers": analysis.get("ai_markers", []),
            "tampering_indicators": analysis.get("tampering_indicators", []),
            "is_tampered_or_ai": analysis.get("is_tampered_or_ai", False),
            "summary": analysis.get("summary", "Analysis completed.")
        }

        visual_evidence: List[Dict[str, Any]] = []

        # Multimodal Gemini Vision Semantic Understanding
        if image_base64:
            try:
                print("Invoking Gemini 2.5 Flash Multimodal Vision for semantic image verification...")
                clean_b64 = image_base64
                if "base64," in clean_b64:
                    clean_b64 = clean_b64.split("base64,")[1]

                vision_prompt = f"""
                You are a senior multimodal forensic fact-checker.
                Evaluate this uploaded image against the user's claim:
                CLAIM: "{claim}"

                Analyze the image thoroughly and return a valid JSON object with the following fields:
                {{
                  "description": "Factual description of what is depicted (people, setting, objects, visible event)",
                  "alignment": "SUPPORTS" | "CONTRADICTS" | "MISATTRIBUTED" | "UNRELATED",
                  "confidence": 0.0 to 1.0,
                  "finding": "1-2 punchy sentences explaining whether the image corroborates or contradicts the claim",
                  "detected_text": "Any visible headline, watermark, jersey text, or banner text in the image",
                  "visual_anomalies": ["Any visual glitches, unnatural hands/limbs, or AI generation artifacts if present"]
                }}
                """

                vision_llm = get_agent_llm("image_agent", temperature=0)
                vision_message = HumanMessage(
                    content=[
                        {"type": "text", "text": vision_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{clean_b64}"}}
                    ]
                )
                
                vision_response = vision_llm.invoke([vision_message])
                response_text = vision_response.content.strip()
                
                # Extract JSON if enclosed in markdown code fences
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0].strip()
                
                vision_data = json.loads(response_text)
                image_forensics["visual_analysis"] = vision_data
                image_forensics["summary"] = f"{vision_data.get('finding')} (Visual Alignment: {vision_data.get('alignment')})"
                
                alignment = vision_data.get("alignment", "UNRELATED")
                label = "SUPPORT" if alignment == "SUPPORTS" else ("REFUTE" if alignment in ["CONTRADICTS", "MISATTRIBUTED"] else "INFO")
                
                visual_evidence.append({
                    "sentence": f"Visual Multimodal Analysis: {vision_data.get('finding')} Evidence details: {vision_data.get('description', '')}.",
                    "label": label,
                    "score": float(vision_data.get("confidence", 0.85)),
                    "source": "Gemini Multimodal Vision"
                })

                if vision_data.get("visual_anomalies"):
                    for anomaly in vision_data["visual_anomalies"]:
                        image_forensics["tampering_indicators"].append(f"Visual artifact: {anomaly}")
                        image_forensics["is_tampered_or_ai"] = True

            except Exception as vision_err:
                print(f"Warning: Multimodal vision extraction failed ({vision_err}). Falling back to local forensics.")

        if image_forensics["is_tampered_or_ai"]:
            print(f"[!] Tampering or AI marker detected: {image_forensics['summary']}")
        else:
            print("[OK] Image processed successfully.")

        return {
            "image_metadata": image_metadata,
            "image_forensics": image_forensics,
            "visual_evidence": visual_evidence
        }

    except Exception as e:
        print(f"Error in ImageAgent: {e}")
        return {
            "image_metadata": {},
            "image_forensics": {
                "has_image": True,
                "is_tampered_or_ai": False,
                "tampering_indicators": [f"Forensic error: {str(e)}"],
                "summary": f"Failed forensic inspection: {e}"
            },
            "visual_evidence": []
        }
