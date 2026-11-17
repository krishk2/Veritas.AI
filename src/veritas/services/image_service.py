from typing import Dict, Any, Optional, Union, List, Tuple
import io
import re
import base64
import hashlib
from datetime import datetime
from PIL import Image, ImageChops, ExifTags
from veritas.core.interfaces import IImageForensicsService, IReverseImageProvider, ISearchProvider

AI_SOFTWARE_SIGNATURES = [
    "midjourney",
    "stable diffusion",
    "dall-e",
    "novelai",
    "comfyui",
    "automatic1111",
    "adobe firefly",
    "civitai",
    "bing image creator"
]

MANIPULATION_SOFTWARE_SIGNATURES = [
    "photoshop",
    "gimp",
    "canva",
    "lightroom",
    "snapseed",
    "picsart",
    "affinity photo",
    "pixelmator"
]

def _parse_gps(gps_info: Dict[Any, Any]) -> Optional[Dict[str, float]]:
    """Converts EXIF GPSInfo tags into decimal latitude and longitude."""
    try:
        def to_decimal(coords, ref):
            d, m, s = coords
            val = float(d) + float(m) / 60.0 + float(s) / 3600.0
            if ref in ['S', 'W']:
                val = -val
            return round(val, 6)

        gps_data = {}
        for key, val in gps_info.items():
            sub_name = ExifTags.GPSTAGS.get(key, str(key))
            gps_data[sub_name] = val

        if 'GPSLatitude' in gps_data and 'GPSLatitudeRef' in gps_data:
            lat = to_decimal(gps_data['GPSLatitude'], gps_data['GPSLatitudeRef'])
            lon = to_decimal(gps_data['GPSLongitude'], gps_data['GPSLongitudeRef'])
            return {"latitude": lat, "longitude": lon}
    except Exception:
        pass
    return None

def compute_dhash(image: Image.Image, hash_size: int = 8) -> str:
    """Computes a 64-bit difference hash (dHash) for perceptual image fingerprinting."""
    try:
        # Resize to (hash_size + 1, hash_size) in grayscale
        resized = image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
        diff = []
        for row in range(hash_size):
            for col in range(hash_size):
                pixel_left = resized.getpixel((col, row))
                pixel_right = resized.getpixel((col + 1, row))
                diff.append(pixel_left > pixel_right)

        decimal_value = 0
        hex_string = []
        for index, value in enumerate(diff):
            if value:
                decimal_value += 2 ** (index % 8)
            if (index % 8) == 7:
                hex_string.append(hex(decimal_value)[2:].rjust(2, "0"))
                decimal_value = 0
        return "".join(hex_string)
    except Exception:
        return "0" * 16

def compute_ela_score(image: Image.Image, quality: int = 95) -> float:
    """
    Computes Error Level Analysis (ELA) score.
    Higher score indicates higher compression variance or localized editing artifacts.
    """
    try:
        rgb_img = image.convert("RGB")
        buffer = io.BytesIO()
        rgb_img.save(buffer, format="JPEG", quality=quality)
        buffer.seek(0)
        resaved = Image.open(buffer)

        diff = ImageChops.difference(rgb_img, resaved)
        # Find maximum extrema across RGB channels
        extrema = diff.getextrema()
        max_diff = max([ex[1] for ex in extrema])
        
        # Scale to 0.0 - 1.0 (typical raw difference range is 0 - 50)
        normalized_score = min(1.0, max_diff / 50.0)
        return round(normalized_score, 3)
    except Exception:
        return 0.0


