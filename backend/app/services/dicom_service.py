"""
DICOM processing service for reading and converting DICOM files.
"""
import os
import io
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
import numpy as np
from PIL import Image
import pydicom
from pydicom.pixel_data_handlers.util import apply_voi_lut, apply_modality_lut


class DicomService:
    """Service for DICOM file processing."""
    
    def __init__(self, upload_dir: str = "/app/uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    def read_dicom(self, file_path: str) -> pydicom.Dataset:
        """Read a DICOM file."""
        return pydicom.dcmread(file_path)
    
    def extract_metadata(self, ds: pydicom.Dataset) -> Dict[str, Any]:
        """Extract relevant metadata from DICOM dataset."""
        metadata = {}
        
        # Patient info
        metadata["patient_id"] = str(getattr(ds, "PatientID", ""))
        metadata["patient_name"] = str(getattr(ds, "PatientName", ""))
        
        # Study info
        metadata["accession_number"] = str(getattr(ds, "AccessionNumber", ""))
        metadata["study_description"] = str(getattr(ds, "StudyDescription", ""))
        metadata["study_date"] = self._parse_date(getattr(ds, "StudyDate", None))
        metadata["study_time"] = str(getattr(ds, "StudyTime", ""))
        
        # Series info
        metadata["modality"] = str(getattr(ds, "Modality", "CR"))
        metadata["series_description"] = str(getattr(ds, "SeriesDescription", ""))
        
        # Image info
        metadata["view_position"] = str(getattr(ds, "ViewPosition", ""))
        metadata["laterality"] = str(getattr(ds, "ImageLaterality", getattr(ds, "Laterality", "")))
        metadata["body_part"] = str(getattr(ds, "BodyPartExamined", ""))
        
        # Image dimensions
        metadata["rows"] = int(getattr(ds, "Rows", 0))
        metadata["columns"] = int(getattr(ds, "Columns", 0))
        metadata["bits_stored"] = int(getattr(ds, "BitsStored", 0))
        
        # Photometric interpretation
        metadata["photometric_interpretation"] = str(getattr(ds, "PhotometricInterpretation", ""))
        
        return metadata
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse DICOM date string to datetime."""
        if not date_str:
            return None
        try:
            return datetime.strptime(str(date_str), "%Y%m%d")
        except ValueError:
            return None
    
    def convert_to_png(
        self,
        ds: pydicom.Dataset,
        output_path: Optional[str] = None,
        apply_windowing: bool = True
    ) -> Tuple[bytes, str]:
        """
        Convert DICOM pixel data to PNG.
        
        Args:
            ds: DICOM dataset
            output_path: Optional path to save PNG file
            apply_windowing: Whether to apply VOI LUT windowing
        
        Returns:
            Tuple of (PNG bytes, output path)
        """
        # Get pixel array
        pixel_array = ds.pixel_array.astype(float)
        
        # Apply modality LUT if present
        if hasattr(ds, "RescaleSlope") or hasattr(ds, "RescaleIntercept"):
            pixel_array = apply_modality_lut(pixel_array, ds)
        
        # Apply VOI LUT (windowing) if requested
        if apply_windowing:
            try:
                pixel_array = apply_voi_lut(pixel_array, ds)
            except Exception:
                # Fallback to simple windowing
                window_center = getattr(ds, "WindowCenter", None)
                window_width = getattr(ds, "WindowWidth", None)
                
                if window_center is not None and window_width is not None:
                    if isinstance(window_center, pydicom.multival.MultiValue):
                        window_center = window_center[0]
                    if isinstance(window_width, pydicom.multival.MultiValue):
                        window_width = window_width[0]
                    
                    min_val = window_center - window_width / 2
                    max_val = window_center + window_width / 2
                    pixel_array = np.clip(pixel_array, min_val, max_val)
        
        # Normalize to 0-255
        pixel_min = pixel_array.min()
        pixel_max = pixel_array.max()
        if pixel_max > pixel_min:
            pixel_array = (pixel_array - pixel_min) / (pixel_max - pixel_min) * 255
        pixel_array = pixel_array.astype(np.uint8)
        
        # Handle photometric interpretation
        photometric = str(getattr(ds, "PhotometricInterpretation", "MONOCHROME2"))
        if photometric == "MONOCHROME1":
            # Invert for MONOCHROME1
            pixel_array = 255 - pixel_array
        
        # Create PIL Image
        image = Image.fromarray(pixel_array)
        
        # Convert to RGB if grayscale
        if image.mode != "RGB":
            image = image.convert("RGB")
        
        # Save to bytes
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        png_bytes = buffer.getvalue()
        
        # Save to file if path provided
        if output_path:
            with open(output_path, "wb") as f:
                f.write(png_bytes)
        
        return png_bytes, output_path or ""
    
    def process_uploaded_file(
        self,
        file_bytes: bytes,
        filename: str,
        study_id: str
    ) -> Dict[str, Any]:
        """
        Process an uploaded file (DICOM or image).
        
        Returns:
            Dictionary with file info and paths
        """
        # Create study directory
        study_dir = self.upload_dir / study_id
        study_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine file type
        file_ext = Path(filename).suffix.lower()
        
        result = {
            "original_filename": filename,
            "study_dir": str(study_dir),
            "metadata": {}
        }
        
        if file_ext in [".dcm", ".dicom"] or self._is_dicom(file_bytes):
            # Process as DICOM
            result["file_type"] = "DICOM"
            
            # Save original DICOM
            dicom_path = study_dir / "original.dcm"
            with open(dicom_path, "wb") as f:
                f.write(file_bytes)
            result["original_path"] = str(dicom_path)
            
            # Read and extract metadata
            ds = pydicom.dcmread(io.BytesIO(file_bytes))
            result["metadata"] = self.extract_metadata(ds)
            
            # Convert to PNG
            png_path = study_dir / "image.png"
            self.convert_to_png(ds, str(png_path))
            result["png_path"] = str(png_path)
            
        elif file_ext in [".png", ".jpg", ".jpeg"]:
            # Process as regular image
            result["file_type"] = file_ext.upper().replace(".", "")
            
            # Save original
            original_path = study_dir / f"original{file_ext}"
            with open(original_path, "wb") as f:
                f.write(file_bytes)
            result["original_path"] = str(original_path)
            
            # Convert to PNG if needed
            if file_ext != ".png":
                image = Image.open(io.BytesIO(file_bytes))
                png_path = study_dir / "image.png"
                image.save(png_path, "PNG")
                result["png_path"] = str(png_path)
            else:
                result["png_path"] = str(original_path)
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
        
        return result
    
    def _is_dicom(self, file_bytes: bytes) -> bool:
        """Check if file bytes represent a DICOM file."""
        # Check for DICOM magic number at offset 128
        if len(file_bytes) > 132:
            return file_bytes[128:132] == b"DICM"
        return False
    
    def create_dicom_sr(
        self,
        original_ds: pydicom.Dataset,
        findings: list,
        triage_level: str,
        report_text: str
    ) -> bytes:
        """
        Create a DICOM Structured Report from analysis results.
        
        This is a simplified SR - full implementation would require
        proper SR templates and TID structures.
        """
        from pydicom.uid import generate_uid
        from pydicom.dataset import FileDataset, FileMetaDataset
        
        # Create file meta
        file_meta = FileMetaDataset()
        file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.88.11"  # Basic Text SR
        file_meta.MediaStorageSOPInstanceUID = generate_uid()
        file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
        
        # Create SR dataset
        sr = FileDataset(None, {}, file_meta=file_meta, preamble=b"\0" * 128)
        
        # Copy patient/study info from original
        sr.PatientID = getattr(original_ds, "PatientID", "")
        sr.PatientName = getattr(original_ds, "PatientName", "")
        sr.StudyInstanceUID = getattr(original_ds, "StudyInstanceUID", generate_uid())
        sr.StudyDate = getattr(original_ds, "StudyDate", "")
        sr.StudyTime = getattr(original_ds, "StudyTime", "")
        sr.AccessionNumber = getattr(original_ds, "AccessionNumber", "")
        
        # SR specific
        sr.SOPClassUID = "1.2.840.10008.5.1.4.1.1.88.11"
        sr.SOPInstanceUID = generate_uid()
        sr.SeriesInstanceUID = generate_uid()
        sr.Modality = "SR"
        sr.SeriesDescription = "AI Analysis Report"
        
        # Content
        sr.ContentDate = datetime.now().strftime("%Y%m%d")
        sr.ContentTime = datetime.now().strftime("%H%M%S")
        
        # Simplified text content (not full SR structure)
        sr.TextValue = report_text
        
        # Save to bytes
        buffer = io.BytesIO()
        sr.save_as(buffer)
        return buffer.getvalue()


def get_dicom_service(upload_dir: str = None) -> DicomService:
    """Factory function to create DICOM service."""
    from app.config import settings
    return DicomService(upload_dir or settings.upload_dir)
