"""
Monitoring API for platform module.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.platform.data.repositories.platform_client_repository import PlatformClientRepository
from app.platform.data.repositories.platform_diet_plan_repository import PlatformDietPlanRepository
from app.platform.data.repositories.platform_monitoring_record_repository import PlatformMonitoringRecordRepository

router = APIRouter(prefix="/monitoring", tags=["Platform Monitoring"])


ALLOWED_METRIC_TYPES = {"weight", "lab", "adherence", "symptom", "vitals"}


class MonitoringRecordCreate(BaseModel):
    client_id: UUID
    plan_id: UUID
    metric_type: str = Field(description="weight | lab | adherence | symptom | vitals")
    metric_value: Dict[str, Any]
    recorded_at: Optional[datetime] = None


class MonitoringRecordResponse(BaseModel):
    id: UUID
    client_id: UUID
    plan_id: UUID
    metric_type: str
    metric_value: Dict[str, Any]
    recorded_at: datetime
    reassess_recommended: Optional[bool] = None


def _validate_metric_type(metric_type: str):
    if metric_type not in ALLOWED_METRIC_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"metric_type must be one of {sorted(ALLOWED_METRIC_TYPES)}"
        )


def _compute_reassess_flag(metric_type: str, metric_value: Dict[str, Any]) -> bool:
    """
    Simple heuristic for reassessment recommendation.
    Deterministic, no AI: if lab/symptom/vitals indicate deterioration.
    """
    metric_type = metric_type.lower()
    if metric_type in {"lab", "vitals"}:
        # crude checks: high blood pressure or high glucose markers
        systolic = metric_value.get("bp_systolic") or metric_value.get("systolic")
        diastolic = metric_value.get("bp_diastolic") or metric_value.get("diastolic")
        hba1c = metric_value.get("hba1c") or metric_value.get("HbA1c")
        if (systolic and systolic >= 150) or (diastolic and diastolic >= 95):
            return True
        if hba1c and float(hba1c) >= 8.0:
            return True
    if metric_type == "symptom":
        severity = metric_value.get("severity")
        if isinstance(severity, (int, float)) and severity >= 7:
            return True
    return False


@router.post("", response_model=MonitoringRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_monitoring_record(
    record: MonitoringRecordCreate,
    db: Session = Depends(get_db)
):
    _validate_metric_type(record.metric_type)

    client_repo = PlatformClientRepository(db)
    if client_repo.get_by_id(record.client_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    plan_repo = PlatformDietPlanRepository(db)
    plan = plan_repo.get_by_id(record.plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    if plan.client_id != record.client_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Plan does not belong to client")

    repo = PlatformMonitoringRecordRepository(db)
    payload = record.dict()
    if payload.get("recorded_at") is None:
        payload["recorded_at"] = datetime.utcnow()
    created = repo.create(payload)

    reassess = _compute_reassess_flag(created.metric_type, created.metric_value or {})

    return MonitoringRecordResponse(
        id=created.id,
        client_id=created.client_id,
        plan_id=created.plan_id,
        metric_type=created.metric_type,
        metric_value=created.metric_value,
        recorded_at=created.recorded_at,
        reassess_recommended=reassess,
    )


def _filter_records(records, metric_type: Optional[str], start: Optional[datetime], end: Optional[datetime]):
    results = records
    if metric_type:
        _validate_metric_type(metric_type)
        results = [r for r in results if r.metric_type == metric_type]
    if start:
        results = [r for r in results if r.recorded_at >= start]
    if end:
        results = [r for r in results if r.recorded_at <= end]
    return results


def _to_response(rec) -> MonitoringRecordResponse:
    reassess = _compute_reassess_flag(rec.metric_type, rec.metric_value or {})
    return MonitoringRecordResponse(
        id=rec.id,
        client_id=rec.client_id,
        plan_id=rec.plan_id,
        metric_type=rec.metric_type,
        metric_value=rec.metric_value,
        recorded_at=rec.recorded_at,
        reassess_recommended=reassess,
    )


@router.get("/plan/{plan_id}", response_model=List[MonitoringRecordResponse])
async def get_records_for_plan(
    plan_id: UUID,
    metric_type: Optional[str] = Query(None),
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    db: Session = Depends(get_db)
):
    plan_repo = PlatformDietPlanRepository(db)
    plan = plan_repo.get_by_id(plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    repo = PlatformMonitoringRecordRepository(db)
    records = repo.get_by_plan_id(plan_id)
    filtered = _filter_records(records, metric_type, start, end)
    return [_to_response(r) for r in filtered]


@router.get("/client/{client_id}", response_model=List[MonitoringRecordResponse])
async def get_records_for_client(
    client_id: UUID,
    metric_type: Optional[str] = Query(None),
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    db: Session = Depends(get_db)
):
    client_repo = PlatformClientRepository(db)
    if client_repo.get_by_id(client_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    repo = PlatformMonitoringRecordRepository(db)
    records = repo.get_by_client_id(client_id)
    filtered = _filter_records(records, metric_type, start, end)
    return [_to_response(r) for r in filtered]


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_record(
    record_id: UUID,
    db: Session = Depends(get_db)
):
    repo = PlatformMonitoringRecordRepository(db)
    deleted = repo.delete(record_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    return

