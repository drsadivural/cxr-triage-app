"""
Inference Service - FastAPI application for CXR model inference.
"""
import os
import io
import time
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image
import numpy as np

from app import __version__
from app.config import settings
from app.classifier import CXRClassifier, get_classifier
from app.detector import CXRDetector, get_detector, SimpleNoduleDetector


# Global model instances
classifier: Optional[CXRClassifier] = None
detector = None
models_loaded = False


class HealthResponse(BaseModel):
    status: str
    version: str
    models_loaded: bool
    device: str


class ModelsResponse(BaseModel):
    classifier: Optional[Dict[str, Any]] = None
    detector: Optional[Dict[str, Any]] = None
    models_available: bool


class FindingResult(BaseModel):
    name: str
    probability: float
    calibrated_probability: float


class BoundingBoxResult(BaseModel):
    name: str
    confidence: float
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    x_min_px: Optional[int] = None
    y_min_px: Optional[int] = None
    x_max_px: Optional[int] = None
    y_max_px: Optional[int] = None


class AnalysisResponse(BaseModel):
    findings: List[FindingResult]
    bounding_boxes: List[BoundingBoxResult]
    processing_time_ms: int
    model_info: Dict[str, Any]


def load_models():
    """Load all models."""
    global classifier, detector, models_loaded
    
    print("Loading models...")
    
    # Load classifier
    try:
        classifier = get_classifier(settings.device)
        if not classifier.load():
            print("Warning: Classifier failed to load")
            classifier = None
    except Exception as e:
        print(f"Error loading classifier: {e}")
        classifier = None
    
    # Load detector
    try:
        detector = get_detector(settings.device)
        if not detector.load():
            print("Warning: Deep detector failed to load, using simple detector")
            detector = SimpleNoduleDetector()
            detector.load()
    except Exception as e:
        print(f"Error loading detector: {e}")
        # Fallback to simple detector
        detector = SimpleNoduleDetector()
        detector.load()
    
    models_loaded = classifier is not None or detector is not None
    print(f"Models loaded: classifier={classifier is not None}, detector={detector is not None}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print("Starting Inference Service...")
    load_models()
    yield
    # Shutdown
    print("Shutting down Inference Service...")


app = FastAPI(
    title="CXR Inference Service",
    description="AI inference service for Chest X-ray analysis",
    version=__version__,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy" if models_loaded else "degraded",
        version=__version__,
        models_loaded=models_loaded,
        device=settings.device
    )


@app.get("/models", response_model=ModelsResponse)
async def get_models_info():
    """Get information about loaded models."""
    classifier_info = classifier.get_info() if classifier else None
    detector_info = detector.get_info() if detector else None
    
    return ModelsResponse(
        classifier=classifier_info,
        detector=detector_info,
        models_available=models_loaded
    )


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_image(
    file: UploadFile = File(...),
    detector_conf: float = Form(0.25),
    detector_iou: float = Form(0.45),
    detector_max_boxes: int = Form(10),
    calibration_enabled: str = Form("true")
):
    """
    Analyze a chest X-ray image.
    
    Args:
        file: Image file (PNG, JPEG)
        detector_conf: Confidence threshold for detector
        detector_iou: IoU threshold for NMS
        detector_max_boxes: Maximum number of bounding boxes
        calibration_enabled: Whether to apply probability calibration
    
    Returns:
        Analysis results with findings and bounding boxes
    """
    start_time = time.time()
    
    # Parse calibration flag
    calibrate = calibration_enabled.lower() == "true"
    
    # Read image
    try:
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read image: {e}")
    
    findings = []
    bounding_boxes = []
    
    # Run classifier
    if classifier and classifier.loaded:
        try:
            classifier_results = classifier.predict(image, calibrate=calibrate)
            
            for finding_name, probs in classifier_results.items():
                findings.append(FindingResult(
                    name=finding_name,
                    probability=probs["probability"],
                    calibrated_probability=probs["calibrated_probability"]
                ))
        except Exception as e:
            print(f"Classifier error: {e}")
    
    # Run detector
    if detector and detector.loaded:
        try:
            detector_results = detector.predict(
                image,
                conf_threshold=detector_conf,
                iou_threshold=detector_iou,
                max_boxes=detector_max_boxes
            )
            
            for det in detector_results:
                bounding_boxes.append(BoundingBoxResult(
                    name=det["name"],
                    confidence=det["confidence"],
                    x_min=det["x_min"],
                    y_min=det["y_min"],
                    x_max=det["x_max"],
                    y_max=det["y_max"],
                    x_min_px=det.get("x_min_px"),
                    y_min_px=det.get("y_min_px"),
                    x_max_px=det.get("x_max_px"),
                    y_max_px=det.get("y_max_px")
                ))
        except Exception as e:
            print(f"Detector error: {e}")
    
    processing_time_ms = int((time.time() - start_time) * 1000)
    
    # Build model info
    model_info = {
        "classifier": classifier.get_info() if classifier else None,
        "detector": detector.get_info() if detector else None,
        "calibration_enabled": calibrate
    }
    
    return AnalysisResponse(
        findings=findings,
        bounding_boxes=bounding_boxes,
        processing_time_ms=processing_time_ms,
        model_info=model_info
    )


@app.post("/reload")
async def reload_models():
    """Reload models (admin endpoint)."""
    load_models()
    return {"status": "reloaded", "models_loaded": models_loaded}


@app.get("/download-status")
async def download_status():
    """Check model download status."""
    models_dir = settings.models_dir
    
    status = {
        "models_dir": models_dir,
        "models_dir_exists": os.path.exists(models_dir),
        "files": []
    }
    
    if os.path.exists(models_dir):
        for f in os.listdir(models_dir):
            filepath = os.path.join(models_dir, f)
            status["files"].append({
                "name": f,
                "size_mb": os.path.getsize(filepath) / (1024 * 1024) if os.path.isfile(filepath) else 0
            })
    
    return status


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
