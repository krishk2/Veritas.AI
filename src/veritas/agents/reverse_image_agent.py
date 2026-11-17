from typing import Dict, Any, List
from veritas.core.state import AgentState
from veritas.core.container import container

def reverse_image_agent(state: AgentState) -> Dict[str, Any]:
    """
    ReverseImageAgent: Detects image recycling, out-of-context reuse, and earliest appearance across the web.
    """
    print("---ReverseImageAgent---")
    image_base64 = state.get("image_base64")
    image_url = state.get("image_url")
    claim = state.get("claim", "")
    existing_sources = state.get("sources", [])

    if not image_base64 and not image_url:
        print("No image provided. Skipping reverse image lookup.")
        return {
            "visual_evidence": [],
            "sources": existing_sources
        }

    reverse_provider = container.get_reverse_image_provider()
    target_input = image_base64 if image_base64 else image_url

    try:
        print(f"Searching web origins for visual media against claim: '{claim}'...")
        lookup = reverse_provider.search(
            image_input=target_input,
            image_url=image_url,
            claim=claim
        )

        visual_evidence: List[Dict[str, Any]] = []
        is_recycled = lookup.get("is_recycled", False)
        recycled_reason = lookup.get("recycled_reason")
        earliest_year = lookup.get("earliest_year")

        if is_recycled and recycled_reason:
            visual_evidence.append({
                "sentence": recycled_reason,
                "label": "REFUTE",
                "score": 0.88,
                "source": "reverse_image_provenance",
                "details": f"Earliest detected appearance: {earliest_year}"
            })
            print(f"[!] Reverse image alert: {recycled_reason}")
        elif earliest_year:
            visual_evidence.append({
                "sentence": f"Visual media verified on the web with earliest indexed appearance: {earliest_year}.",
                "label": "SUPPORT",
                "score": 0.65,
                "source": "reverse_image_provenance"
            })

        # Append any new web sources discovered during reverse search
        new_sources = list(existing_sources)
        existing_urls = {s.get("url") for s in existing_sources if "url" in s}

        for match in lookup.get("matched_sources", []):
            url = match.get("url")
            if url and url not in existing_urls:
                new_sources.append({
                    "title": match.get("title", "Reverse Image Match"),
                    "url": url,
                    "content": match.get("snippet", "")
                })
                existing_urls.add(url)

        return {
            "visual_evidence": visual_evidence,
            "sources": new_sources
        }

    except Exception as e:
        print(f"Error in ReverseImageAgent: {e}")
        return {
            "visual_evidence": [],
            "sources": existing_sources
        }
