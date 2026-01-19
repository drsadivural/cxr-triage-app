"""
Main FastAPI application for CXR Triage System.
"""
import os
import time
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from app import __version__
from app.config import settings, AppSettings, get_secret_manager
from app.database import get_db, create_tables, load_app_settings, save_app_settings, test_connection
from app.models import Study, Finding, BoundingBox, AuditLog, ModelRegistry, QAReview, TriageLevel
from app.schemas import (
    HealthResponse, ModelsResponse, ModelInfo,
    AnalyzeResponse, AnalysisResult, FindingResult, BoundingBoxResult, ReportResult,
    StudySummary, StudyDetail, WorklistResponse,
    SettingsResponse, SettingsUpdate, TestConnectionRequest, TestConnectionResponse,
    AuditLogEntry, AuditLogResponse, QAReviewCreate, QAReviewResponse,
    DashboardMetrics, LatencyMetrics, TriageDistribution,
    ExportRequest, ExportResponse
)
from app.services.inference_client import get_inference_client
from app.services.dicom_service import get_dicom_service
from app.services.report_service import get_report_generator
from app.services.audit_service import get_audit_service


# Prometheus metrics
REQUEST_COUNT = Counter("cxr_requests_total", "Total requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("cxr_request_latency_seconds", "Request latency", ["method", "endpoint"])
ANALYSIS_COUNT = Counter("cxr_analysis_total", "Total analyses", ["triage_level"])
ANALYSIS_LATENCY = Histogram("cxr_analysis_latency_ms", "Analysis latency in ms")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print("Starting CXR Triage System...")
    await create_tables()
    print("Database tables created/verified")
    yield
    # Shutdown
    print("Shutting down CXR Triage System...")


app = FastAPI(
    title="CXR Triage System",
    description="AI-powered Chest X-ray Triage and Detection System",
    version=__version__,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Health & Status ==============

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    inference_client = get_inference_client()
    inference_health = await inference_client.health_check()
    
    db_healthy = await test_connection()
    
    return HealthResponse(
        status="healthy" if db_healthy else "degraded",
        version=__version__,
        services={
            "database": "healthy" if db_healthy else "unhealthy",
            "inference": inference_health.get("status", "unknown"),
        }
    )


@app.get("/v1/models", response_model=ModelsResponse)
async def get_models():
    """Get information about loaded models."""
    inference_client = get_inference_client()
    models_info = await inference_client.get_models_info()
    
    classifier = None
    detector = None
    
    if "classifier" in models_info:
        c = models_info["classifier"]
        classifier = ModelInfo(
            name=c.get("name", "Unknown"),
            type="classifier",
            version=c.get("version", "Unknown"),
            status=c.get("status", "unknown"),
            findings_supported=c.get("findings_supported", [])
        )
    
    if "detector" in models_info:
        d = models_info["detector"]
        detector = ModelInfo(
            name=d.get("name", "Unknown"),
            type="detector",
            version=d.get("version", "Unknown"),
            status=d.get("status", "unknown"),
            findings_supported=d.get("findings_supported", [])
        )
    
    return ModelsResponse(
        classifier=classifier,
        detector=detector,
        models_available=models_info.get("models_available", False)
    )


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ============== Analysis ==============

@app.post("/v1/cxr/analyze", response_model=AnalyzeResponse)
async def analyze_cxr(
    request: Request,
    file: UploadFile = File(...),
    async_mode: bool = Form(False),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze a chest X-ray image.
    
    Accepts DICOM, PNG, or JPEG files.
    Returns findings, bounding boxes, triage level, and report.
    """
    start_time = time.time()
    
    # Load settings
    app_settings = await load_app_settings(db)
    
    # Read file
    file_bytes = await file.read()
    filename = file.filename or "unknown"
    
    # Create study record
    study = Study(
        original_filename=filename,
        status="processing"
    )
    db.add(study)
    await db.commit()
    await db.refresh(study)
    
    # Audit log
    audit_service = get_audit_service(db)
    client_ip = request.client.host if request.client else None
    await audit_service.log_study_upload(study.id, filename, "unknown", client_ip)
    
    try:
        # Process file
        dicom_service = get_dicom_service()
        file_info = dicom_service.process_uploaded_file(file_bytes, filename, str(study.id))
        
        # Update study with file info
        study.file_path = file_info["png_path"]
        study.file_type = file_info["file_type"]
        
        metadata = file_info.get("metadata", {})
        study.patient_id = metadata.get("patient_id")
        study.accession_number = metadata.get("accession_number")
        study.study_date = metadata.get("study_date")
        study.study_description = metadata.get("study_description")
        study.modality = metadata.get("modality", "CR")
        study.view_position = metadata.get("view_position")
        study.laterality = metadata.get("laterality")
        
        await db.commit()
        
        # If async mode, queue job and return
        if async_mode:
            # TODO: Queue Celery task
            study.status = "queued"
            await db.commit()
            return AnalyzeResponse(
                study_id=study.id,
                status="queued",
                job_id=str(study.id)
            )
        
        # Synchronous analysis
        await audit_service.log_analysis_start(study.id, client_ip)
        
        # Call inference service
        inference_client = get_inference_client()
        inference_result = await inference_client.analyze_image(
            file_info["png_path"],
            detector_conf=app_settings.ai.detector_confidence,
            detector_iou=app_settings.ai.detector_iou,
            detector_max_boxes=app_settings.ai.detector_max_boxes,
            calibration_enabled=app_settings.ai.calibration_enabled
        )
        
        # Parse findings
        findings = inference_client.parse_findings(inference_result, app_settings.ai)
        bounding_boxes = inference_client.parse_bounding_boxes(inference_result)
        
        # Save findings to database
        for f in findings:
            finding = Finding(
                study_id=study.id,
                finding_name=f.finding_name,
                probability=f.probability,
                calibrated_probability=f.calibrated_probability,
                status=f.status,
                triage_threshold=f.triage_threshold,
                strong_threshold=f.strong_threshold
            )
            db.add(finding)
        
        # Save bounding boxes
        for b in bounding_boxes:
            box = BoundingBox(
                study_id=study.id,
                finding_name=b.finding_name,
                confidence=b.confidence,
                x_min=b.x_min,
                y_min=b.y_min,
                x_max=b.x_max,
                y_max=b.y_max,
                x_min_px=b.x_min_px,
                y_min_px=b.y_min_px,
                x_max_px=b.x_max_px,
                y_max_px=b.y_max_px
            )
            db.add(box)
        
        # Generate report
        report_generator = get_report_generator(app_settings.ai, app_settings.llm)
        report = await report_generator.generate_report(findings)
        triage_level, triage_reasons = report_generator.determine_triage(findings)
        
        # Update study
        study.status = "completed"
        study.triage_level = TriageLevel(triage_level)
        study.triage_reasons = triage_reasons
        study.report_findings = report.findings_text
        study.report_impression = report.impression_text
        study.report_llm_rewritten = report.llm_rewritten
        study.processed_at = datetime.utcnow()
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        study.processing_time_ms = processing_time_ms
        
        await db.commit()
        
        # Audit log
        await audit_service.log_analysis_complete(
            study.id, triage_level, processing_time_ms,
            len(findings), len(bounding_boxes), client_ip
        )
        
        # Update metrics
        ANALYSIS_COUNT.labels(triage_level=triage_level).inc()
        ANALYSIS_LATENCY.observe(processing_time_ms)
        
        # Build response
        result = AnalysisResult(
            study_id=study.id,
            status="completed",
            triage_level=triage_level,
            triage_reasons=triage_reasons,
            findings=findings,
            bounding_boxes=bounding_boxes,
            report=report,
            processing_time_ms=processing_time_ms,
            model_info=inference_result.get("model_info", {})
        )
        
        return AnalyzeResponse(
            study_id=study.id,
            status="completed",
            result=result
        )
        
    except ConnectionError as e:
        # Inference service not available
        study.status = "failed"
        study.error_message = f"Inference service unavailable: {str(e)}"
        await db.commit()
        
        await audit_service.log_analysis_error(study.id, str(e), client_ip)
        
        raise HTTPException(
            status_code=503, 
            detail=f"Inference service unavailable. Please ensure the inference service is running. Error: {str(e)}"
        )
    except FileNotFoundError as e:
        study.status = "failed"
        study.error_message = str(e)
        await db.commit()
        
        await audit_service.log_analysis_error(study.id, str(e), client_ip)
        
        raise HTTPException(status_code=500, detail=f"File processing error: {str(e)}")
    except Exception as e:
        import traceback
        error_detail = f"{type(e).__name__}: {str(e)}"
        print(f"Analysis error: {error_detail}")
        print(traceback.format_exc())
        
        study.status = "failed"
        study.error_message = error_detail
        await db.commit()
        
        await audit_service.log_analysis_error(study.id, error_detail, client_ip)
        
        raise HTTPException(status_code=500, detail=error_detail)


@app.get("/v1/cxr/result/{study_id}", response_model=AnalysisResult)
async def get_result(study_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get analysis result for a study."""
    result = await db.execute(select(Study).where(Study.id == study_id))
    study = result.scalar_one_or_none()
    
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    
    if study.status != "completed":
        return AnalysisResult(
            study_id=study.id,
            status=study.status
        )
    
    # Get findings
    findings_result = await db.execute(
        select(Finding).where(Finding.study_id == study_id)
    )
    findings = [
        FindingResult(
            finding_name=f.finding_name,
            probability=f.probability,
            calibrated_probability=f.calibrated_probability,
            status=f.status,
            triage_threshold=f.triage_threshold,
            strong_threshold=f.strong_threshold
        )
        for f in findings_result.scalars().all()
    ]
    
    # Get bounding boxes
    boxes_result = await db.execute(
        select(BoundingBox).where(BoundingBox.study_id == study_id)
    )
    bounding_boxes = [
        BoundingBoxResult(
            finding_name=b.finding_name,
            confidence=b.confidence,
            x_min=b.x_min,
            y_min=b.y_min,
            x_max=b.x_max,
            y_max=b.y_max,
            x_min_px=b.x_min_px,
            y_min_px=b.y_min_px,
            x_max_px=b.x_max_px,
            y_max_px=b.y_max_px
        )
        for b in boxes_result.scalars().all()
    ]
    
    report = ReportResult(
        findings_text=study.report_findings or "",
        impression_text=study.report_impression or "",
        llm_rewritten=study.report_llm_rewritten or False
    )
    
    return AnalysisResult(
        study_id=study.id,
        status=study.status,
        triage_level=study.triage_level.value if study.triage_level else None,
        triage_reasons=study.triage_reasons or [],
        findings=findings,
        bounding_boxes=bounding_boxes,
        report=report,
        processing_time_ms=study.processing_time_ms
    )


# ============== Worklist ==============

@app.get("/v1/worklist", response_model=WorklistResponse)
async def get_worklist(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    triage_level: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get worklist of studies."""
    query = select(Study)
    count_query = select(func.count()).select_from(Study)
    
    if triage_level:
        query = query.where(Study.triage_level == TriageLevel(triage_level))
        count_query = count_query.where(Study.triage_level == TriageLevel(triage_level))
    
    if status:
        query = query.where(Study.status == status)
        count_query = count_query.where(Study.status == status)
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    query = query.order_by(Study.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    studies = result.scalars().all()
    
    return WorklistResponse(
        studies=[
            StudySummary(
                id=s.id,
                accession_number=s.accession_number,
                patient_id=s.patient_id,
                study_date=s.study_date,
                view_position=s.view_position,
                triage_level=s.triage_level.value if s.triage_level else None,
                status=s.status,
                created_at=s.created_at,
                processing_time_ms=s.processing_time_ms
            )
            for s in studies
        ],
        total=total,
        page=page,
        page_size=page_size
    )


@app.get("/v1/study/{study_id}", response_model=StudyDetail)
async def get_study(study_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get detailed study information."""
    result = await db.execute(select(Study).where(Study.id == study_id))
    study = result.scalar_one_or_none()
    
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    
    # Get findings
    findings_result = await db.execute(
        select(Finding).where(Finding.study_id == study_id)
    )
    findings = [
        FindingResult(
            finding_name=f.finding_name,
            probability=f.probability,
            calibrated_probability=f.calibrated_probability,
            status=f.status,
            triage_threshold=f.triage_threshold,
            strong_threshold=f.strong_threshold
        )
        for f in findings_result.scalars().all()
    ]
    
    # Get bounding boxes
    boxes_result = await db.execute(
        select(BoundingBox).where(BoundingBox.study_id == study_id)
    )
    bounding_boxes = [
        BoundingBoxResult(
            finding_name=b.finding_name,
            confidence=b.confidence,
            x_min=b.x_min,
            y_min=b.y_min,
            x_max=b.x_max,
            y_max=b.y_max,
            x_min_px=b.x_min_px,
            y_min_px=b.y_min_px,
            x_max_px=b.x_max_px,
            y_max_px=b.y_max_px
        )
        for b in boxes_result.scalars().all()
    ]
    
    return StudyDetail(
        id=study.id,
        accession_number=study.accession_number,
        patient_id=study.patient_id,
        study_date=study.study_date,
        view_position=study.view_position,
        triage_level=study.triage_level.value if study.triage_level else None,
        status=study.status,
        created_at=study.created_at,
        processing_time_ms=study.processing_time_ms,
        original_filename=study.original_filename,
        file_type=study.file_type,
        triage_reasons=study.triage_reasons,
        report_findings=study.report_findings,
        report_impression=study.report_impression,
        findings=findings,
        bounding_boxes=bounding_boxes
    )


# ============== Settings ==============

@app.get("/v1/settings", response_model=SettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)):
    """Get application settings (admin only)."""
    app_settings = await load_app_settings(db)
    
    # Mask sensitive data
    response = SettingsResponse(
        database=app_settings.database,
        llm=app_settings.llm,
        ai=app_settings.ai
    )
    
    # Mask passwords and API keys
    response.database.password = "********" if response.database.password else ""
    if response.llm.azure_openai.api_key:
        response.llm.azure_openai.api_key = "********"
    if response.llm.claude.api_key:
        response.llm.claude.api_key = "********"
    if response.llm.gemini.api_key:
        response.llm.gemini.api_key = "********"
    
    return response


@app.put("/v1/settings", response_model=SettingsResponse)
async def update_settings(
    request: Request,
    update: SettingsUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update application settings (admin only)."""
    app_settings = await load_app_settings(db)
    
    # Update database settings
    if update.database:
        # Don't update password if it's masked
        if update.database.password != "********":
            app_settings.database = update.database
        else:
            # Keep existing password
            new_db = update.database.model_copy()
            new_db.password = app_settings.database.password
            app_settings.database = new_db
    
    # Update LLM settings
    if update.llm:
        # Handle masked API keys
        if update.llm.azure_openai.api_key == "********":
            update.llm.azure_openai.api_key = app_settings.llm.azure_openai.api_key
        if update.llm.claude.api_key == "********":
            update.llm.claude.api_key = app_settings.llm.claude.api_key
        if update.llm.gemini.api_key == "********":
            update.llm.gemini.api_key = app_settings.llm.gemini.api_key
        app_settings.llm = update.llm
    
    # Update AI settings
    if update.ai:
        app_settings.ai = update.ai
    
    # Save settings
    await save_app_settings(db, app_settings)
    
    # Audit log
    audit_service = get_audit_service(db)
    client_ip = request.client.host if request.client else None
    await audit_service.log_settings_change("settings_update", ip_address=client_ip)
    
    return await get_settings(db)


@app.post("/v1/settings/test-connection", response_model=TestConnectionResponse)
async def test_db_connection(config: TestConnectionRequest):
    """Test database connection with provided settings."""
    try:
        if config.db_type == "postgres":
            import asyncpg
            conn = await asyncpg.connect(
                host=config.host,
                port=config.port,
                user=config.user,
                password=config.password,
                database=config.dbname,
                ssl=config.ssl_mode
            )
            await conn.execute("SELECT 1")
            await conn.close()
        else:
            # SQLite - just check if we can create the file
            import aiosqlite
            async with aiosqlite.connect(f"./data/{config.dbname}.db") as db:
                await db.execute("SELECT 1")
        
        return TestConnectionResponse(success=True, message="Connection successful")
    except Exception as e:
        return TestConnectionResponse(success=False, message=str(e))


# ============== Audit & QA ==============

@app.get("/v1/audit", response_model=AuditLogResponse)
async def get_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    action: Optional[str] = None,
    study_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get audit logs."""
    audit_service = get_audit_service(db)
    logs, total = await audit_service.get_logs(page, page_size, action, study_id)
    
    return AuditLogResponse(
        logs=[
            AuditLogEntry(
                id=log.id,
                study_id=log.study_id,
                action=log.action,
                actor=log.actor,
                details=log.details,
                ip_address=log.ip_address,
                created_at=log.created_at
            )
            for log in logs
        ],
        total=total,
        page=page,
        page_size=page_size
    )


@app.post("/v1/qa/review", response_model=QAReviewResponse)
async def create_qa_review(
    review: QAReviewCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a QA review for a study."""
    qa_review = QAReview(
        study_id=review.study_id,
        review_type=review.review_type,
        finding_name=review.finding_name,
        reviewer=review.reviewer,
        notes=review.notes
    )
    db.add(qa_review)
    await db.commit()
    await db.refresh(qa_review)
    
    return QAReviewResponse(
        id=qa_review.id,
        study_id=qa_review.study_id,
        review_type=qa_review.review_type,
        finding_name=qa_review.finding_name,
        reviewer=qa_review.reviewer,
        notes=qa_review.notes,
        created_at=qa_review.created_at
    )


@app.get("/v1/metrics/dashboard", response_model=DashboardMetrics)
async def get_dashboard_metrics(db: AsyncSession = Depends(get_db)):
    """Get dashboard metrics."""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    
    # Studies today
    today_result = await db.execute(
        select(func.count()).select_from(Study).where(Study.created_at >= today_start)
    )
    studies_today = today_result.scalar()
    
    # Studies this week
    week_result = await db.execute(
        select(func.count()).select_from(Study).where(Study.created_at >= week_start)
    )
    studies_this_week = week_result.scalar()
    
    # Triage distribution
    triage_result = await db.execute(
        select(Study.triage_level, func.count()).group_by(Study.triage_level)
    )
    triage_counts = {row[0]: row[1] for row in triage_result.all()}
    
    # Latency metrics (last 24 hours)
    latency_result = await db.execute(
        select(Study.processing_time_ms)
        .where(and_(
            Study.created_at >= now - timedelta(hours=24),
            Study.processing_time_ms.isnot(None)
        ))
    )
    latencies = [row[0] for row in latency_result.all()]
    
    if latencies:
        import numpy as np
        latencies_arr = np.array(latencies)
        avg_latency = float(np.mean(latencies_arr))
        p50_latency = float(np.percentile(latencies_arr, 50))
        p95_latency = float(np.percentile(latencies_arr, 95))
        p99_latency = float(np.percentile(latencies_arr, 99))
    else:
        avg_latency = p50_latency = p95_latency = p99_latency = 0.0
    
    return DashboardMetrics(
        latency=LatencyMetrics(
            avg_processing_time_ms=avg_latency,
            p50_processing_time_ms=p50_latency,
            p95_processing_time_ms=p95_latency,
            p99_processing_time_ms=p99_latency,
            total_studies=len(latencies),
            period_hours=24
        ),
        triage_distribution=TriageDistribution(
            normal=triage_counts.get(TriageLevel.NORMAL, 0),
            routine=triage_counts.get(TriageLevel.ROUTINE, 0),
            urgent=triage_counts.get(TriageLevel.URGENT, 0),
            total=sum(triage_counts.values())
        ),
        studies_today=studies_today,
        studies_this_week=studies_this_week
    )


# ============== Export ==============

@app.get("/v1/study/{study_id}/export/{format}")
async def export_study(
    request: Request,
    study_id: UUID,
    format: str,
    db: AsyncSession = Depends(get_db)
):
    """Export study results in various formats."""
    result = await db.execute(select(Study).where(Study.id == study_id))
    study = result.scalar_one_or_none()
    
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    
    # Audit log
    audit_service = get_audit_service(db)
    client_ip = request.client.host if request.client else None
    await audit_service.log_export(study_id, format, client_ip)
    
    if format == "json":
        # Get full result
        analysis_result = await get_result(study_id, db)
        return JSONResponse(
            content=analysis_result.model_dump(mode="json"),
            headers={"Content-Disposition": f"attachment; filename=result_{study_id}.json"}
        )
    
    elif format == "png":
        # Return annotated PNG
        if study.file_path and os.path.exists(study.file_path):
            return FileResponse(
                study.file_path,
                media_type="image/png",
                filename=f"cxr_{study_id}.png"
            )
        raise HTTPException(status_code=404, detail="Image not found")
    
    elif format == "dicom_sr":
        # Generate DICOM SR
        dicom_service = get_dicom_service()
        
        # Get original DICOM if available
        study_dir = os.path.dirname(study.file_path) if study.file_path else None
        original_dcm_path = os.path.join(study_dir, "original.dcm") if study_dir else None
        
        if original_dcm_path and os.path.exists(original_dcm_path):
            import pydicom
            original_ds = pydicom.dcmread(original_dcm_path)
        else:
            original_ds = pydicom.Dataset()
        
        # Get findings
        findings_result = await db.execute(
            select(Finding).where(Finding.study_id == study_id)
        )
        findings = findings_result.scalars().all()
        
        report_text = f"FINDINGS:\n{study.report_findings}\n\nIMPRESSION:\n{study.report_impression}"
        
        sr_bytes = dicom_service.create_dicom_sr(
            original_ds,
            findings,
            study.triage_level.value if study.triage_level else "UNKNOWN",
            report_text
        )
        
        return Response(
            content=sr_bytes,
            media_type="application/dicom",
            headers={"Content-Disposition": f"attachment; filename=sr_{study_id}.dcm"}
        )
    
    raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")


# ============== Image Serving ==============

@app.get("/v1/study/{study_id}/image")
async def get_study_image(study_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get study image."""
    result = await db.execute(select(Study).where(Study.id == study_id))
    study = result.scalar_one_or_none()
    
    if not study or not study.file_path:
        raise HTTPException(status_code=404, detail="Image not found")
    
    if not os.path.exists(study.file_path):
        raise HTTPException(status_code=404, detail="Image file not found")
    
    return FileResponse(study.file_path, media_type="image/png")


@app.get("/v1/study/{study_id}/dicom")
async def get_study_dicom(study_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get original DICOM file."""
    result = await db.execute(select(Study).where(Study.id == study_id))
    study = result.scalar_one_or_none()
    
    if not study or not study.file_path:
        raise HTTPException(status_code=404, detail="Study not found")
    
    study_dir = os.path.dirname(study.file_path)
    dicom_path = os.path.join(study_dir, "original.dcm")
    
    if not os.path.exists(dicom_path):
        raise HTTPException(status_code=404, detail="DICOM file not found")
    
    return FileResponse(dicom_path, media_type="application/dicom")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
