from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


PolicyType = Literal["motor", "health"]
FlowType = Literal["new", "renewal"]


class Policy(BaseModel):
    id: str
    name: str
    policy_type: PolicyType
    flow_supported: list[FlowType]
    description: str


class EnquiryCreate(BaseModel):
    full_name: str = Field(min_length=2)
    email: EmailStr
    phone_number: str = Field(min_length=8, max_length=20)
    policy_type: PolicyType
    flow_type: FlowType


class PurchaseCreate(EnquiryCreate):
    policy_id: str


class KycCreate(BaseModel):
    full_name: str = Field(min_length=2)
    aadhaar_number: str = Field(min_length=12, max_length=12)
    pan_number: str = Field(min_length=10, max_length=10)
    email: EmailStr
    phone_number: str = Field(min_length=8, max_length=20)
    nominee_name: str = Field(min_length=2)
    nominee_age: int = Field(ge=0, le=120)
    previous_year_policy_copy_url: Optional[str] = None
    rc_copy_url: Optional[str] = None
    flow_type: FlowType
    policy_type: PolicyType


class TrackingResponse(BaseModel):
    tracking_id: str
    status: str
    message: str


class StatusResponse(BaseModel):
    tracking_id: str
    status: str
    category: str
    summary: str
    updated_at: datetime
    metadata: dict


CashbackActionType = Literal["invest", "redeem"]
RedeemChannel = Literal["bank", "amazon", "flipkart", "swiggy", "blinkit", "kfc"]
InvestmentSource = Literal["wallet", "bank", "upi"]


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=3, max_length=120)


class LoginResponse(BaseModel):
    session_id: str
    username: str
    access_token: str
    token_type: str
    message: str


class LogoutRequest(BaseModel):
    session_id: str
    username: str = Field(min_length=3, max_length=80)


class LogoutResponse(BaseModel):
    status: str
    message: str


class JourneyEnquiryCreate(BaseModel):
    session_id: str
    username: str = Field(min_length=3, max_length=80)
    full_name: str = Field(min_length=2)
    email: EmailStr
    phone_number: str = Field(min_length=8, max_length=20)
    policy_type: PolicyType
    flow_type: FlowType


class JourneyKycCreate(BaseModel):
    session_id: str
    username: str = Field(min_length=3, max_length=80)
    full_name: str = Field(min_length=2)
    aadhaar_number: str = Field(min_length=12, max_length=12)
    pan_number: str = Field(min_length=10, max_length=10)
    email: EmailStr
    phone_number: str = Field(min_length=8, max_length=20)
    nominee_name: str = Field(min_length=2)
    nominee_age: int = Field(ge=0, le=120)
    previous_year_policy_copy_url: Optional[str] = None
    rc_copy_url: Optional[str] = None
    flow_type: FlowType
    policy_type: PolicyType


class QuoteCreate(BaseModel):
    session_id: str
    username: str = Field(min_length=3, max_length=80)
    policy_id: str
    policy_type: PolicyType
    flow_type: FlowType
    insured_amount: int = Field(ge=10000, le=5000000)
    tenure_years: int = Field(ge=1, le=5)


class CashbackActionCreate(BaseModel):
    session_id: str
    username: str = Field(min_length=3, max_length=80)
    quote_id: str
    cashback_amount: int = Field(ge=0)
    action: CashbackActionType


class JourneyStepResponse(BaseModel):
    reference_id: str
    status: str
    message: str


class QuoteResponse(BaseModel):
    quote_id: str
    premium_amount: int
    cashback_amount: int
    message: str


class CashbackActionResponse(BaseModel):
    action_id: str
    action: CashbackActionType
    status: str
    cashback_amount: int
    projected_value: Optional[float] = None
    message: str


class DashboardResponse(BaseModel):
    session_id: str
    username: str
    new_policies: int
    renewal_policies: int
    total_quotes: int
    invested_amount: int
    redeemed_amount: int
    projected_returns: float
    current_cashback_balance: int
    storage_backends: list[str]


class PaymentCreate(BaseModel):
    session_id: str
    username: str = Field(min_length=3, max_length=80)
    quote_id: str
    policy_id: str
    policy_type: PolicyType
    agree_tnc: bool


class PaymentResponse(BaseModel):
    payment_id: str
    cashback_id: str
    status: str
    cashback_amount: int
    message: str


class CashbackPendingItem(BaseModel):
    cashback_id: str
    quote_id: str
    policy_id: str
    policy_type: PolicyType
    cashback_amount: int
    status: str
    created_at: datetime


class CashbackPendingResponse(BaseModel):
    items: list[CashbackPendingItem]
    page: int = 1
    page_size: int = 20
    total: int = 0
    has_next: bool = False


class CashbackClaimCreate(BaseModel):
    session_id: str
    username: str = Field(min_length=3, max_length=80)
    cashback_id: str


class CashbackClaimResponse(BaseModel):
    cashback_id: str
    status: str
    wallet_balance: int
    message: str


class PolicyHistoryItem(BaseModel):
    quote_id: str
    policy_id: str
    policy_type: PolicyType
    flow_type: FlowType
    premium_amount: int
    cashback_amount: int
    payment_status: str
    created_at: datetime


class PolicyHistoryResponse(BaseModel):
    items: list[PolicyHistoryItem]
    page: int = 1
    page_size: int = 20
    total: int = 0
    has_next: bool = False


class WalletSummaryResponse(BaseModel):
    available_balance: int
    total_credited: int
    total_redeemed: int
    total_invested_from_wallet: int


class WalletTransactionItem(BaseModel):
    entry_id: str
    entry_type: str
    source: str
    endpoint: str
    method: str
    amount: int
    note: str
    created_at: datetime


class WalletTransactionResponse(BaseModel):
    items: list[WalletTransactionItem]
    page: int = 1
    page_size: int = 20
    total: int = 0
    has_next: bool = False


class WalletRedeemCreate(BaseModel):
    session_id: str
    username: str = Field(min_length=3, max_length=80)
    amount: int = Field(gt=0)
    channel: RedeemChannel


class WalletRedeemResponse(BaseModel):
    redeem_id: str
    status: str
    channel: RedeemChannel
    amount: int
    available_balance: int
    message: str


class InvestmentCreate(BaseModel):
    session_id: str
    username: str = Field(min_length=3, max_length=80)
    amount: int = Field(gt=0)
    source: InvestmentSource


class InvestmentResponse(BaseModel):
    investment_id: str
    status: str
    source: InvestmentSource
    amount: int
    message: str


class InvestmentProjectionPoint(BaseModel):
    year: int
    value: float


class InvestmentProjectionResponse(BaseModel):
    principal: int
    annual_rate: float
    points: list[InvestmentProjectionPoint]


class InvestmentHistoryItem(BaseModel):
    investment_id: str
    source: InvestmentSource
    status: str
    amount: int
    annual_rate: float
    current_value: float
    returns: float
    created_at: datetime


class InvestmentHistoryResponse(BaseModel):
    items: list[InvestmentHistoryItem]
    page: int = 1
    page_size: int = 20
    total: int = 0
    has_next: bool = False
