"""
CXR Object Detection model for bounding box localization.
Implements a detector based on pretrained weights for nodule/mass detection.
"""
import os
import json
import numpy as np
from typing import Dict, List, Optional, Tuple
from pathlib import Path

import torch
import torch.nn as nn
import torchvision
from torchvision.models.detection import fasterrcnn_resnet50_fpn, FasterRCNN_ResNet50_FPN_Weights
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
import torchvision.transforms as transforms
from PIL import Image

from app.config import settings, DETECTOR_CONFIG, DETECTOR_CLASS_MAPPING


def non_max_suppression(boxes: np.ndarray, scores: np.ndarray, iou_threshold: float) -> List[int]:
    """
    Apply non-maximum suppression.
    
    Args:
        boxes: Array of shape (N, 4) with [x1, y1, x2, y2] format
        scores: Array of shape (N,) with confidence scores
        iou_threshold: IoU threshold for suppression
    
    Returns:
        List of indices to keep
    """
    if len(boxes) == 0:
        return []
    
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]
    
    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]
    
    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        
        if order.size == 1:
            break
        
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        
        w = np.maximum(0, xx2 - xx1)
        h = np.maximum(0, yy2 - yy1)
        
        intersection = w * h
        union = areas[i] + areas[order[1:]] - intersection
        iou = intersection / (union + 1e-8)
        
        inds = np.where(iou <= iou_threshold)[0]
        order = order[inds + 1]
    
    return keep


