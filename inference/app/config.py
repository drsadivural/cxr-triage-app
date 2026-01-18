"""
Inference service configuration.
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Inference service settings."""
    
    # Model paths
    models_dir: str = "/app/models"
    classifier_model: str = "densenet121-res224-all"
    detector_model: str = "vindr_detector"
    
    # Device settings
    device: str = "cuda"  # cuda or cpu
    use_onnx: bool = True
    
    # Calibration
    calibration_file: str = "calibration.json"
    
    # Performance
    batch_size: int = 1
    num_workers: int = 2
    
    class Config:
        env_prefix = "INFERENCE_"


settings = Settings()


# Model configurations
CLASSIFIER_CONFIG = {
    "densenet121-res224-all": {
        "name": "DenseNet121-All",
        "version": "1.0.0",
        "input_size": 224,
        "findings": [
            "Atelectasis",
            "Consolidation", 
            "Infiltration",
            "Pneumothorax",
            "Edema",
            "Emphysema",
            "Fibrosis",
            "Effusion",
            "Pneumonia",
            "Pleural_Thickening",
            "Cardiomegaly",
            "Nodule",
            "Mass",
            "Hernia"
        ],
        "source": "torchxrayvision"
    }
}

DETECTOR_CONFIG = {
    "vindr_detector": {
        "name": "VinDr-CXR Detector",
        "version": "1.0.0",
        "input_size": 512,
        "findings": [
            "Nodule/Mass",
            "Pleural effusion",
            "Pneumothorax",
            "Consolidation",
            "Cardiomegaly"
        ],
        "source": "vindr-cxr"
    }
}

# Mapping from TorchXRayVision findings to our app findings
FINDING_MAPPING = {
    "Pneumothorax": "pneumothorax",
    "Effusion": "pleural_effusion",
    "Consolidation": "consolidation",
    "Atelectasis": "consolidation",  # Map to consolidation
    "Cardiomegaly": "cardiomegaly",
    "Edema": "edema",
    "Nodule": "nodule",
    "Mass": "mass",
}

# Detector class mapping
DETECTOR_CLASS_MAPPING = {
    0: "nodule",
    1: "mass",
    2: "pleural_effusion",
    3: "pneumothorax",
    4: "consolidation",
    5: "cardiomegaly"
}
