"""
Audit logging service for tracking all operations.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models import AuditLog


class AuditService:
    """Service for audit logging."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def log(
        self,
        action: str,
        study_id: Optional[UUID] = None,
        actor: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> AuditLog:
        """Create an audit log entry."""
        log_entry = AuditLog(
            action=action,
            study_id=study_id,
            actor=actor or "system",
            details=details,
            ip_address=ip_address,
        )
        self.db.add(log_entry)
        await self.db.commit()
        await self.db.refresh(log_entry)
        return log_entry
    
    async def log_study_upload(
        self,
        study_id: UUID,
        filename: str,
        file_type: str,
        ip_address: Optional[str] = None
    ):
        """Log study upload event."""
        await self.log(
            action="study_upload",
            study_id=study_id,
            details={"filename": filename, "file_type": file_type},
            ip_address=ip_address
        )
    
    async def log_analysis_start(
        self,
        study_id: UUID,
        ip_address: Optional[str] = None
    ):
        """Log analysis start event."""
        await self.log(
            action="analysis_start",
            study_id=study_id,
            ip_address=ip_address
        )
    
    async def log_analysis_complete(
        self,
        study_id: UUID,
        triage_level: str,
        processing_time_ms: int,
        findings_count: int,
        boxes_count: int,
        ip_address: Optional[str] = None
    ):
        """Log analysis completion event."""
        await self.log(
            action="analysis_complete",
            study_id=study_id,
            details={
                "triage_level": triage_level,
                "processing_time_ms": processing_time_ms,
                "findings_count": findings_count,
                "boxes_count": boxes_count
            },
            ip_address=ip_address
        )
    
    async def log_analysis_error(
        self,
        study_id: UUID,
        error: str,
        ip_address: Optional[str] = None
    ):
        """Log analysis error event."""
        await self.log(
            action="analysis_error",
            study_id=study_id,
            details={"error": error},
            ip_address=ip_address
        )
    
    async def log_settings_change(
        self,
        setting_type: str,
        actor: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """Log settings change event."""
        await self.log(
            action="settings_change",
            actor=actor,
            details={"setting_type": setting_type},
            ip_address=ip_address
        )
    
    async def log_export(
        self,
        study_id: UUID,
        export_format: str,
        ip_address: Optional[str] = None
    ):
        """Log export event."""
        await self.log(
            action="export",
            study_id=study_id,
            details={"format": export_format},
            ip_address=ip_address
        )
    
    async def get_logs(
        self,
        page: int = 1,
        page_size: int = 50,
        action_filter: Optional[str] = None,
        study_id_filter: Optional[UUID] = None
    ):
        """Get paginated audit logs."""
        query = select(AuditLog)
        
        if action_filter:
            query = query.where(AuditLog.action == action_filter)
        if study_id_filter:
            query = query.where(AuditLog.study_id == study_id_filter)
        
        # Count total
        count_query = select(func.count()).select_from(AuditLog)
        if action_filter:
            count_query = count_query.where(AuditLog.action == action_filter)
        if study_id_filter:
            count_query = count_query.where(AuditLog.study_id == study_id_filter)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Get paginated results
        query = query.order_by(AuditLog.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        logs = result.scalars().all()
        
        return logs, total


def get_audit_service(db: AsyncSession) -> AuditService:
    """Factory function to create audit service."""
    return AuditService(db)