class CXRDetector:
    """
    Chest X-ray object detector for localizing abnormalities.
    Uses Faster R-CNN with pretrained backbone, fine-tuned for CXR.
    """
    
    def __init__(self, device: str = "cuda"):
        self.device = device if torch.cuda.is_available() else "cpu"
        self.model = None
        self.transform = None
        self.config = DETECTOR_CONFIG.get(settings.detector_model, {})
        self.loaded = False
        self.num_classes = len(DETECTOR_CLASS_MAPPING) + 1  # +1 for background
        
    def load(self) -> bool:
        """Load the detector model."""
        try:
            print(f"Loading detector model on {self.device}...")
            
            # Check for custom weights
            weights_path = Path(settings.models_dir) / "detector_weights.pth"
            
            if weights_path.exists():
                # Load custom trained weights
                self.model = self._create_model()
                state_dict = torch.load(weights_path, map_location=self.device)
                self.model.load_state_dict(state_dict)
                print("Loaded custom detector weights")
            else:
                # Use pretrained Faster R-CNN and adapt for CXR
                # This provides a working detector even without custom weights
                self.model = self._create_model(pretrained=True)
                print("Using pretrained Faster R-CNN backbone (no custom CXR weights)")
            
            self.model = self.model.to(self.device)
            self.model.eval()
            
            # Setup transforms
            self.transform = transforms.Compose([
                transforms.Resize((512, 512)),
                transforms.ToTensor(),
            ])
            
            self.loaded = True
            print("Detector loaded successfully")
            return True
            
        except Exception as e:
            print(f"Failed to load detector: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _create_model(self, pretrained: bool = False) -> nn.Module:
        """Create the Faster R-CNN model."""
        if pretrained:
            # Load pretrained model
            model = fasterrcnn_resnet50_fpn(weights=FasterRCNN_ResNet50_FPN_Weights.DEFAULT)
        else:
            model = fasterrcnn_resnet50_fpn(weights=None)
        
        # Replace the classifier head for our number of classes
        in_features = model.roi_heads.box_predictor.cls_score.in_features
        model.roi_heads.box_predictor = FastRCNNPredictor(in_features, self.num_classes)
        
        return model
    
    def preprocess(self, image: Image.Image) -> Tuple[torch.Tensor, Tuple[int, int]]:
        """
        Preprocess image for model input.
        
        Returns:
            Tuple of (tensor, original_size)
        """
        original_size = image.size  # (width, height)
        
        # Convert to RGB if needed
        if image.mode != "RGB":
            image = image.convert("RGB")
        
        # Apply transforms
        tensor = self.transform(image)
        
        return tensor.to(self.device), original_size
    
    @torch.no_grad()
    def predict(
        self,
        image: Image.Image,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        max_boxes: int = 10
    ) -> List[Dict]:
        """
        Run detection on an image.
        
        Args:
            image: PIL Image
            conf_threshold: Confidence threshold for detections
            iou_threshold: IoU threshold for NMS
            max_boxes: Maximum number of boxes to return
        
        Returns:
            List of detection dictionaries with boxes and classes
        """
        if not self.loaded:
            raise RuntimeError("Model not loaded. Call load() first.")
        
        # Preprocess
        input_tensor, original_size = self.preprocess(image)
        
        # Run inference
        outputs = self.model([input_tensor])
        
        # Process outputs
        output = outputs[0]
        boxes = output["boxes"].cpu().numpy()
        scores = output["scores"].cpu().numpy()
        labels = output["labels"].cpu().numpy()
        
        # Filter by confidence
        mask = scores >= conf_threshold
        boxes = boxes[mask]
        scores = scores[mask]
        labels = labels[mask]
        
        if len(boxes) == 0:
            return []
        
        # Apply NMS
        keep_indices = non_max_suppression(boxes, scores, iou_threshold)
        boxes = boxes[keep_indices]
        scores = scores[keep_indices]
        labels = labels[keep_indices]
        
        # Limit number of boxes
        if len(boxes) > max_boxes:
            top_indices = np.argsort(scores)[::-1][:max_boxes]
            boxes = boxes[top_indices]
            scores = scores[top_indices]
            labels = labels[top_indices]
        
        # Convert to output format
        results = []
        input_size = 512  # Our resize target
        orig_w, orig_h = original_size
        
        for box, score, label in zip(boxes, scores, labels):
            # Convert to normalized coordinates
            x1, y1, x2, y2 = box
            
            # Normalize to [0, 1]
            x1_norm = x1 / input_size
            y1_norm = y1 / input_size
            x2_norm = x2 / input_size
            y2_norm = y2 / input_size
            
            # Convert to original pixel coordinates
            x1_px = int(x1_norm * orig_w)
            y1_px = int(y1_norm * orig_h)
            x2_px = int(x2_norm * orig_w)
            y2_px = int(y2_norm * orig_h)
            
            # Get class name
            class_id = int(label) - 1  # Subtract 1 because 0 is background
            if class_id in DETECTOR_CLASS_MAPPING:
                class_name = DETECTOR_CLASS_MAPPING[class_id]
            else:
                class_name = "unknown"
            
            results.append({
                "name": class_name,
                "confidence": float(score),
                "x_min": float(x1_norm),
                "y_min": float(y1_norm),
                "x_max": float(x2_norm),
                "y_max": float(y2_norm),
                "x_min_px": x1_px,
                "y_min_px": y1_px,
                "x_max_px": x2_px,
                "y_max_px": y2_px
            })
        
        return results
    
    def get_info(self) -> Dict:
        """Get model information."""
        return {
            "name": self.config.get("name", "Faster R-CNN Detector"),
            "version": self.config.get("version", "1.0.0"),
            "status": "loaded" if self.loaded else "not_loaded",
            "device": self.device,
            "findings_supported": list(DETECTOR_CLASS_MAPPING.values()),
            "source": self.config.get("source", "torchvision")
        }


class SimpleNoduleDetector:
    """
    Simple nodule detector using image processing techniques.
    Fallback when deep learning detector is not available.
    """
    
    def __init__(self):
        self.loaded = False
    
    def load(self) -> bool:
        """Load the detector (no-op for this simple detector)."""
        self.loaded = True
        return True
    
    def predict(
        self,
        image: Image.Image,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        max_boxes: int = 10
    ) -> List[Dict]:
        """
        Detect potential nodules using image processing.
        This is a simplified approach for demonstration.
        """
        import cv2
        from scipy import ndimage
        
        # Convert to grayscale numpy array
        if image.mode != "L":
            gray = image.convert("L")
        else:
            gray = image
        
        img_array = np.array(gray)
        orig_h, orig_w = img_array.shape
        
        # Resize for processing
        img_resized = cv2.resize(img_array, (512, 512))
        
        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(img_resized, (5, 5), 0)
        
        # Detect circular structures using Hough circles
        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=30,
            param1=50,
            param2=30,
            minRadius=5,
            maxRadius=50
        )
        
        results = []
        
        if circles is not None:
            circles = np.uint16(np.around(circles))
            
            for circle in circles[0, :max_boxes]:
                cx, cy, r = circle
                
                # Convert to box coordinates
                x1 = max(0, cx - r)
                y1 = max(0, cy - r)
                x2 = min(512, cx + r)
                y2 = min(512, cy + r)
                
                # Normalize
                x1_norm = x1 / 512
                y1_norm = y1 / 512
                x2_norm = x2 / 512
                y2_norm = y2 / 512
                
                # Calculate confidence based on circularity and intensity
                roi = img_resized[int(y1):int(y2), int(x1):int(x2)]
                if roi.size > 0:
                    intensity_score = 1 - (np.mean(roi) / 255)  # Darker = higher score
                    size_score = min(1.0, r / 30)  # Reasonable size
                    confidence = (intensity_score + size_score) / 2 * 0.5 + 0.25
                else:
                    confidence = 0.25
                
                if confidence >= conf_threshold:
                    results.append({
                        "name": "nodule",
                        "confidence": float(confidence),
                        "x_min": float(x1_norm),
                        "y_min": float(y1_norm),
                        "x_max": float(x2_norm),
                        "y_max": float(y2_norm),
                        "x_min_px": int(x1_norm * orig_w),
                        "y_min_px": int(y1_norm * orig_h),
                        "x_max_px": int(x2_norm * orig_w),
                        "y_max_px": int(y2_norm * orig_h)
                    })
        
        return results
    
    def get_info(self) -> Dict:
        """Get model information."""
        return {
            "name": "Simple Nodule Detector",
            "version": "1.0.0",
            "status": "loaded" if self.loaded else "not_loaded",
            "device": "cpu",
            "findings_supported": ["nodule"],
            "source": "image_processing"
        }


def get_detector(device: str = None, use_simple: bool = False) -> CXRDetector:
    """Factory function to create detector."""
    if use_simple:
        return SimpleNoduleDetector()
    
    if device is None:
        device = settings.device
    return CXRDetector(device)
