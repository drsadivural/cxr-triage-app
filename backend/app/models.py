"""
Database models for CXR Triage application.
"""
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, JSON, 
    ForeignKey, Enum as SQLEnum, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()


class TriageLevel(str, enum.Enum):
    NORMAL = "NORMAL"
    ROUTINE = "ROUTINE"
    URGENT = "URGENT"


class FindingStatus(str, enum.Enum):
    NEG = "NEG"
    POSSIBLE = "POSSIBLE"
    POSITIVE = "POSITIVE"
    UNCERTAIN = "UNCERTAIN"


class Study(Base):
    """Represents a CXR study."""
    __tablename__ = "studies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    accession_number = Column(String(64), index=True, nullable=True)
    patient_id = Column(String(64), index=True, nullable=True)
    study_date = Column(DateTime, nullable=True)
    study_description = Column(String(256), nullable=True)
    modality = Column(String(16), default="CR")
    view_position = Column(String(16), nullable=True)  # AP, PA, LATERAL
    laterality = Column(String(8), nullable=True)  # L, R
    
    # File info
    original_filename = Column(String(256))
    file_path = Column(String(512))
    file_type = Column(String(16))  # DICOM, PNG, JPEG
    
    # Processing status
    status = Column(String(32), default="pending")  # pending, processing, completed, failed
    error_message = Column(Text, nullable=True)
    
    # Triage result
    triage_level = Column(SQLEnum(TriageLevel), nullable=True)
    triage_reasons = Column(JSON, nullable=True)
    
    # Report
    report_findings = Column(Text, nullable=True)
    report_impression = Column(Text, nullable=True)
    report_llm_rewritten = Column(Boolean, default=False)
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    
    # Relationships
    findings = relationship("Finding", back_populates="study", cascade="all, delete-orphan")
    bounding_boxes = relationship("BoundingBox", back_populates="study", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="study", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_studies_created_at", "created_at"),
        Index("ix_studies_triage_level", "triage_level"),
    )


class Finding(Base):
    """Individual finding from classification model."""
    __tablename__ = "findings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    study_id = Column(UUID(as_uuid=True), ForeignKey("studies.id"), nullable=False)
    
    finding_name = Column(String(64), nullable=False)
    probability = Column(Float, nullable=False)
    calibrated_probability = Column(Float, nullable=True)
    status = Column(SQLEnum(FindingStatus), nullable=False)
    
    # Thresholds used
    triage_threshold = Column(Float, nullable=True)
    strong_threshold = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    study = relationship("Study", back_populates="findings")


class BoundingBox(Base):
    """Bounding box from detection model."""
    __tablename__ = "bounding_boxes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    study_id = Column(UUID(as_uuid=True), ForeignKey("studies.id"), nullable=False)
    
    finding_name = Column(String(64), nullable=False)
    confidence = Column(Float, nullable=False)
    
    # Normalized coordinates (0-1)
    x_min = Column(Float, nullable=False)
    y_min = Column(Float, nullable=False)
    x_max = Column(Float, nullable=False)
    y_max = Column(Float, nullable=False)
    
    # Original pixel coordinates
    x_min_px = Column(Integer, nullable=True)
    y_min_px = Column(Integer, nullable=True)
    x_max_px = Column(Integer, nullable=True)
    y_max_px = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    study = relationship("Study", back_populates="bounding_boxes")


class AuditLog(Base):
    """Audit log for all operations."""
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    study_id = Column(UUID(as_uuid=True), ForeignKey("studies.id"), nullable=True)
    
    action = Column(String(64), nullable=False)
    actor = Column(String(128), nullable=True)  # user or system
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    study = relationship("Study", back_populates="audit_logs")
    
    __table_args__ = (
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_action", "action"),
    )


class ModelRegistry(Base):
    """Registry of AI models."""
    __tablename__ = "model_registry"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_name = Column(String(128), nullable=False, unique=True)
    model_type = Column(String(32), nullable=False)  # classifier, detector
    version = Column(String(32), nullable=False)
    file_path = Column(String(512), nullable=False)
    checksum = Column(String(128), nullable=True)
    
    # Metadata
    description = Column(Text, nullable=True)
    source_url = Column(String(512), nullable=True)
    findings_supported = Column(JSON, nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AppConfig(Base):
    """Encrypted application configuration storage."""
    __tablename__ = "app_config"
    
    id = Column(Integer, primary_key=True)
    config_key = Column(String(64), unique=True, nullable=False)
    encrypted_value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class QAReview(Base):
    """QA review tags for studies."""
    __tablename__ = "qa_reviews"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    study_id = Column(UUID(as_uuid=True), ForeignKey("studies.id"), nullable=False)
    
    review_type = Column(String(32), nullable=False)  # FP, FN, TP, TN
    finding_name = Column(String(64), nullable=True)
    reviewer = Column(String(128), nullable=True)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
