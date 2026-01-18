"""
Celery tasks for async processing.
"""
import os
import time
import json
from datetime import datetime
from typing import Dict, Any
import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.celery_app import celery_app

# Database connection
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://cxr_user:cxr_password@db:5432/cxr_triage"
)
INFERENCE_URL = os.getenv("INFERENCE_SERVICE_URL", "http://inference:8001")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


@celery_app.task(bind=True, max_retries=3)
def analyze_study(self, study_id: str, image_path: str, settings: Dict[str, Any]):
    """
    Async task to analyze a CXR study.
    
    Args:
        study_id: UUID of the study
        image_path: Path to the image file
        settings: AI settings for analysis
    """
    from app.models import Study, Finding, BoundingBox, AuditLog
    
    session = SessionLocal()
    
    try:
        # Update status
        study = session.query(Study).filter(Study.id == study_id).first()
        if not study:
            raise ValueError(f"Study {study_id} not found")
        
        study.status = "processing"
        session.commit()
        
        start_time = time.time()
        
        # Call inference service
        with open(image_path, "rb") as f:
            files = {"file": (os.path.basename(image_path), f, "image/png")}
            data = {
                "detector_conf": str(settings.get("detector_confidence", 0.25)),
                "detector_iou": str(settings.get("detector_iou", 0.45)),
                "detector_max_boxes": str(settings.get("detector_max_boxes", 10)),
                "calibration_enabled": str(settings.get("calibration_enabled", True)).lower()
            }
            
            response = httpx.post(
                f"{INFERENCE_URL}/analyze",
                files=files,
                data=data,
                timeout=120.0
            )
            response.raise_for_status()
            result = response.json()
        
        # Process findings
        findings_data = result.get("findings", [])
        for f in findings_data:
            finding = Finding(
                study_id=study_id,
                finding_name=f["name"],
                probability=f["probability"],
                calibrated_probability=f["calibrated_probability"],
                status=determine_status(f, settings)
            )
            session.add(finding)
        
        # Process bounding boxes
        boxes_data = result.get("bounding_boxes", [])
        for b in boxes_data:
            box = BoundingBox(
                study_id=study_id,
                finding_name=b["name"],
                confidence=b["confidence"],
                x_min=b["x_min"],
                y_min=b["y_min"],
                x_max=b["x_max"],
                y_max=b["y_max"],
                x_min_px=b.get("x_min_px"),
                y_min_px=b.get("y_min_px"),
                x_max_px=b.get("x_max_px"),
                y_max_px=b.get("y_max_px")
            )
            session.add(box)
        
        # Determine triage level
        triage_level, triage_reasons = determine_triage(findings_data, settings)
        
        # Generate report
        report_findings, report_impression = generate_report(findings_data, settings)
        
        # Update study
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        study.status = "completed"
        study.triage_level = triage_level
        study.triage_reasons = triage_reasons
        study.report_findings = report_findings
        study.report_impression = report_impression
        study.processed_at = datetime.utcnow()
        study.processing_time_ms = processing_time_ms
        
        # Audit log
        audit = AuditLog(
            study_id=study_id,
            action="analysis_complete",
            details={
                "triage_level": triage_level,
                "processing_time_ms": processing_time_ms,
                "findings_count": len(findings_data),
                "boxes_count": len(boxes_data)
            }
        )
        session.add(audit)
        
        session.commit()
        
        return {
            "study_id": study_id,
            "status": "completed",
            "triage_level": triage_level,
            "processing_time_ms": processing_time_ms
        }
        
    except Exception as e:
        session.rollback()
        
        # Update study with error
        study = session.query(Study).filter(Study.id == study_id).first()
        if study:
            study.status = "failed"
            study.error_message = str(e)
            session.commit()
        
        # Retry or fail
        raise self.retry(exc=e, countdown=30)
    
    finally:
        session.close()


