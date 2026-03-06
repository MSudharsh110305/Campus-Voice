"""
Image verification service using Groq Vision API.

✅ UPDATED: Uses data URIs from database (binary storage)
✅ UPDATED: Returns ImageVerificationResult schema format
✅ UPDATED: No file path dependencies
"""

import logging
import base64
import asyncio
from typing import Dict, Any, Optional, Tuple
from uuid import UUID
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from groq import Groq
from src.config.settings import settings

logger = logging.getLogger(__name__)


class ImageVerificationService:
    """Service for image verification using Groq Vision API"""

    def __init__(self):
        """Initialize with Groq client.

        Gracefully handles missing GROQ_API_KEY by setting client to None.
        Verification falls back to keyword matching when the client is
        unavailable.
        """
        self.groq_client = None
        # Use latest Llama 4 Scout vision model (2026)
        self.vision_model = "meta-llama/llama-4-scout-17b-16e-instruct"
        self.temperature = 0.2  # Lower for consistent results
        self.max_tokens = 1000

        api_key = settings.GROQ_API_KEY
        if api_key and api_key.strip():
            try:
                self.groq_client = Groq(api_key=api_key)
                logger.info("Image verification service initialized with Groq Vision API")
            except Exception as e:
                logger.warning(f"Failed to initialize Groq client for image verification: {e}")
        else:
            logger.warning("GROQ_API_KEY not set. Image verification will use fallback logic.")
    
    async def verify_image_from_bytes(
        self,
        db: AsyncSession,
        complaint_id: UUID,
        complaint_text: str,
        image_bytes: bytes,
        mimetype: str,
        image_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify if image is relevant to complaint using Groq Vision API.
        
        ✅ NEW: Accepts image_bytes instead of image_url
        
        Args:
            db: Database session
            complaint_id: Complaint UUID
            complaint_text: Complaint text
            image_bytes: Image bytes from database
            mimetype: Image MIME type (e.g., "image/jpeg")
            image_description: Optional image description
        
        Returns:
            Verification result matching ImageVerificationResult schema:
            {
                "is_relevant": bool,
                "confidence_score": float (0.0-1.0),
                "explanation": str,
                "status": str ("Verified" | "Rejected" | "Pending")
            }
        """
        try:
            # Convert bytes to data URI
            data_uri = self.encode_bytes_to_data_uri(image_bytes, mimetype)
            
            # Use LLM Vision to verify relevance
            result = await self.verify_image_relevance(
                complaint_text=complaint_text,
                image_data_uri=data_uri,
                image_description=image_description
            )
            
            # Log verification to database
            from src.database.models import ImageVerificationLog
            log = ImageVerificationLog(
                complaint_id=complaint_id,
                is_relevant=result["is_relevant"],
                confidence_score=result["confidence_score"],
                rejection_reason=result["explanation"] if not result["is_relevant"] else None
            )
            db.add(log)
            await db.commit()
            
            logger.info(
                f"Image verification for {complaint_id}: "
                f"Relevant={result['is_relevant']}, Confidence={result['confidence_score']}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Image verification error for {complaint_id}: {e}")
            # Fallback to accepting image if API fails
            return {
                "is_relevant": True,
                "confidence_score": 0.5,
                "explanation": f"Verification error, accepted by default: {str(e)}",
                "status": "Pending"
            }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((httpx.HTTPError, TimeoutError))
    )
    async def verify_image_relevance(
        self,
        complaint_text: str,
        image_data_uri: str,
        image_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify if image is relevant to complaint using Groq Vision API.
        
        ✅ UPDATED: Accepts data_uri directly (from database)
        
        Args:
            complaint_text: Complaint text
            image_data_uri: Base64 data URI (data:image/jpeg;base64,...)
            image_description: Optional image description
        
        Returns:
            Dictionary matching ImageVerificationResult schema:
            {
                "is_relevant": bool,
                "confidence_score": float (0.0-1.0),
                "explanation": str,
                "status": str
            }
        """
        try:
            # Validate data URI
            if not image_data_uri.startswith("data:"):
                logger.error(f"Invalid data URI format: {image_data_uri[:50]}...")
                return self._fallback_verification(complaint_text, image_description)

            # If Groq client is not available, use fallback
            if not self.groq_client:
                logger.info("Groq client unavailable, using fallback image verification")
                return self._fallback_verification(complaint_text, image_description)

            # Build verification prompt
            prompt = self._build_verification_prompt(complaint_text, image_description)

            # Call Groq Vision API
            response = await asyncio.to_thread(
                self.groq_client.chat.completions.create,
                model=self.vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_data_uri
                                }
                            }
                        ]
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # Parse response
            content = response.choices[0].message.content

            # Extract JSON from response — strip markdown code fences if present
            import json, re
            try:
                clean = content.strip()
                fence_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', clean)
                if fence_match:
                    clean = fence_match.group(1).strip()
                raw_result = json.loads(clean)
                result = self._transform_to_schema_format(raw_result, complaint_text)
            except json.JSONDecodeError:
                # If not JSON, parse manually
                result = self._parse_vision_response(content, complaint_text)
            
            logger.info(
                f"Vision API verification: Relevant={result['is_relevant']}, "
                f"Confidence={result['confidence_score']}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Groq Vision API error: {e}")
            return self._fallback_verification(complaint_text, image_description)
    
    def _build_verification_prompt(
        self,
        complaint_text: str,
        image_description: Optional[str]
    ) -> str:
        """Build prompt for image verification"""
        
        base_prompt = f"""You are an image verification system for a campus complaint management system.

**Complaint Text:**
"{complaint_text}"

{"**Image Description:** " + image_description if image_description else ""}

**Task:** Determine if this image is relevant supporting evidence for this complaint.

**ACCEPT the image if:**
- It directly shows the subject being complained about (e.g., food/canteen area for a food complaint, a room/hostel for a hostel complaint, a broken item for a maintenance complaint)
- It shows the specific location or issue mentioned in the complaint text
- It clearly depicts the problem or evidence of the problem described

**REJECT the image if ANY of these apply:**
- The image subject does not match the complaint topic (e.g., a ceiling fan for a food/canteen complaint, a classroom for a hostel complaint, a vehicle for a facilities complaint)
- It is a meme, joke image, or internet screenshot unrelated to the issue
- It contains offensive, inappropriate, or abusive content
- It is clearly a test/dummy/random image with no connection to the complaint
- The image shows something from a completely different category than what is described (infrastructure/equipment unrelated to the complaint)

**CRITICAL: Be strict. The image must be relevant to the specific subject of the complaint. A photo of something that exists on campus but is unrelated to the complaint topic should be REJECTED.**

Respond ONLY with valid JSON:

{{
  "is_relevant": true/false,
  "confidence": 0.0-1.0,
  "reason": "Brief explanation (max 100 words)",
  "detected_objects": ["list", "of", "visible", "objects"],
  "visible_issues": ["list", "of", "problems", "or", "none"],
  "quality_rating": "Good|Fair|Poor",
  "is_appropriate": true/false
}}

Analyze the provided image and respond with JSON:"""
        
        return base_prompt
    
    def _transform_to_schema_format(
        self,
        raw_result: Dict[str, Any],
        complaint_text: str
    ) -> Dict[str, Any]:
        """
        ✅ NEW: Transform raw API response to ImageVerificationResult schema format
        
        Args:
            raw_result: Raw response from Vision API
            complaint_text: Original complaint text
        
        Returns:
            Dictionary matching ImageVerificationResult schema
        """
        is_relevant = raw_result.get("is_relevant", False)
        confidence = raw_result.get("confidence", 0.5)
        reason = raw_result.get("reason", "No reason provided")
        is_appropriate = raw_result.get("is_appropriate", is_relevant)
        
        # Combine reason with additional details
        detected_objects = raw_result.get("detected_objects", [])
        visible_issues = raw_result.get("visible_issues", [])
        quality_rating = raw_result.get("quality_rating", "Unknown")
        
        explanation_parts = [reason]
        if detected_objects:
            explanation_parts.append(f"Detected: {', '.join(detected_objects[:5])}")
        if visible_issues:
            explanation_parts.append(f"Issues: {', '.join(visible_issues[:3])}")
        explanation_parts.append(f"Quality: {quality_rating}")
        
        explanation = ". ".join(explanation_parts)
        
        # Determine status
        if is_relevant and is_appropriate:
            status = "Verified"
        elif not is_relevant or not is_appropriate:
            status = "Rejected"
        else:
            status = "Pending"
        
        return {
            "is_relevant": is_relevant and is_appropriate,
            "confidence_score": float(confidence),
            "explanation": explanation[:500],  # Limit length
            "status": status
        }
    
    def _parse_vision_response(self, content: str, complaint_text: str) -> Dict[str, Any]:
        """
        Parse vision API response if not JSON
        
        ✅ UPDATED: Returns ImageVerificationResult schema format
        """
        
        content_lower = content.lower()
        
        # Determine relevance based on keywords
        relevant_indicators = [
            "relevant", "related", "shows", "visible", "matches",
            "appropriate", "genuine", "evidence", "depicts"
        ]
        
        irrelevant_indicators = [
            "not relevant", "irrelevant", "unrelated", "spam", "meme",
            "inappropriate", "not related", "doesn't match", "fake"
        ]
        
        # Calculate relevance
        relevant_count = sum(1 for word in relevant_indicators if word in content_lower)
        irrelevant_count = sum(1 for word in irrelevant_indicators if word in content_lower)
        
        is_relevant = relevant_count > irrelevant_count
        confidence = min((max(relevant_count, irrelevant_count) / 5.0), 1.0)
        
        explanation = content[:200] + "..." if len(content) > 200 else content
        status = "Verified" if is_relevant else "Rejected"
        
        return {
            "is_relevant": is_relevant,
            "confidence_score": confidence,
            "explanation": explanation,
            "status": status
        }
    
    def _fallback_verification(
        self,
        complaint_text: str,
        image_description: Optional[str]
    ) -> Dict[str, Any]:
        """
        Fallback verification using keyword matching.
        Used when Vision API fails.
        
        ✅ UPDATED: Returns ImageVerificationResult schema format
        """
        
        if not image_description:
            # No description, accept by default
            return {
                "is_relevant": True,
                "confidence_score": 0.6,
                "explanation": "No image description provided, accepting by default (Vision API unavailable)",
                "status": "Pending"
            }
        
        # Check if description relates to complaint
        text_lower = complaint_text.lower()
        desc_lower = image_description.lower()
        
        # Find common words
        text_words = set(text_lower.split())
        desc_words = set(desc_lower.split())
        common_words = text_words & desc_words
        
        # Remove common stopwords
        stopwords = {"the", "a", "an", "is", "in", "on", "at", "to", "for", "of", "with"}
        common_words = common_words - stopwords
        
        # Calculate relevance score
        relevance_score = len(common_words) / max(len(text_words), 1)
        is_relevant = relevance_score > 0.1
        
        explanation = f"Keyword matching: Found {len(common_words)} common keywords (Vision API fallback)"
        if common_words:
            explanation += f" - {', '.join(list(common_words)[:5])}"
        
        return {
            "is_relevant": is_relevant,
            "confidence_score": min(relevance_score * 2, 1.0),
            "explanation": explanation,
            "status": "Verified" if is_relevant else "Rejected"
        }
    
    def encode_bytes_to_data_uri(
        self,
        image_bytes: bytes,
        mimetype: str = "image/jpeg"
    ) -> str:
        """
        ✅ NEW: Encode image bytes to base64 data URI.
        
        Args:
            image_bytes: Image bytes from database
            mimetype: MIME type (e.g., "image/jpeg", "image/png")
        
        Returns:
            Data URI string (data:image/jpeg;base64,...)
        """
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        return f"data:{mimetype};base64,{base64_image}"
    
    def decode_data_uri_to_bytes(
        self,
        data_uri: str
    ) -> Tuple[bytes, str]:
        """
        ✅ NEW: Decode data URI back to bytes.
        
        Args:
            data_uri: Data URI string
        
        Returns:
            Tuple of (image_bytes, mimetype)
        """
        try:
            # Parse data URI: data:image/jpeg;base64,ABC123...
            header, encoded = data_uri.split(",", 1)
            mimetype = header.split(";")[0].split(":")[1]
            image_bytes = base64.b64decode(encoded)
            return image_bytes, mimetype
        except Exception as e:
            logger.error(f"Failed to decode data URI: {e}")
            raise ValueError(f"Invalid data URI format: {str(e)}")


# Create global instance
image_verification_service = ImageVerificationService()

__all__ = ["ImageVerificationService", "image_verification_service"]
