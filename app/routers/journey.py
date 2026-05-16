from fastapi import APIRouter, HTTPException, Query

try:
    from app.schemas.models import (
        CashbackActionCreate,
        CashbackActionResponse,
        CashbackClaimCreate,
        CashbackClaimResponse,
        CashbackPendingResponse,
        DashboardResponse,
        InvestmentCreate,
        InvestmentHistoryResponse,
        InvestmentProjectionResponse,
        InvestmentResponse,
        JourneyEnquiryCreate,
        JourneyKycCreate,
        JourneyStepResponse,
        LoginRequest,
        LoginResponse,
        LogoutRequest,
        LogoutResponse,
        PaymentCreate,
        PaymentResponse,
        PolicyHistoryResponse,
        QuoteCreate,
        QuoteResponse,
        WalletRedeemCreate,
        WalletRedeemResponse,
        WalletSummaryResponse,
        WalletTransactionResponse,
    )
    from app.services.data_service import data_service
except ModuleNotFoundError:
    from schemas.models import (
        CashbackActionCreate,
        CashbackActionResponse,
        CashbackClaimCreate,
        CashbackClaimResponse,
        CashbackPendingResponse,
        DashboardResponse,
        InvestmentCreate,
        InvestmentHistoryResponse,
        InvestmentProjectionResponse,
        InvestmentResponse,
        JourneyEnquiryCreate,
        JourneyKycCreate,
        JourneyStepResponse,
        LoginRequest,
        LoginResponse,
        LogoutRequest,
        LogoutResponse,
        PaymentCreate,
        PaymentResponse,
        PolicyHistoryResponse,
        QuoteCreate,
        QuoteResponse,
        WalletRedeemCreate,
        WalletRedeemResponse,
        WalletSummaryResponse,
        WalletTransactionResponse,
    )
    from services.data_service import data_service

router = APIRouter()


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    try:
        result = data_service.create_login_session(payload.username, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return LoginResponse(**result)


@router.post("/auth/logout", response_model=LogoutResponse)
def logout(payload: LogoutRequest) -> LogoutResponse:
    try:
        result = data_service.logout_session(payload.session_id, payload.username)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return LogoutResponse(**result)


@router.post("/journey/enquiry", response_model=JourneyStepResponse)
def journey_enquiry(payload: JourneyEnquiryCreate) -> JourneyStepResponse:
    result = data_service.create_journey_enquiry(payload)
    return JourneyStepResponse(**result)


@router.post("/journey/kyc", response_model=JourneyStepResponse)
def journey_kyc(payload: JourneyKycCreate) -> JourneyStepResponse:
    result = data_service.create_journey_kyc(payload)
    return JourneyStepResponse(**result)


@router.post("/journey/quote", response_model=QuoteResponse)
def journey_quote(payload: QuoteCreate) -> QuoteResponse:
    result = data_service.create_quote(payload)
    return QuoteResponse(**result)


@router.post("/journey/cashback", response_model=CashbackActionResponse)
def journey_cashback(payload: CashbackActionCreate) -> CashbackActionResponse:
    result = data_service.apply_cashback_action(payload)
    return CashbackActionResponse(**result)


@router.get("/journey/dashboard/{session_id}", response_model=DashboardResponse)
def journey_dashboard(session_id: str, username: str = Query(..., min_length=3)) -> DashboardResponse:
    try:
        result = data_service.get_dashboard(session_id, username)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return DashboardResponse(**result)


@router.post("/journey/payment", response_model=PaymentResponse)
def journey_payment(payload: PaymentCreate) -> PaymentResponse:
    try:
        result = data_service.create_payment(
            payload.session_id,
            payload.username,
            payload.quote_id,
            payload.policy_id,
            payload.policy_type,
            payload.agree_tnc,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PaymentResponse(**result)


@router.get("/journey/cashback/pending/{session_id}", response_model=CashbackPendingResponse)
def pending_cashback(
    session_id: str,
    username: str = Query(..., min_length=3),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
) -> CashbackPendingResponse:
    try:
        result = data_service.list_pending_cashback(session_id, username, page, page_size, start_date, end_date)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return CashbackPendingResponse(**result)


@router.get("/journey/cashback/{session_id}", response_model=CashbackPendingResponse)
def cashback_by_status(
    session_id: str,
    username: str = Query(..., min_length=3),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
) -> CashbackPendingResponse:
    try:
        result = data_service.list_cashback(session_id, username, status, page, page_size, start_date, end_date)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return CashbackPendingResponse(**result)


@router.post("/journey/cashback/claim", response_model=CashbackClaimResponse)
def claim_cashback(payload: CashbackClaimCreate) -> CashbackClaimResponse:
    try:
        result = data_service.claim_cashback_to_wallet(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CashbackClaimResponse(**result)


@router.get("/journey/history/{session_id}", response_model=PolicyHistoryResponse)
def policy_history(
    session_id: str,
    username: str = Query(..., min_length=3),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
) -> PolicyHistoryResponse:
    try:
        result = data_service.get_policy_history(session_id, username, page, page_size, start_date, end_date)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return PolicyHistoryResponse(**result)


@router.get("/journey/wallet/{session_id}", response_model=WalletSummaryResponse)
def wallet_summary(session_id: str, username: str = Query(..., min_length=3)) -> WalletSummaryResponse:
    try:
        result = data_service.get_wallet_summary(session_id, username)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return WalletSummaryResponse(**result)


@router.get("/journey/wallet/transactions/{session_id}", response_model=WalletTransactionResponse)
def wallet_transactions(
    session_id: str,
    username: str = Query(..., min_length=3),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
) -> WalletTransactionResponse:
    try:
        result = data_service.get_wallet_transactions(session_id, username, page, page_size, start_date, end_date)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return WalletTransactionResponse(**result)


@router.post("/journey/wallet/redeem", response_model=WalletRedeemResponse)
def redeem_wallet(payload: WalletRedeemCreate) -> WalletRedeemResponse:
    try:
        result = data_service.redeem_wallet(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return WalletRedeemResponse(**result)


@router.post("/journey/invest", response_model=InvestmentResponse)
def invest(payload: InvestmentCreate) -> InvestmentResponse:
    try:
        result = data_service.create_investment(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return InvestmentResponse(**result)


@router.get("/journey/invest/projection/{session_id}", response_model=InvestmentProjectionResponse)
def invest_projection(session_id: str, username: str = Query(..., min_length=3)) -> InvestmentProjectionResponse:
    try:
        result = data_service.investment_projection(session_id, username)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return InvestmentProjectionResponse(**result)


@router.get("/journey/invest/history/{session_id}", response_model=InvestmentHistoryResponse)
def investment_history(
    session_id: str,
    username: str = Query(..., min_length=3),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
) -> InvestmentHistoryResponse:
    try:
        result = data_service.list_investments(session_id, username, page, page_size, start_date, end_date)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return InvestmentHistoryResponse(**result)
