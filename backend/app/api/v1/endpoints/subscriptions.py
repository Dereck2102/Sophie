from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_superadmin
from app.core.database import get_db
from app.infrastructure.models.subscriptions import GatewayProviderEnum
from app.infrastructure.models.usuario import Usuario
from app.schemas.subscriptions import (
    ActivateCustomOrderOut,
    CheckoutRequest,
    CheckoutResponse,
    CustomOrderCreate,
    CustomOrderOut,
    EmpresaSubscriptionOut,
    EmpresaSubscriptionUpsert,
    PayPhoneWebhookIn,
    PayPhoneWebhookOut,
    PaymentGatewayConfigOut,
    PaymentGatewayConfigUpsert,
    PaymentTransactionOut,
    PendingCustomOrderOut,
    PlanPresetOut,
)
from app.services.subscriptions_service import SubscriptionService

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions & Billing"])
admin_router = APIRouter(prefix="/admin/subscriptions", tags=["Administración de Suscripciones"])

def _service(db: AsyncSession) -> SubscriptionService:
    return SubscriptionService(db)


@router.get("/plans", response_model=list[PlanPresetOut])
async def list_subscription_plans(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[PlanPresetOut]:
    return await _service(db).list_subscription_plans()


@router.get("/my-company", response_model=EmpresaSubscriptionOut)
async def get_my_company_subscription(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> EmpresaSubscriptionOut:
    return await _service(db).get_my_company_subscription(current_user)


@router.post("/checkout", response_model=CheckoutResponse, status_code=status.HTTP_201_CREATED)
async def create_checkout_request(
    body: CheckoutRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CheckoutResponse:
    return await _service(db).create_checkout_request(body)


@router.post("/payphone/webhook", response_model=PayPhoneWebhookOut)
async def payphone_webhook(
    body: PayPhoneWebhookIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_webhook_token: Annotated[str | None, Header(alias="X-Webhook-Token")] = None,
) -> PayPhoneWebhookOut:
    return await _service(db).process_payphone_webhook(body, webhook_token=x_webhook_token)


@admin_router.get("/gateways", response_model=list[PaymentGatewayConfigOut])
async def list_gateway_configs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_superadmin())],
) -> list[PaymentGatewayConfigOut]:
    _ = current_user
    return await _service(db).list_gateway_configs()


@admin_router.put("/gateways/{provider}", response_model=PaymentGatewayConfigOut)
async def upsert_gateway_config(
    provider: GatewayProviderEnum,
    body: PaymentGatewayConfigUpsert,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_superadmin())],
) -> PaymentGatewayConfigOut:
    return await _service(db).upsert_gateway_config(provider, body, current_user=current_user)


@admin_router.get("/companies", response_model=list[EmpresaSubscriptionOut])
async def list_company_subscriptions(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_superadmin())],
    limit: int = Query(200, ge=1, le=500),
) -> list[EmpresaSubscriptionOut]:
    _ = current_user
    return await _service(db).list_company_subscriptions(limit=limit)


@admin_router.put("/companies/{id_empresa}", response_model=EmpresaSubscriptionOut)
async def upsert_company_subscription(
    id_empresa: int,
    body: EmpresaSubscriptionUpsert,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_superadmin())],
) -> EmpresaSubscriptionOut:
    return await _service(db).upsert_company_subscription(
        id_empresa=id_empresa,
        body=body,
        current_user=current_user,
    )


@admin_router.post("/custom-orders", response_model=CustomOrderOut, status_code=status.HTTP_201_CREATED)
async def create_custom_order(
    body: CustomOrderCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_superadmin())],
) -> CustomOrderOut:
    return await _service(db).create_custom_order(body, current_user=current_user)


@admin_router.get("/custom-orders/pending", response_model=list[PendingCustomOrderOut])
async def list_pending_custom_orders(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_superadmin())],
    limit: int = Query(100, ge=1, le=500),
) -> list[PendingCustomOrderOut]:
    _ = current_user
    return await _service(db).list_pending_custom_orders(limit=limit)


@admin_router.post("/custom-orders/{id_pago}/activate", response_model=ActivateCustomOrderOut)
async def activate_custom_order(
    id_pago: Annotated[int, Path(..., description="ID del pago a activar")],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_superadmin())],
) -> ActivateCustomOrderOut:
    return await _service(db).activate_custom_order(id_pago=id_pago, current_user=current_user)


@admin_router.get("/payments", response_model=list[PaymentTransactionOut])
async def list_payment_requests(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_superadmin())],
    limit: int = Query(100, ge=1, le=500),
) -> list[PaymentTransactionOut]:
    _ = current_user
    return await _service(db).list_payment_requests(limit=limit)
