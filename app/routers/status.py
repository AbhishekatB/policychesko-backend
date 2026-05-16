from fastapi import APIRouter, HTTPException

try:
    from app.schemas.models import StatusResponse
    from app.services.data_service import data_service
except ModuleNotFoundError:
    from schemas.models import StatusResponse
    from services.data_service import data_service

router = APIRouter()


@router.get("/status/{tracking_id}", response_model=StatusResponse)
def get_status(tracking_id: str) -> StatusResponse:
    data = data_service.get_status(tracking_id)
    if not data:
        raise HTTPException(status_code=404, detail="Tracking ID not found")
    return StatusResponse(**data)
