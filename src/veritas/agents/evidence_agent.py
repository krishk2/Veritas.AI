from typing import Dict, Any, List
import os
import json
from veritas.core.llm import get_agent_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from veritas.core.state import AgentState
from dotenv import load_dotenv

load_dotenv()

def evidence_agent(state: AgentState) -> Dict[str, Any]:
    """
    EvidenceAgent: Extracts supporting and refuting sentences from textual passages
    and synthesizes multimodal visual forensics & provenance evidence.
    """
    print("---EvidenceAgent---")
    claim = state["claim"]
    passages = state.get("retrieved_passages", [])
    visual_evidence = state.get("visual_evidence", []) or []
    image_forensics = state.get("image_forensics", {}) or {}

    combined_evidence: List[Dict[str, Any]] = list(visual_evidence)

    # 1. Integrate Image Forensics into evidence records
    if image_forensics.get("ai_generation_detected"):
        markers = ", ".join(image_forensics.get("ai_markers", []))
        combined_evidence.append({
            "sentence": f"Forensic analysis detected synthetic AI image generation markers: {markers}.",
            "label": "REFUTE",
            "score": 0.95,
            "source": "image_forensics"
        })

    for indicator in image_forensics.get("tampering_indicators", []):
        combined_evidence.append({
            "sentence": f"Forensic manipulation indicator: {indicator}",
            "label": "REFUTE",
            "score": 0.85,
            "source": "image_forensics"
        })

    # If image has verified EXIF camera data without tampering
    if image_forensics.get("has_image") and not image_forensics.get("is_tampered_or_ai"):
        metadata = state.get("image_metadata", {})
        exif = metadata.get("exif", {}) if metadata else {}
        if exif.get("Make") or exif.get("Model"):
            combined_evidence.append({
                "sentence": f"Image contains authentic camera capture EXIF data ({exif.get('Make', '')} {exif.get('Model', '')}).",
                "label": "SUPPORT",
                "score": 0.70,
                "source": "image_metadata"
            })

    # 2. Integrate Video Deepfake & AI Forensics into evidence records
    video_forensics = state.get("video_forensics", {}) or {}
    if video_forensics.get("is_deepfake_or_ai"):
        v_conf = video_forensics.get("confidence", 0.90)
        for marker in video_forensics.get("ai_video_markers", []):
            combined_evidence.append({
                "sentence": f"Synthetic AI video generator marker detected: {marker}.",
                "label": "REFUTE",
                "score": v_conf,
                "source": "video_deepfake_forensics"
            })
        for ind in video_forensics.get("deepfake_indicators", []):
            combined_evidence.append({
                "sentence": f"Deepfake visual manipulation detected: {ind}.",
                "label": "REFUTE",
                "score": v_conf,
                "source": "video_deepfake_forensics"
            })

    # 3. Extract textual evidence from passages
    if passages:
        print(f"Analyzing {len(passages)} passages for evidence...")
        try:
            llm = get_agent_llm("evidence_agent", temperature=0)
            
            prompt_text = """
            You are an expert fact-checker. 
            Given the following claim and a list of retrieved passages, extract sentences that either SUPPORT or REFUTE the claim.
            For each sentence, assign a label (SUPPORT/REFUTE) and a confidence score (0.0-1.0).
            
            Claim: {claim}
            
            Passages:
            {passages}
            
            Return the output as a JSON object with a key "evidence" containing a list of objects.
            Each object should have: "sentence", "label", "score".
            """
            
            prompt = ChatPromptTemplate.from_template(prompt_text)
            chain = prompt | llm | JsonOutputParser()
            
            context = "\n\n".join(passages)
            result = chain.invoke({"claim": claim, "passages": context})
            
            extracted = result.get("evidence", [])
            for item in extracted:
                item["source"] = item.get("source", "web_passages")
                combined_evidence.append(item)
            print(f"Extracted {len(extracted)} textual evidence sentences.")
            
        except Exception as e:
            print(f"Warning in EvidenceAgent text extraction: {e}")
    else:
        print("No text passages to analyze.")

    print(f"Total evidence items synthesized: {len(combined_evidence)}")
    return {"evidence": combined_evidence}
