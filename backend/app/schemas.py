"""
Pydantic schemas for API request/response models.
"""
from datetime import datetime
from typing import Optional, List, Literal
from uuid import UUID
from pydantic import BaseModel, Field

from app.config import (
    DatabaseSettings, LLMSettings, AISettings, AppSettings,
    AzureOpenAISettings, ClaudeSettings, GeminiSettings, FindingThreshold
)


# ============== Health & Status ==============

class HealthResponse(BaseModel):
    status: str
    version: str
    services: dict


class ModelInfo(BaseModel):
    name: str
    type: str
    version: str
    status: str
    findings_supported: List[str] = []


class ModelsResponse(BaseModel):
    classifier: Optional[ModelInfo] = None
    detector: Optional[ModelInfo] = None
    models_available: bool


# ============== Findings & Results ==============

class FindingResult(BaseModel):
    finding_name: str
    probability: float
    calibrated_probability: Optional[float] = None
    status: Literal["NEG", "POSSIBLE", "POSITIVE", "UNCERTAIN"]
    triage_threshold: float
    strong_threshold: float


class BoundingBoxResult(BaseModel):
    finding_name: str
    confidence: float
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    x_min_px: Optional[int] = None
    y_min_px: Optional[int] = None
    x_max_px: Optional[int] = None
    y_max_px: Optional[int] = None


class ReportResult(BaseModel):
    findings_text: str
    impression_text: str
    llm_rewritten: bool
    disclaimer: str = "AI assistance only. Not for standalone diagnosis. All findings require radiologist review."


class AnalysisResult(BaseModel):
    study_id: UUID
    status: str
    triage_level: Optional[Literal["NORMAL", "ROUTINE", "URGENT"]] = None
    triage_reasons: List[str] = []
    findings: List[FindingResult] = []
    bounding_boxes: List[BoundingBoxResult] = []
    report: Optional[ReportResult] = None
    processing_time_ms: Optional[int] = None
    model_info: dict = {}
    disclaimer: str = "AI assistance only. Not for standalone diagnosis."


class AnalyzeRequest(BaseModel):
    async_mode: bool = False


class AnalyzeResponse(BaseModel):
    study_id: UUID
    status: str
    job_id: Optional[str] = None
    result: Optional[AnalysisResult] = None


# ============== Study & Worklist ==============

class StudySummary(BaseModel):
    id: UUID
    accession_number: Optional[str] = None
    patient_id: Optional[str] = None
    study_date: Optional[datetime] = None
    view_position: Optional[str] = None
    triage_level: Optional[str] = None
    status: str
    created_at: datetime
    processing_time_ms: Optional[int] = None

    class Config:
        from_attributes = True


class StudyDetail(StudySummary):
    original_filename: Optional[str] = None
    file_type: Optional[str] = None
    triage_reasons: Optional[List[str]] = None
    report_findings: Optional[str] = None
    report_impression: Optional[str] = None
    findings: List[FindingResult] = []
    bounding_boxes: List[BoundingBoxResult] = []


class WorklistResponse(BaseModel):
    studies: List[StudySummary]
    total: int
    page: int
    page_size: int


# ============== Settings ==============

class DatabaseSettingsUpdate(BaseModel):
    db_type: Optional[Literal["postgres", "sqlite"]] = None
    host: Optional[str] = None
    port: Optional[int] = None
    user: Optional[str] = None
    password: Optional[str] = None
    dbname: Optional[str] = None
    ssl_mode: Optional[str] = None


class TestConnectionRequest(BaseModel):
    db_type: Literal["postgres", "sqlite"]
    host: str
    port: int
    user: str
    password: str
    dbname: str
    ssl_mode: str = "prefer"


class TestConnectionResponse(BaseModel):
    success: bool
    message: str


class SettingsResponse(BaseModel):
    database: DatabaseSettings
    llm: LLMSettings
    ai: AISettings


class SettingsUpdate(BaseModel):
    database: Optional[DatabaseSettings] = None
    llm: Optional[LLMSettings] = None
    ai: Optional[AISettings] = None


# ============== Audit & QA ==============

class AuditLogEntry(BaseModel):
    id: UUID
    study_id: Optional[UUID] = None
    action: str
    actor: Optional[str] = None
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    logs: List[AuditLogEntry]
    total: int
    page: int
    page_size: int


class QAReviewCreate(BaseModel):
    study_id: UUID
    review_type: Literal["FP", "FN", "TP", "TN"]
    finding_name: Optional[str] = None
    reviewer: Optional[str] = None
    notes: Optional[str] = None


class QAReviewResponse(BaseModel):
    id: UUID
    study_id: UUID
    review_type: str
    finding_name: Optional[str] = None
    reviewer: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============== Metrics ==============

class LatencyMetrics(BaseModel):
    avg_processing_time_ms: float
    p50_processing_time_ms: float
    p95_processing_time_ms: float
    p99_processing_time_ms: float
    total_studies: int
    period_hours: int


class TriageDistribution(BaseModel):
    normal: int
    routine: int
    urgent: int
    total: int


class DashboardMetrics(BaseModel):
    latency: LatencyMetrics
    triage_distribution: TriageDistribution
    studies_today: int
    studies_this_week: int


# ============== Export ==============

class ExportRequest(BaseModel):
    format: Literal["json", "png", "dicom_sr"]


class ExportResponse(BaseModel):
    file_url: str
    filename: str
    content_type: str
