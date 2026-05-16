from fastapi import APIRouter

try:
    from app.schemas.models import EnquiryCreate, KycCreate, PurchaseCreate, TrackingResponse
    from app.services.data_service import data_service
except ModuleNotFoundError:
    from schemas.models import EnquiryCreate, KycCreate, PurchaseCreate, TrackingResponse
    from services.data_service import data_service

router = APIRouter()


@router.get("/policies")
def get_policies() -> dict:
    return {"items": [policy.model_dump() for policy in data_service.list_policies()]}


@router.post("/enquiries", response_model=TrackingResponse)
def create_enquiry(payload: EnquiryCreate) -> TrackingResponse:
    result = data_service.create_enquiry(payload)
    return TrackingResponse(
        tracking_id=result["tracking_id"],
        status=result["status"],
        message="Enquiry submitted successfully.",
    )


@router.post("/purchases", response_model=TrackingResponse)
def create_purchase(payload: PurchaseCreate) -> TrackingResponse:
    result = data_service.create_purchase(payload)
    cashback = result.get("cashback", 0)
    return TrackingResponse(
        tracking_id=result["tracking_id"],
        status=result["status"],
        message=f"Purchase simulated successfully. Cashback: INR {cashback}",
    )


@router.post("/kyc", response_model=TrackingResponse)
def create_kyc(payload: KycCreate) -> TrackingResponse:
    result = data_service.submit_kyc(payload)
    return TrackingResponse(
        tracking_id=result["tracking_id"],
        status=result["status"],
        message="KYC submitted successfully.",
    )