@celery_app.task
def convert_dicom(dicom_path: str, output_path: str) -> Dict[str, Any]:
    """
    Convert DICOM to PNG.
    
    Args:
        dicom_path: Path to DICOM file
        output_path: Path for output PNG
    
    Returns:
        Conversion result with metadata
    """
    import pydicom
    from PIL import Image
    import numpy as np
    
    try:
        ds = pydicom.dcmread(dicom_path)
        
        # Get pixel array
        pixel_array = ds.pixel_array.astype(float)
        
        # Normalize
        pixel_min = pixel_array.min()
        pixel_max = pixel_array.max()
        if pixel_max > pixel_min:
            pixel_array = (pixel_array - pixel_min) / (pixel_max - pixel_min) * 255
        pixel_array = pixel_array.astype(np.uint8)
        
        # Handle MONOCHROME1
        if str(getattr(ds, "PhotometricInterpretation", "")) == "MONOCHROME1":
            pixel_array = 255 - pixel_array
        
        # Save as PNG
        image = Image.fromarray(pixel_array)
        image.save(output_path, "PNG")
        
        # Extract metadata
        metadata = {
            "patient_id": str(getattr(ds, "PatientID", "")),
            "accession_number": str(getattr(ds, "AccessionNumber", "")),
            "study_date": str(getattr(ds, "StudyDate", "")),
            "modality": str(getattr(ds, "Modality", "")),
            "view_position": str(getattr(ds, "ViewPosition", "")),
        }
        
        return {
            "success": True,
            "output_path": output_path,
            "metadata": metadata
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def determine_status(finding: Dict, settings: Dict) -> str:
    """Determine finding status based on thresholds."""
    prob = finding.get("calibrated_probability", finding.get("probability", 0))
    finding_name = finding.get("name", "").lower()
    
    # Get thresholds from settings
    thresholds = settings.get("thresholds", {}).get(finding_name, {})
    triage_threshold = thresholds.get("triage_threshold", 0.3)
    strong_threshold = thresholds.get("strong_threshold", 0.7)
    
    if prob >= strong_threshold:
        return "POSITIVE"
    elif prob >= triage_threshold:
        return "POSSIBLE"
    elif prob >= triage_threshold * 0.7:
        return "UNCERTAIN"
    else:
        return "NEG"


def determine_triage(findings: list, settings: Dict) -> tuple:
    """Determine triage level from findings."""
    urgent_findings = []
    routine_findings = []
    
    for f in findings:
        status = determine_status(f, settings)
        if status == "POSITIVE":
            urgent_findings.append(f["name"])
        elif status in ["POSSIBLE", "UNCERTAIN"]:
            routine_findings.append(f["name"])
    
    if urgent_findings:
        return "URGENT", [f"High confidence {f} detected" for f in urgent_findings]
    elif routine_findings:
        return "ROUTINE", [f"Possible {f} detected" for f in routine_findings]
    else:
        return "NORMAL", ["No significant abnormalities detected"]


def generate_report(findings: list, settings: Dict) -> tuple:
    """Generate report text from findings."""
    findings_texts = []
    
    for f in findings:
        status = determine_status(f, settings)
        name = f["name"]
        
        if status == "POSITIVE":
            findings_texts.append(f"Findings suggestive of {name}.")
        elif status == "POSSIBLE":
            findings_texts.append(f"Possible {name}. Clinical correlation recommended.")
        elif status == "UNCERTAIN":
            findings_texts.append(f"Cannot exclude {name}. Radiologist review recommended.")
    
    if not findings_texts:
        findings_text = "No significant abnormalities identified."
    else:
        findings_text = " ".join(findings_texts)
    
    # Generate impression
    triage_level, reasons = determine_triage(findings, settings)
    
    if triage_level == "URGENT":
        impression = f"URGENT: {', '.join(reasons)}. Immediate clinical attention recommended."
    elif triage_level == "ROUTINE":
        impression = f"Abnormal chest radiograph. {', '.join(reasons)}. Clinical correlation recommended."
    else:
        impression = "No acute cardiopulmonary abnormality identified."
    
    return findings_text, impression
