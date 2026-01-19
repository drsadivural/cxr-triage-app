"""
Client for communicating with the inference service.
"""
import httpx
from typing import Optional, Dict, Any, List
import base64
from pathlib import Path

from app.config import settings
from app.schemas import FindingResult, BoundingBoxResult


class InferenceClient:
    """Client for the inference service."""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or settings.inference_service_url
        self.timeout = httpx.Timeout(120.0, connect=10.0)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check inference service health."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(f"{self.base_url}/health")
                response.raise_for_status()
                return response.json()
            except httpx.ConnectError:
                return {"status": "unavailable", "error": "Cannot connect to inference service"}
            except Exception as e:
                return {"status": "unhealthy", "error": str(e)}
    
    async def get_models_info(self) -> Dict[str, Any]:
        """Get information about loaded models."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(f"{self.base_url}/models")
                response.raise_for_status()
                return response.json()
            except httpx.ConnectError:
                return {"error": "Cannot connect to inference service", "models_available": False}
            except Exception as e:
                return {"error": str(e), "models_available": False}
    
    async def analyze_image(
        self,
        image_path: str,
        detector_conf: float = 0.25,
        detector_iou: float = 0.45,
        detector_max_boxes: int = 10,
        calibration_enabled: bool = True
    ) -> Dict[str, Any]:
        """
        Send image to inference service for analysis.
        
        Args:
            image_path: Path to the image file (PNG/JPEG)
            detector_conf: Confidence threshold for detector
            detector_iou: IoU threshold for NMS
            detector_max_boxes: Maximum number of boxes to return
            calibration_enabled: Whether to apply probability calibration
        
        Returns:
            Dictionary containing findings and bounding boxes
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                # Read image file
                with open(image_path, "rb") as f:
                    image_data = f.read()
                
                # Prepare multipart form data
                files = {
                    "file": (Path(image_path).name, image_data, "image/png")
                }
                data = {
                    "detector_conf": str(detector_conf),
                    "detector_iou": str(detector_iou),
                    "detector_max_boxes": str(detector_max_boxes),
                    "calibration_enabled": str(calibration_enabled).lower()
                }
                
                response = await client.post(
                    f"{self.base_url}/analyze",
                    files=files,
                    data=data
                )
                response.raise_for_status()
                return response.json()
            except httpx.ConnectError as e:
                raise ConnectionError(f"Cannot connect to inference service at {self.base_url}: {e}")
            except httpx.HTTPStatusError as e:
                raise RuntimeError(f"Inference service error: {e.response.status_code} - {e.response.text}")
            except FileNotFoundError:
                raise FileNotFoundError(f"Image file not found: {image_path}")
    
    async def analyze_image_bytes(
        self,
        image_bytes: bytes,
        filename: str = "image.png",
        detector_conf: float = 0.25,
        detector_iou: float = 0.45,
        detector_max_boxes: int = 10,
        calibration_enabled: bool = True
    ) -> Dict[str, Any]:
        """
        Send image bytes to inference service for analysis.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                files = {
                    "file": (filename, image_bytes, "image/png")
                }
                data = {
                    "detector_conf": str(detector_conf),
                    "detector_iou": str(detector_iou),
                    "detector_max_boxes": str(detector_max_boxes),
                    "calibration_enabled": str(calibration_enabled).lower()
                }
                
                response = await client.post(
                    f"{self.base_url}/analyze",
                    files=files,
                    data=data
                )
                response.raise_for_status()
                return response.json()
            except httpx.ConnectError as e:
                raise ConnectionError(f"Cannot connect to inference service: {e}")
            except httpx.HTTPStatusError as e:
                raise RuntimeError(f"Inference service error: {e.response.status_code}")
    
    def parse_findings(self, response: Dict[str, Any], ai_settings) -> List[FindingResult]:
        """Parse findings from inference response."""
        findings = []
        raw_findings = response.get("findings", [])
        
        for f in raw_findings:
            finding_name = f.get("name", "")
            prob = f.get("probability", 0.0)
            calibrated_prob = f.get("calibrated_probability", prob)
            
            # Get thresholds from settings
            threshold = ai_settings.get_threshold(finding_name)
            
            # Determine status
            effective_prob = calibrated_prob if ai_settings.calibration_enabled else prob
            
            if effective_prob >= threshold.strong_threshold:
                status = "POSITIVE"
            elif effective_prob >= threshold.triage_threshold:
                status = "POSSIBLE"
            elif effective_prob >= threshold.triage_threshold * 0.7:
                status = "UNCERTAIN"
            else:
                status = "NEG"
            
            findings.append(FindingResult(
                finding_name=finding_name,
                probability=prob,
                calibrated_probability=calibrated_prob,
                status=status,
                triage_threshold=threshold.triage_threshold,
                strong_threshold=threshold.strong_threshold
            ))
        
        return findings
    
    def parse_bounding_boxes(self, response: Dict[str, Any]) -> List[BoundingBoxResult]:
        """Parse bounding boxes from inference response."""
        boxes = []
        raw_boxes = response.get("bounding_boxes", [])
        
        for b in raw_boxes:
            boxes.append(BoundingBoxResult(
                finding_name=b.get("name", ""),
                confidence=b.get("confidence", 0.0),
                x_min=b.get("x_min", 0.0),
                y_min=b.get("y_min", 0.0),
                x_max=b.get("x_max", 0.0),
                y_max=b.get("y_max", 0.0),
                x_min_px=b.get("x_min_px"),
                y_min_px=b.get("y_min_px"),
                x_max_px=b.get("x_max_px"),
                y_max_px=b.get("y_max_px")
            ))
        
        return boxes


# Singleton instance
_inference_client: Optional[InferenceClient] = None


def get_inference_client() -> InferenceClient:
    """Factory function to create inference client."""
    global _inference_client
    if _inference_client is None:
        _inference_client = InferenceClient()
    return _inference_client
