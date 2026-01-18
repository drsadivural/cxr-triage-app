"""
CXR Classification model using TorchXRayVision.
Real pretrained model with calibration support.
"""
import os
import json
import numpy as np
from typing import Dict, List, Optional, Tuple
from pathlib import Path

import torch
import torch.nn.functional as F
import torchvision.transforms as transforms
from PIL import Image

try:
    import torchxrayvision as xrv
    TORCHXRAYVISION_AVAILABLE = True
except ImportError:
    TORCHXRAYVISION_AVAILABLE = False
    print("Warning: torchxrayvision not available")

from app.config import settings, CLASSIFIER_CONFIG, FINDING_MAPPING


class TemperatureScaling:
    """Temperature scaling for probability calibration."""
    
    def __init__(self, temperature: float = 1.0):
        self.temperature = temperature
    
    def calibrate(self, logits: np.ndarray) -> np.ndarray:
        """Apply temperature scaling to logits."""
        return logits / self.temperature


class IsotonicCalibrator:
    """Isotonic regression calibrator."""
    
    def __init__(self, calibration_map: Dict[str, List[Tuple[float, float]]]):
        """
        Initialize with calibration mapping.
        
        Args:
            calibration_map: Dict mapping finding names to list of (raw_prob, calibrated_prob) tuples
        """
        self.calibration_map = calibration_map
    
    def calibrate(self, finding: str, probability: float) -> float:
        """Calibrate a single probability."""
        if finding not in self.calibration_map:
            return probability
        
        points = self.calibration_map[finding]
        if not points:
            return probability
        
        # Linear interpolation
        points = sorted(points, key=lambda x: x[0])
        
        if probability <= points[0][0]:
            return points[0][1]
        if probability >= points[-1][0]:
            return points[-1][1]
        
        for i in range(len(points) - 1):
            if points[i][0] <= probability <= points[i + 1][0]:
                # Linear interpolation
                t = (probability - points[i][0]) / (points[i + 1][0] - points[i][0])
                return points[i][1] + t * (points[i + 1][1] - points[i][1])
        
        return probability


class CXRClassifier:
    """
    Chest X-ray classifier using TorchXRayVision.
    Uses real pretrained DenseNet121 model trained on multiple CXR datasets.
    """
    
    def __init__(self, device: str = "cuda"):
        self.device = device if torch.cuda.is_available() else "cpu"
        self.model = None
        self.transform = None
        self.calibrator = None
        self.config = CLASSIFIER_CONFIG.get(settings.classifier_model, {})
        self.loaded = False
        
    def load(self) -> bool:
        """Load the model and calibration."""
        if not TORCHXRAYVISION_AVAILABLE:
            print("TorchXRayVision not available, cannot load classifier")
            return False
        
        try:
            # Load TorchXRayVision DenseNet model
            # This downloads pretrained weights automatically
            print(f"Loading TorchXRayVision model on {self.device}...")
            
            self.model = xrv.models.DenseNet(weights="densenet121-res224-all")
            self.model = self.model.to(self.device)
            self.model.eval()
            
            # Setup transforms - TorchXRayVision expects specific preprocessing
            self.transform = transforms.Compose([
                xrv.datasets.XRayCenterCrop(),
                xrv.datasets.XRayResizer(224)
            ])
            
            # Load calibration if available
            self._load_calibration()
            
            self.loaded = True
            print("Classifier loaded successfully")
            return True
            
        except Exception as e:
            print(f"Failed to load classifier: {e}")
            return False
    
    def _load_calibration(self):
        """Load calibration parameters."""
        calibration_path = Path(settings.models_dir) / settings.calibration_file
        
        if calibration_path.exists():
            try:
                with open(calibration_path) as f:
                    cal_data = json.load(f)
                
                if "temperature" in cal_data:
                    self.calibrator = TemperatureScaling(cal_data["temperature"])
                elif "isotonic" in cal_data:
                    self.calibrator = IsotonicCalibrator(cal_data["isotonic"])
                
                print("Calibration loaded")
            except Exception as e:
                print(f"Failed to load calibration: {e}")
        else:
            # Use default temperature scaling
            self.calibrator = TemperatureScaling(1.2)  # Slight smoothing
    
    def preprocess(self, image: Image.Image) -> torch.Tensor:
        """Preprocess image for model input."""
        # Convert to grayscale if needed
        if image.mode != "L":
            image = image.convert("L")
        
        # Convert to numpy array
        img_array = np.array(image).astype(np.float32)
        
        # Normalize to [0, 1]
        img_array = img_array / 255.0
        
        # Apply TorchXRayVision normalization
        # XRV expects values in [-1024, 1024] range (like HU values)
        img_array = (img_array - 0.5) * 2048
        
        # Add channel dimension
        img_array = img_array[np.newaxis, ...]
        
        # Apply transforms
        img_array = self.transform(img_array)
        
        # Convert to tensor and add batch dimension
        tensor = torch.from_numpy(img_array).unsqueeze(0)
        
        return tensor.to(self.device)
    
    @torch.no_grad()
    def predict(self, image: Image.Image, calibrate: bool = True) -> Dict[str, Dict]:
        """
        Run prediction on an image.
        
        Args:
            image: PIL Image
            calibrate: Whether to apply probability calibration
        
        Returns:
            Dictionary with finding names and their probabilities
        """
        if not self.loaded:
            raise RuntimeError("Model not loaded. Call load() first.")
        
        # Preprocess
        input_tensor = self.preprocess(image)
        
        # Run inference
        outputs = self.model(input_tensor)
        
        # Get probabilities (model outputs are already sigmoid-activated)
        probs = outputs.cpu().numpy()[0]
        
        # Map to our findings
        results = {}
        
        # TorchXRayVision pathologies
        pathologies = self.model.pathologies
        
        for i, pathology in enumerate(pathologies):
            if pathology in FINDING_MAPPING:
                finding_name = FINDING_MAPPING[pathology]
                raw_prob = float(probs[i])
                
                # Apply calibration
                if calibrate and self.calibrator:
                    if isinstance(self.calibrator, TemperatureScaling):
                        # For temperature scaling, we need to convert back to logits
                        logit = np.log(raw_prob / (1 - raw_prob + 1e-8))
                        calibrated_logit = self.calibrator.calibrate(logit)
                        calibrated_prob = 1 / (1 + np.exp(-calibrated_logit))
                    else:
                        calibrated_prob = self.calibrator.calibrate(finding_name, raw_prob)
                else:
                    calibrated_prob = raw_prob
                
                # Handle multiple mappings to same finding (take max)
                if finding_name in results:
                    if raw_prob > results[finding_name]["probability"]:
                        results[finding_name] = {
                            "probability": raw_prob,
                            "calibrated_probability": float(calibrated_prob)
                        }
                else:
                    results[finding_name] = {
                        "probability": raw_prob,
                        "calibrated_probability": float(calibrated_prob)
                    }
        
        return results
    
    def get_info(self) -> Dict:
        """Get model information."""
        return {
            "name": self.config.get("name", "Unknown"),
            "version": self.config.get("version", "Unknown"),
            "status": "loaded" if self.loaded else "not_loaded",
            "device": self.device,
            "findings_supported": list(set(FINDING_MAPPING.values())),
            "source": self.config.get("source", "unknown")
        }


def get_classifier(device: str = None) -> CXRClassifier:
    """Factory function to create classifier."""
    if device is None:
        device = settings.device
    return CXRClassifier(device)
