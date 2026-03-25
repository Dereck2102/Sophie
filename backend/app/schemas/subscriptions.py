from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field

from app.infrastructure.models.subscriptions import (
    BillingCycleEnum,
    CustomOrderStatusEnum,
    GatewayProviderEnum,
    PaymentStatusEnum,
    PlanTierEnum,
    SubscriptionStatusEnum,
)


class PlanPresetOut(BaseModel):
    plan: PlanTierEnum
    name: str
    description: str
    monthly_price_usd: Decimal | None
    yearly_price_usd: Decimal | None
    features: list[str]


class CheckoutRequest(BaseModel):
    plan: PlanTierEnum
    billing_cycle: BillingCycleEnum = BillingCycleEnum.MONTHLY
    id_empresa: int | None = None
    id_usuario_owner: int | None = None
    customer_name: str | None = None
    customer_email: EmailStr | None = None
    custom_requirements: str | None = None


class CheckoutResponse(BaseModel):
    id_pago: int
    provider: str
    status: PaymentStatusEnum
    amount: Decimal
    currency: str
    checkout_url: str | None
    detail: str


class PaymentGatewayConfigUpsert(BaseModel):
    provider: GatewayProviderEnum
    enabled: bool = False
    public_key: str | None = None
    secret: str | None = None
    endpoint_url: str | None = None
    store_id: str | None = None
    return_url: str | None = None
    cancel_url: str | None = None
    webhook_token: str | None = None


class PaymentGatewayConfigOut(BaseModel):
    provider: GatewayProviderEnum
    enabled: bool
    public_key: str | None
    has_secret: bool
    endpoint_url: str | None = None
    store_id: str | None = None
    return_url: str | None = None
    cancel_url: str | None = None
    has_webhook_token: bool = False
    updated_by_user_id: int | None = None
    updated_at: datetime | None = None


class EmpresaSubscriptionUpsert(BaseModel):
    plan_tier: PlanTierEnum
    billing_cycle: BillingCycleEnum = BillingCycleEnum.MONTHLY
    status: SubscriptionStatusEnum = SubscriptionStatusEnum.ACTIVE
    custom_notes: str | None = None
    feature_overrides: list[str] = Field(default_factory=list)


class EmpresaSubscriptionOut(BaseModel):
    id_empresa: int
    empresa_nombre: str
    plan_tier: PlanTierEnum
    billing_cycle: BillingCycleEnum
    status: SubscriptionStatusEnum
    price_usd: Decimal
    currency: str
    features: list[str]
    custom_notes: str | None = None
    updated_by_user_id: int | None = None
    updated_at: datetime | None = None


class UserSubscriptionUpsert(BaseModel):
    plan_tier: PlanTierEnum
    billing_cycle: BillingCycleEnum = BillingCycleEnum.MONTHLY
    status: SubscriptionStatusEnum = SubscriptionStatusEnum.ACTIVE
    custom_notes: str | None = None
    feature_overrides: list[str] = Field(default_factory=list)


class UserSubscriptionOut(BaseModel):
    id_usuario: int
    username: str
    email: str
    plan_tier: PlanTierEnum
    billing_cycle: BillingCycleEnum
    status: SubscriptionStatusEnum
    price_usd: Decimal
    currency: str
    features: list[str]
    custom_notes: str | None = None
    updated_by_user_id: int | None = None
    updated_at: datetime | None = None


class PaymentTransactionOut(BaseModel):
    id_pago: int
    id_empresa: int | None
    id_usuario_owner: int | None
    plan_tier: PlanTierEnum
    billing_cycle: BillingCycleEnum
    amount: Decimal
    currency: str
    provider: str
    provider_reference: str | None
    checkout_url: str | None
    status: PaymentStatusEnum
    customer_name: str | None
    customer_email: str | None
    created_at: datetime
    paid_at: datetime | None

    model_config = {"from_attributes": True}


class PayPhoneWebhookIn(BaseModel):
    transaction_id: str | None = None
    client_transaction_id: str | None = None
    status: str
    amount: Decimal | None = None
    currency: str | None = None


class PayPhoneWebhookOut(BaseModel):
    detail: str
    payment_id: int | None = None
    auto_activated: bool = False


class CustomOrderCreate(BaseModel):
    id_empresa: int
    billing_cycle: BillingCycleEnum = BillingCycleEnum.MONTHLY
    amount_usd: Decimal = Field(gt=0)
    custom_requirements: str
    feature_overrides: list[str] = Field(default_factory=list)
    generate_payphone_checkout: bool = False


class CustomOrderOut(BaseModel):
    id_pago: int
    order_number: str
    status: PaymentStatusEnum
    amount: Decimal
    currency: str
    checkout_url: str | None
    detail: str


class ActivateCustomOrderOut(BaseModel):
    """Response when activating a custom order"""
    id_pago: int
    id_empresa: int
    plan_tier: PlanTierEnum
    status: SubscriptionStatusEnum
    features: list[str]
    detail: str = "Orden de cobro personalizada activada exitosamente"


class PendingCustomOrderOut(BaseModel):
    id_order: int
    order_number: str
    id_pago: int | None
    id_empresa: int
    empresa_nombre: str
    billing_cycle: BillingCycleEnum
    amount: Decimal
    currency: str
    status: CustomOrderStatusEnum
    created_at: datetime