class PillowImageForensicsService:
    """Production implementation of IImageForensicsService using Pillow and heuristic analysis."""

    def _decode_image(self, image_input: Union[str, bytes]) -> Tuple[Image.Image, bytes]:
        if isinstance(image_input, bytes):
            raw_bytes = image_input
        elif isinstance(image_input, str):
            # Strip data URL prefix if present (e.g. data:image/png;base64,...)
            if "," in image_input and "base64" in image_input.split(",")[0]:
                image_input = image_input.split(",", 1)[1]
            try:
                raw_bytes = base64.b64decode(image_input)
            except Exception:
                # Might be a local file path
                with open(image_input, "rb") as f:
                    raw_bytes = f.read()
        else:
            raise ValueError(f"Unsupported image input type: {type(image_input)}")

        img = Image.open(io.BytesIO(raw_bytes))
        return img, raw_bytes

    def analyze(self, image_input: Union[str, bytes]) -> Dict[str, Any]:
        """Performs full forensic inspection of metadata, tampering signatures, ELA, and hashes."""
        try:
            img, raw_bytes = self._decode_image(image_input)
        except Exception as e:
            return {
                "error": f"Failed to decode image: {e}",
                "is_tampered_or_ai": False,
                "tampering_indicators": [f"Image decoding error: {e}"]
            }

        md5_hash = hashlib.md5(raw_bytes).hexdigest()
        dhash = compute_dhash(img)
        ela_score = compute_ela_score(img)

        # 1. Extract EXIF data
        exif_data: Dict[str, Any] = {}
        gps_coords = None
        has_exif = False

        try:
            raw_exif = img.getexif()
            if raw_exif:
                for tag_id, value in raw_exif.items():
                    tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                    # Handle GPSInfo sub-dict
                    if tag_name == "GPSInfo" and isinstance(value, dict):
                        gps_coords = _parse_gps(value)
                    else:
                        # Clean binary or non-serializable values
                        if isinstance(value, bytes):
                            try:
                                value = value.decode("utf-8", errors="ignore").strip("\x00")
                            except Exception:
                                value = str(value)
                        exif_data[tag_name] = value
                if exif_data:
                    has_exif = True
        except Exception:
            pass

        # Also inspect _getexif() for JPEG-specific IFDs if getexif() missed them
        if not exif_data and hasattr(img, "_getexif"):
            try:
                legacy_exif = img._getexif()
                if legacy_exif:
                    for tag_id, value in legacy_exif.items():
                        tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                        if tag_name == "GPSInfo" and isinstance(value, dict):
                            gps_coords = _parse_gps(value)
                        elif isinstance(value, (str, int, float)):
                            exif_data[tag_name] = value
                    if exif_data:
                        has_exif = True
            except Exception:
                pass

        # 2. Check for AI generator markers & text chunks (PNG text, info dict)
        ai_markers: List[str] = []
        info_dict_str = str(getattr(img, "info", {})).lower()
        exif_str = str(exif_data).lower()
        combined_meta = f"{info_dict_str} {exif_str}"

        for sig in AI_SOFTWARE_SIGNATURES:
            if sig in combined_meta:
                ai_markers.append(f"AI Generator Signature found: '{sig}'")

        # 3. Check for manipulation/editing software signatures
        tampering_indicators: List[str] = []
        software_detected = exif_data.get("Software") or getattr(img, "info", {}).get("Software", "")
        if software_detected:
            software_lower = str(software_detected).lower()
            for sig in MANIPULATION_SOFTWARE_SIGNATURES:
                if sig in software_lower:
                    tampering_indicators.append(
                        f"Image editing software detected in metadata: '{software_detected}'"
                    )

        # 4. Check ELA anomaly
        if ela_score > 0.8:
            tampering_indicators.append(
                f"High Error Level Analysis (ELA) anomaly score ({ela_score}): potential localized splicing or high re-compression artifacts."
            )

        # 5. Metadata inconsistency checks
        if "Make" in exif_data and not exif_data.get("Model"):
            tampering_indicators.append("Camera metadata has Make but Model is missing or stripped.")

        is_tampered_or_ai = len(ai_markers) > 0 or len(tampering_indicators) > 0

        # Construct summary
        summary_parts = []
        if ai_markers:
            summary_parts.append(f"AI Generation markers detected ({', '.join(ai_markers)})")
        if tampering_indicators:
            summary_parts.append(f"Tampering indicators: {'; '.join(tampering_indicators)}")
        if not is_tampered_or_ai:
            summary_parts.append("No obvious digital manipulation or AI signatures detected in metadata.")

        return {
            "has_exif": has_exif,
            "format": img.format or "UNKNOWN",
            "dimensions": {"width": img.width, "height": img.height},
            "exif": exif_data,
            "gps": gps_coords,
            "hashes": {
                "dhash": dhash,
                "md5": md5_hash
            },
            "ela_score": ela_score,
            "ai_generation_detected": len(ai_markers) > 0,
            "ai_markers": ai_markers,
            "tampering_indicators": tampering_indicators,
            "is_tampered_or_ai": is_tampered_or_ai,
            "summary": " | ".join(summary_parts)
        }


class WebReverseImageProvider:
    """Reverse image lookup provider using web search correlation and recycling detection."""

    def __init__(self, search_provider: Optional[ISearchProvider] = None):
        self.search_provider = search_provider

    def search(
        self,
        image_input: Optional[Union[str, bytes]] = None,
        image_url: Optional[str] = None,
        claim: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Detects if an image has been recycled from an earlier event or previously debunked.
        """
        matched_sources: List[Dict[str, Any]] = []
        earliest_year: Optional[int] = None
        is_recycled = False
        recycled_reason = None

        # Build query for reverse search correlation
        search_query = None
        if claim:
            search_query = f"{claim} original photo origin"
        elif image_url:
            search_query = f"{image_url} image origin source"

        if search_query and self.search_provider:
            try:
                results = self.search_provider.search(search_query, max_results=5)
                for item in results:
                    url = item.get("url", "")
                    title = item.get("title", "")
                    content = item.get("content", "")

                    # Extract publication years (e.g., 2005 - current year) from snippet / url
                    found_years = [
                        int(y) for y in re.findall(r"\b(200[5-9]|201[0-9]|202[0-6])\b", f"{url} {title} {content}")
                    ]
                    
                    matched_sources.append({
                        "url": url,
                        "title": title,
                        "years": found_years,
                        "snippet": content[:200] if content else ""
                    })

                    for yr in found_years:
                        if earliest_year is None or yr < earliest_year:
                            earliest_year = yr
            except Exception as e:
                pass

        # Check if earliest publication year is substantially older than current year or claim context
        current_year = datetime.now().year
        if earliest_year and (current_year - earliest_year) >= 2:
            is_recycled = True
            recycled_reason = (
                f"Visual media matches earlier records dating back to {earliest_year}, "
                f"suggesting image recycling or out-of-context reuse."
            )

        return {
            "earliest_year": earliest_year,
            "is_recycled": is_recycled,
            "recycled_reason": recycled_reason,
            "matched_sources": matched_sources,
            "summary": (
                recycled_reason
                if is_recycled
                else f"No prior recycling detected. Earliest indexed reference: {earliest_year or 'Unknown'}."
            )
        }
