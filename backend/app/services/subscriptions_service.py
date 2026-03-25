from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from decimal import Decimal

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.platform_catalog import get_plan_by_tier
from app.core.security import decrypt_vault, encrypt_vault
from app.infrastructure.models.cliente import Empresa
from app.infrastructure.models.subscriptions import (
    BillingCycleEnum,
    CustomOrder,
    CustomOrderStatusEnum,
    EmpresaSubscription,
    GatewayProviderEnum,
    PaymentGatewayConfig,
    PaymentStatusEnum,
    PaymentTransaction,
    PaymentWebhookEvent,
    PlanTierEnum,
    SubscriptionStatusEnum,
    UserSubscription,
)
from app.infrastructure.models.usuario import RolEnum, Usuario
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
    UserSubscriptionOut,
    UserSubscriptionUpsert,
)

_PLAN_PRESETS: dict[PlanTierEnum, dict[str, object]] = {
    PlanTierEnum.STARTER: {
        "name": "Basic ERP",
        "description": "ERP básico con operación técnica: tickets, taller y proyectos.",
        "monthly_price_usd": Decimal("29.00"),
        "yearly_price_usd": Decimal("290.00"),
        "features": ["tickets", "taller", "proyectos", "dashboard_basic", "email_notifications"],
    },
    PlanTierEnum.PRO: {
        "name": "Plus ERP",
        "description": "ERP con operación extendida: inventario, compras y analítica ampliada.",
        "monthly_price_usd": Decimal("79.00"),
        "yearly_price_usd": Decimal("790.00"),
        "features": [
            "tickets",
            "taller",
            "proyectos",
            "dashboard_advanced",
            "compras",
            "inventory",
            "workflows_basic",
        ],
    },
    PlanTierEnum.ENTERPRISE: {
        "name": "Enterprise ERP",
        "description": "ERP corporativo con automatización avanzada, auditoría por cliente e integración API.",
        "monthly_price_usd": Decimal("149.00"),
        "yearly_price_usd": Decimal("1490.00"),
        "features": [
            "tickets",
            "taller",
            "proyectos",
            "dashboard_advanced",
            "compras",
            "inventory",
            "auditoria",
            "advanced_mfa",
            "api_access",
            "multiempresa",
            "multimoneda",
            "workflows_advanced",
            "bi_realtime",
        ],
    },
    PlanTierEnum.CUSTOM: {
        "name": "Custom",
        "description": "Implementación personalizada por requerimientos del cliente.",
        "monthly_price_usd": None,
        "yearly_price_usd": None,
        "features": [],
    },
}

_SENSITIVE_GATEWAY_EXTRA_KEYS = {"webhook_token"}


def _parse_features_json(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return sorted({str(item).strip() for item in data if str(item).strip()})


def _parse_json_obj(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value) for key, value in data.items() if value is not None}


def _decrypt_gateway_value(value: str | None, *, strict: bool = False) -> str | None:
    raw = (value or "").strip()
    if not raw:
        return None
    if not raw.startswith("enc:"):
        return raw
    try:
        return decrypt_vault(raw.removeprefix("enc:"))
    except RuntimeError:
        if strict:
            raise HTTPException(status_code=503, detail="No se pudo descifrar configuración sensible del gateway")
        return None


def _serialize_gateway_extra(data: dict[str, str | None]) -> str:
    normalized: dict[str, str | None] = {}
    for key, value in data.items():
        clean = (value or "").strip()
        if key in _SENSITIVE_GATEWAY_EXTRA_KEYS:
            if not clean:
                normalized[key] = None
                continue
            try:
                normalized[key] = f"enc:{encrypt_vault(clean)}"
            except RuntimeError as exc:
                raise HTTPException(status_code=503, detail=f"No se pudo cifrar configuración sensible: {exc}")
            continue
        normalized[key] = clean or None

    return json.dumps(normalized)


def _read_gateway_extra(raw: str | None, *, strict: bool = False) -> dict[str, str]:
    parsed = _parse_json_obj(raw)
    output: dict[str, str] = {}
    for key, value in parsed.items():
        if key in _SENSITIVE_GATEWAY_EXTRA_KEYS:
            decrypted = _decrypt_gateway_value(value, strict=strict)
            if decrypted:
                output[key] = decrypted
            continue
        output[key] = value
    return output


def _plan_price(plan: PlanTierEnum, yearly: bool) -> Decimal:
    preset = _PLAN_PRESETS[plan]
    key = "yearly_price_usd" if yearly else "monthly_price_usd"
    value = preset.get(key)
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _plan_features(plan: PlanTierEnum) -> list[str]:
    if plan == PlanTierEnum.CUSTOM:
        return []
    try:
        return list(get_plan_by_tier(plan).modules)
    except KeyError:
        features = _PLAN_PRESETS[plan].get("features", [])
        return [str(f) for f in features]


def _extract_custom_features_from_text(custom_requirements: str | None) -> list[str]:
    raw = (custom_requirements or "").splitlines()
    for line in raw:
        if line.startswith("FEATURES:"):
            values = line.replace("FEATURES:", "", 1).split(",")
            return sorted({item.strip() for item in values if item and item.strip()})
    return []


def _compose_custom_requirements(custom_requirements: str, feature_overrides: list[str]) -> str:
    clean_features = sorted({item.strip() for item in feature_overrides if item and item.strip()})
    return f"{custom_requirements.strip()}\nFEATURES:{','.join(clean_features)}"


class SubscriptionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_gateway_config(self, provider: GatewayProviderEnum) -> PaymentGatewayConfig | None:
        result = await self.db.execute(select(PaymentGatewayConfig).where(PaymentGatewayConfig.provider == provider))
        return result.scalar_one_or_none()

    async def _resolve_payment_for_webhook(
        self,
        transaction_id: str | None,
        client_transaction_id: str | None,
    ) -> PaymentTransaction | None:
        if transaction_id:
            result = await self.db.execute(
                select(PaymentTransaction).where(PaymentTransaction.provider_reference == transaction_id)
            )
            payment = result.scalar_one_or_none()
            if payment:
                return payment

        if client_transaction_id:
            result = await self.db.execute(
                select(PaymentTransaction).where(PaymentTransaction.provider_reference == client_transaction_id)
            )
            payment = result.scalar_one_or_none()
            if payment:
                return payment

            if client_transaction_id.startswith("SOPHIE-"):
                _, _, raw_id = client_transaction_id.partition("SOPHIE-")
                if raw_id.isdigit():
                    by_id = await self.db.execute(
                        select(PaymentTransaction).where(PaymentTransaction.id_pago == int(raw_id))
                    )
                    return by_id.scalar_one_or_none()

        return None

    async def _activate_subscription_for_paid_payment(
        self,
        payment: PaymentTransaction,
        *,
        allow_custom: bool = False,
    ) -> bool:
        if payment.plan_tier == PlanTierEnum.CUSTOM and not allow_custom:
            return False
        if payment.id_empresa is None and payment.id_usuario_owner is None:
            return False

        if payment.id_usuario_owner is not None:
            user_result = await self.db.execute(select(Usuario).where(Usuario.id_usuario == payment.id_usuario_owner))
            user = user_result.scalar_one_or_none()
            if not user:
                return False

            user_sub_result = await self.db.execute(
                select(UserSubscription).where(UserSubscription.id_usuario == payment.id_usuario_owner)
            )
            user_sub = user_sub_result.scalar_one_or_none()
            if not user_sub:
                user_sub = UserSubscription(id_usuario=payment.id_usuario_owner)
                self.db.add(user_sub)

            user_sub.plan_tier = payment.plan_tier
            user_sub.billing_cycle = payment.billing_cycle
            user_sub.status = SubscriptionStatusEnum.ACTIVE
            user_sub.price_usd = Decimal(str(payment.amount))
            user_sub.currency = payment.currency or "USD"
            if payment.plan_tier == PlanTierEnum.CUSTOM:
                user_sub.features_json = json.dumps(_extract_custom_features_from_text(payment.custom_requirements))
            else:
                user_sub.features_json = json.dumps(_plan_features(payment.plan_tier))
            await self.db.flush()
            return True

        result = await self.db.execute(
            select(EmpresaSubscription).where(EmpresaSubscription.id_empresa == payment.id_empresa)
        )
        sub = result.scalar_one_or_none()
        if not sub:
            sub = EmpresaSubscription(id_empresa=payment.id_empresa)
            self.db.add(sub)

        sub.plan_tier = payment.plan_tier
        sub.billing_cycle = payment.billing_cycle
        sub.status = SubscriptionStatusEnum.ACTIVE
        sub.price_usd = Decimal(str(payment.amount))
        sub.currency = payment.currency or "USD"
        if payment.plan_tier == PlanTierEnum.CUSTOM:
            sub.features_json = json.dumps(_extract_custom_features_from_text(payment.custom_requirements))
        else:
            sub.features_json = json.dumps(_plan_features(payment.plan_tier))
        await self.db.flush()
        return True

    async def _create_payphone_checkout(
        self,
        payment: PaymentTransaction,
        gateway: PaymentGatewayConfig,
    ) -> tuple[str, str | None, str]:
        if not gateway.secret_encrypted:
            raise HTTPException(status_code=400, detail="PayPhone no tiene token configurado")

        extra = _parse_json_obj(gateway.extra_json)
        endpoint_url = (extra.get("endpoint_url") or "https://pay.payphonetodoesposible.com/api/button/Prepare").strip()
        store_id = (extra.get("store_id") or "").strip()
        if not store_id:
            raise HTTPException(status_code=400, detail="PayPhone requiere store_id")

        try:
            token = decrypt_vault(gateway.secret_encrypted)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=f"No se puede descifrar token de PayPhone: {exc}")

        amount_cents = int((Decimal(str(payment.amount)) * Decimal("100")).quantize(Decimal("1")))
        payload = {
            "amount": amount_cents,
            "amountWithoutTax": amount_cents,
            "tax": 0,
            "clientTransactionId": f"SOPHIE-{payment.id_pago}",
            "storeId": store_id,
            "reference": f"SUB-{payment.plan_tier.value.upper()}-{payment.id_pago}",
        }
        if extra.get("return_url"):
            payload["responseUrl"] = extra["return_url"]
        if extra.get("cancel_url"):
            payload["cancellationUrl"] = extra["cancel_url"]

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(endpoint_url, json=payload, headers=headers)
            if response.status_code >= 400:
                raise HTTPException(
                    status_code=502,
                    detail=f"PayPhone rechazó la solicitud ({response.status_code}): {response.text[:300]}",
                )
            response_data = response.json() if response.content else {}

        checkout_url = (
            response_data.get("payWithCard")
            or response_data.get("paymentUrl")
            or response_data.get("redirectUrl")
            or response_data.get("checkoutUrl")
        )
        if not checkout_url:
            raise HTTPException(status_code=502, detail="PayPhone no devolvió URL de checkout")

        provider_reference = (
            response_data.get("id")
            or response_data.get("transactionId")
            or response_data.get("clientTransactionId")
            or f"SOPHIE-{payment.id_pago}"
        )

        return str(checkout_url), str(provider_reference), "payphone"

    async def list_subscription_plans(self) -> list[PlanPresetOut]:
        return [
            PlanPresetOut(
                plan=plan,
                name=str(data["name"]),
                description=str(data["description"]),
                monthly_price_usd=data["monthly_price_usd"],
                yearly_price_usd=data["yearly_price_usd"],
                features=[str(f) for f in data.get("features", [])],
            )
            for plan, data in _PLAN_PRESETS.items()
        ]

    async def get_my_company_subscription(self, current_user: Usuario) -> EmpresaSubscriptionOut:
        if current_user.rol == RolEnum.SUPERADMIN:
            raise HTTPException(status_code=400, detail="El superadmin no tiene suscripción de empresa propia")
        if current_user.id_cliente is None:
            raise HTTPException(status_code=400, detail="El usuario no está asociado a una empresa")

        empresa_result = await self.db.execute(select(Empresa).where(Empresa.id_cliente == current_user.id_cliente))
        empresa = empresa_result.scalar_one_or_none()
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada para el usuario")

        sub_result = await self.db.execute(
            select(EmpresaSubscription).where(EmpresaSubscription.id_empresa == empresa.id_cliente)
        )
        sub = sub_result.scalar_one_or_none()

        if not sub:
            return EmpresaSubscriptionOut(
                id_empresa=empresa.id_cliente,
                empresa_nombre=empresa.razon_social,
                plan_tier=PlanTierEnum.STARTER,
                billing_cycle=BillingCycleEnum.MONTHLY,
                status=SubscriptionStatusEnum.PENDING,
                price_usd=_plan_price(PlanTierEnum.STARTER, yearly=False),
                currency="USD",
                features=_plan_features(PlanTierEnum.STARTER),
                custom_notes=None,
                updated_by_user_id=None,
                updated_at=None,
            )

        return EmpresaSubscriptionOut(
            id_empresa=empresa.id_cliente,
            empresa_nombre=empresa.razon_social,
            plan_tier=sub.plan_tier,
            billing_cycle=sub.billing_cycle,
            status=sub.status,
            price_usd=Decimal(str(sub.price_usd)),
            currency=sub.currency,
            features=_parse_features_json(sub.features_json) or _plan_features(sub.plan_tier),
            custom_notes=sub.custom_notes,
            updated_by_user_id=sub.updated_by_user_id,
            updated_at=sub.updated_at,
        )

    async def create_checkout_request(self, body: CheckoutRequest) -> CheckoutResponse:
        if body.plan == PlanTierEnum.CUSTOM and not (body.custom_requirements or "").strip():
            raise HTTPException(status_code=400, detail="Para el plan personalizado debes indicar requerimientos.")

        if body.id_empresa is not None:
            empresa_result = await self.db.execute(select(Empresa).where(Empresa.id_cliente == body.id_empresa))
            empresa = empresa_result.scalar_one_or_none()
            if not empresa:
                raise HTTPException(status_code=404, detail="Empresa no encontrada")
        if body.id_usuario_owner is not None:
            user_result = await self.db.execute(select(Usuario).where(Usuario.id_usuario == body.id_usuario_owner))
            owner = user_result.scalar_one_or_none()
            if not owner:
                raise HTTPException(status_code=404, detail="Usuario no encontrado")

        if body.id_empresa is not None and body.id_usuario_owner is not None:
            raise HTTPException(status_code=400, detail="Define id_empresa o id_usuario_owner, pero no ambos")

        is_yearly = body.billing_cycle.value == "yearly"
        amount = _plan_price(body.plan, yearly=is_yearly)
        checkout_ref = secrets.token_urlsafe(18)
        provider = "mock_gateway"
        checkout_url = f"https://pay.sophie.local/checkout/{checkout_ref}"
        provider_reference = checkout_ref

        payment = PaymentTransaction(
            id_empresa=body.id_empresa,
            id_usuario_owner=body.id_usuario_owner,
            plan_tier=body.plan,
            billing_cycle=body.billing_cycle,
            amount=amount,
            currency="USD",
            provider=provider,
            provider_reference=provider_reference,
            checkout_url=checkout_url,
            status=PaymentStatusEnum.PENDING,
            customer_name=body.customer_name,
            customer_email=str(body.customer_email) if body.customer_email else None,
            custom_requirements=body.custom_requirements,
        )
        self.db.add(payment)
        await self.db.flush()

        if body.plan != PlanTierEnum.CUSTOM:
            payphone_cfg = await self._get_gateway_config(GatewayProviderEnum.PAYPHONE)
            if payphone_cfg and payphone_cfg.enabled:
                checkout_url, provider_reference, provider = await self._create_payphone_checkout(payment, payphone_cfg)
                payment.provider = provider
                payment.provider_reference = provider_reference
                payment.checkout_url = checkout_url
                await self.db.flush()

        detail = "Solicitud de checkout creada."
        if body.plan == PlanTierEnum.CUSTOM:
            detail = "Solicitud personalizada registrada. El equipo comercial debe cotizar este plan."
        elif provider == "payphone":
            detail = "Checkout de PayPhone generado correctamente."

        return CheckoutResponse(
            id_pago=payment.id_pago,
            provider=payment.provider,
            status=payment.status,
            amount=Decimal(str(payment.amount)),
            currency=payment.currency,
            checkout_url=payment.checkout_url,
            detail=detail,
        )

    async def process_payphone_webhook(
        self,
        body: PayPhoneWebhookIn,
        *,
        webhook_token: str | None,
    ) -> PayPhoneWebhookOut:
        payphone_cfg = await self._get_gateway_config(GatewayProviderEnum.PAYPHONE)
        if not payphone_cfg or not payphone_cfg.enabled:
            raise HTTPException(status_code=400, detail="PayPhone no está habilitado")

        extra = _read_gateway_extra(payphone_cfg.extra_json, strict=True)
        expected_token = (extra.get("webhook_token") or "").strip()
        if expected_token and (not webhook_token or webhook_token.strip() != expected_token):
            raise HTTPException(status_code=401, detail="Webhook token inválido")

        event_key = body.transaction_id or body.client_transaction_id or f"fallback:{body.status}:{body.amount}:{body.currency}"
        existing_event_result = await self.db.execute(
            select(PaymentWebhookEvent).where(
                PaymentWebhookEvent.provider == "payphone",
                PaymentWebhookEvent.event_key == event_key,
            )
        )
        existing_event = existing_event_result.scalar_one_or_none()
        if existing_event and existing_event.processed:
            return PayPhoneWebhookOut(
                detail="Webhook duplicado ignorado (idempotente)",
                payment_id=existing_event.payment_id,
                auto_activated=False,
            )

        event = existing_event
        if not event:
            event = PaymentWebhookEvent(
                provider="payphone",
                event_key=event_key,
                status_received=(body.status or "").strip().lower(),
                payload_json=json.dumps(body.model_dump(mode="json"), default=str),
                processed=False,
            )
            self.db.add(event)
            await self.db.flush()

        payment = await self._resolve_payment_for_webhook(body.transaction_id, body.client_transaction_id)
        if not payment:
            raise HTTPException(status_code=404, detail="Pago no encontrado")

        normalized_status = (body.status or "").strip().lower()
        auto_activated = False

        if normalized_status in {"paid", "approved", "completed", "success"}:
            payment.status = PaymentStatusEnum.PAID
            payment.paid_at = datetime.now(timezone.utc)
            auto_activated = await self._activate_subscription_for_paid_payment(payment)
        elif normalized_status in {"failed", "denied", "error"}:
            payment.status = PaymentStatusEnum.FAILED
        elif normalized_status in {"canceled", "cancelled"}:
            payment.status = PaymentStatusEnum.CANCELED

        event.payment_id = payment.id_pago
        event.status_received = normalized_status
        event.processed = True
        event.processed_at = datetime.now(timezone.utc)
        await self.db.flush()

        detail = "Webhook procesado"
        if payment.plan_tier == PlanTierEnum.CUSTOM and payment.status == PaymentStatusEnum.PAID:
            detail = "Pago custom registrado. Activación manual requerida por superadmin."

        return PayPhoneWebhookOut(
            detail=detail,
            payment_id=payment.id_pago,
            auto_activated=auto_activated,
        )

    async def list_gateway_configs(self) -> list[PaymentGatewayConfigOut]:
        result = await self.db.execute(select(PaymentGatewayConfig).order_by(PaymentGatewayConfig.provider.asc()))
        rows = list(result.scalars().all())
        output: list[PaymentGatewayConfigOut] = []
        for row in rows:
            extra = _read_gateway_extra(row.extra_json, strict=False)
            output.append(
                PaymentGatewayConfigOut(
                    provider=row.provider,
                    enabled=row.enabled,
                    public_key=row.public_key,
                    has_secret=bool(row.secret_encrypted),
                    endpoint_url=extra.get("endpoint_url"),
                    store_id=extra.get("store_id"),
                    return_url=extra.get("return_url"),
                    cancel_url=extra.get("cancel_url"),
                    has_webhook_token=bool((extra.get("webhook_token") or "").strip()),
                    updated_by_user_id=row.updated_by_user_id,
                    updated_at=row.updated_at,
                )
            )
        return output

    async def upsert_gateway_config(
        self,
        provider: GatewayProviderEnum,
        body: PaymentGatewayConfigUpsert,
        *,
        current_user: Usuario,
    ) -> PaymentGatewayConfigOut:
        if provider != body.provider:
            raise HTTPException(status_code=400, detail="El provider de URL y body deben coincidir")

        result = await self.db.execute(select(PaymentGatewayConfig).where(PaymentGatewayConfig.provider == provider))
        row = result.scalar_one_or_none()
        if not row:
            row = PaymentGatewayConfig(provider=provider)
            self.db.add(row)

        row.enabled = body.enabled
        row.public_key = body.public_key
        row.updated_by_user_id = current_user.id_usuario
        if body.secret is not None:
            if body.secret.strip():
                try:
                    row.secret_encrypted = encrypt_vault(body.secret.strip())
                except RuntimeError as exc:
                    raise HTTPException(status_code=503, detail=f"No se pudo cifrar secreto: {exc}")
            else:
                row.secret_encrypted = None

        row.extra_json = _serialize_gateway_extra(
            {
                "endpoint_url": body.endpoint_url,
                "store_id": body.store_id,
                "return_url": body.return_url,
                "cancel_url": body.cancel_url,
                "webhook_token": body.webhook_token,
            }
        )

        await self.db.flush()
        extra = _read_gateway_extra(row.extra_json, strict=False)
        return PaymentGatewayConfigOut(
            provider=row.provider,
            enabled=row.enabled,
            public_key=row.public_key,
            has_secret=bool(row.secret_encrypted),
            endpoint_url=extra.get("endpoint_url"),
            store_id=extra.get("store_id"),
            return_url=extra.get("return_url"),
            cancel_url=extra.get("cancel_url"),
            has_webhook_token=bool((extra.get("webhook_token") or "").strip()),
            updated_by_user_id=row.updated_by_user_id,
            updated_at=row.updated_at,
        )

    async def list_company_subscriptions(self, *, limit: int) -> list[EmpresaSubscriptionOut]:
        empresas_result = await self.db.execute(select(Empresa).order_by(Empresa.razon_social).limit(limit))
        empresas = list(empresas_result.scalars().all())
        if not empresas:
            return []

        ids = [e.id_cliente for e in empresas]
        subs_result = await self.db.execute(select(EmpresaSubscription).where(EmpresaSubscription.id_empresa.in_(ids)))
        subs_map = {sub.id_empresa: sub for sub in subs_result.scalars().all()}

        output: list[EmpresaSubscriptionOut] = []
        for empresa in empresas:
            sub = subs_map.get(empresa.id_cliente)
            if sub:
                features = _parse_features_json(sub.features_json)
                output.append(
                    EmpresaSubscriptionOut(
                        id_empresa=empresa.id_cliente,
                        empresa_nombre=empresa.razon_social,
                        plan_tier=sub.plan_tier,
                        billing_cycle=sub.billing_cycle,
                        status=sub.status,
                        price_usd=Decimal(str(sub.price_usd)),
                        currency=sub.currency,
                        features=features,
                        custom_notes=sub.custom_notes,
                        updated_by_user_id=sub.updated_by_user_id,
                        updated_at=sub.updated_at,
                    )
                )
            else:
                output.append(
                    EmpresaSubscriptionOut(
                        id_empresa=empresa.id_cliente,
                        empresa_nombre=empresa.razon_social,
                        plan_tier=PlanTierEnum.STARTER,
                        billing_cycle=BillingCycleEnum.MONTHLY,
                        status=SubscriptionStatusEnum.PENDING,
                        price_usd=_plan_price(PlanTierEnum.STARTER, yearly=False),
                        currency="USD",
                        features=_plan_features(PlanTierEnum.STARTER),
                        custom_notes=None,
                        updated_by_user_id=None,
                        updated_at=None,
                    )
                )
        return output

    async def upsert_company_subscription(
        self,
        *,
        id_empresa: int,
        body: EmpresaSubscriptionUpsert,
        current_user: Usuario,
    ) -> EmpresaSubscriptionOut:
        empresa_result = await self.db.execute(select(Empresa).where(Empresa.id_cliente == id_empresa))
        empresa = empresa_result.scalar_one_or_none()
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

        default_features = _plan_features(body.plan_tier)
        override_features = sorted({item.strip() for item in body.feature_overrides if item and item.strip()})

        if body.plan_tier == PlanTierEnum.CUSTOM and not override_features:
            raise HTTPException(
                status_code=400,
                detail="El plan custom requiere features explícitas definidas por superadmin.",
            )

        final_features = override_features or default_features
        price = _plan_price(body.plan_tier, yearly=body.billing_cycle.value == "yearly")

        sub_result = await self.db.execute(select(EmpresaSubscription).where(EmpresaSubscription.id_empresa == id_empresa))
        sub = sub_result.scalar_one_or_none()
        if not sub:
            sub = EmpresaSubscription(id_empresa=id_empresa)
            self.db.add(sub)

        sub.plan_tier = body.plan_tier
        sub.billing_cycle = body.billing_cycle
        sub.status = body.status
        sub.price_usd = price
        sub.currency = "USD"
        sub.features_json = json.dumps(final_features)
        sub.custom_notes = body.custom_notes
        sub.updated_by_user_id = current_user.id_usuario

        await self.db.flush()

        return EmpresaSubscriptionOut(
            id_empresa=id_empresa,
            empresa_nombre=empresa.razon_social,
            plan_tier=sub.plan_tier,
            billing_cycle=sub.billing_cycle,
            status=sub.status,
            price_usd=Decimal(str(sub.price_usd)),
            currency=sub.currency,
            features=final_features,
            custom_notes=sub.custom_notes,
            updated_by_user_id=sub.updated_by_user_id,
            updated_at=sub.updated_at,
        )

    async def list_user_subscriptions(self, *, limit: int) -> list[UserSubscriptionOut]:
        users_result = await self.db.execute(
            select(Usuario).where(Usuario.id_cliente.is_not(None)).order_by(Usuario.username.asc()).limit(limit)
        )
        users = list(users_result.scalars().all())
        if not users:
            return []

        ids = [user.id_usuario for user in users]
        subs_result = await self.db.execute(select(UserSubscription).where(UserSubscription.id_usuario.in_(ids)))
        subs_map = {sub.id_usuario: sub for sub in subs_result.scalars().all()}

        output: list[UserSubscriptionOut] = []
        for user in users:
            sub = subs_map.get(user.id_usuario)
            if sub:
                features = _parse_features_json(sub.features_json)
                output.append(
                    UserSubscriptionOut(
                        id_usuario=user.id_usuario,
                        username=user.username,
                        email=user.email,
                        plan_tier=sub.plan_tier,
                        billing_cycle=sub.billing_cycle,
                        status=sub.status,
                        price_usd=Decimal(str(sub.price_usd)),
                        currency=sub.currency,
                        features=features,
                        custom_notes=sub.custom_notes,
                        updated_by_user_id=sub.updated_by_user_id,
                        updated_at=sub.updated_at,
                    )
                )
            else:
                output.append(
                    UserSubscriptionOut(
                        id_usuario=user.id_usuario,
                        username=user.username,
                        email=user.email,
                        plan_tier=PlanTierEnum.STARTER,
                        billing_cycle=BillingCycleEnum.MONTHLY,
                        status=SubscriptionStatusEnum.PENDING,
                        price_usd=_plan_price(PlanTierEnum.STARTER, yearly=False),
                        currency="USD",
                        features=_plan_features(PlanTierEnum.STARTER),
                        custom_notes=None,
                        updated_by_user_id=None,
                        updated_at=None,
                    )
                )
        return output

    async def upsert_user_subscription(
        self,
        *,
        id_usuario: int,
        body: UserSubscriptionUpsert,
        current_user: Usuario,
    ) -> UserSubscriptionOut:
        user_result = await self.db.execute(select(Usuario).where(Usuario.id_usuario == id_usuario))
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        default_features = _plan_features(body.plan_tier)
        override_features = sorted({item.strip() for item in body.feature_overrides if item and item.strip()})

        if body.plan_tier == PlanTierEnum.CUSTOM and not override_features:
            raise HTTPException(
                status_code=400,
                detail="El plan custom requiere features explícitas definidas por superadmin.",
            )

        final_features = override_features or default_features
        price = _plan_price(body.plan_tier, yearly=body.billing_cycle.value == "yearly")

        sub_result = await self.db.execute(select(UserSubscription).where(UserSubscription.id_usuario == id_usuario))
        sub = sub_result.scalar_one_or_none()
        if not sub:
            sub = UserSubscription(id_usuario=id_usuario)
            self.db.add(sub)

        sub.plan_tier = body.plan_tier
        sub.billing_cycle = body.billing_cycle
        sub.status = body.status
        sub.price_usd = price
        sub.currency = "USD"
        sub.features_json = json.dumps(final_features)
        sub.custom_notes = body.custom_notes
        sub.updated_by_user_id = current_user.id_usuario

        await self.db.flush()

        return UserSubscriptionOut(
            id_usuario=id_usuario,
            username=user.username,
            email=user.email,
            plan_tier=sub.plan_tier,
            billing_cycle=sub.billing_cycle,
            status=sub.status,
            price_usd=Decimal(str(sub.price_usd)),
            currency=sub.currency,
            features=final_features,
            custom_notes=sub.custom_notes,
            updated_by_user_id=sub.updated_by_user_id,
            updated_at=sub.updated_at,
        )

    async def create_custom_order(
        self,
        body: CustomOrderCreate,
        *,
        current_user: Usuario,
    ) -> CustomOrderOut:
        empresa_result = await self.db.execute(select(Empresa).where(Empresa.id_cliente == body.id_empresa))
        empresa = empresa_result.scalar_one_or_none()
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

        feature_overrides = sorted({item.strip() for item in body.feature_overrides if item and item.strip()})
        if not feature_overrides:
            raise HTTPException(status_code=400, detail="Debes definir al menos una feature para el plan personalizado")

        custom_order = CustomOrder(
            order_number=f"TMP-{secrets.token_hex(8)}",
            id_empresa=body.id_empresa,
            billing_cycle=body.billing_cycle,
            amount=body.amount_usd,
            currency="USD",
            status=CustomOrderStatusEnum.PENDING,
            custom_requirements=body.custom_requirements.strip(),
            feature_overrides_json=json.dumps(feature_overrides),
            created_by_user_id=current_user.id_usuario,
        )
        self.db.add(custom_order)
        await self.db.flush()
        custom_order.order_number = f"CUS-ORD-{custom_order.id_order:06d}"

        provider = "custom_order"
        checkout_url = None
        provider_reference = custom_order.order_number
        payment = PaymentTransaction(
            id_empresa=body.id_empresa,
            plan_tier=PlanTierEnum.CUSTOM,
            billing_cycle=body.billing_cycle,
            amount=body.amount_usd,
            currency="USD",
            provider=provider,
            provider_reference=provider_reference,
            checkout_url=checkout_url,
            status=PaymentStatusEnum.PENDING,
            customer_name=empresa.razon_social,
            customer_email=None,
            custom_requirements=_compose_custom_requirements(body.custom_requirements, feature_overrides),
        )
        self.db.add(payment)
        await self.db.flush()

        custom_order.id_pago = payment.id_pago

        if body.generate_payphone_checkout:
            payphone_cfg = await self._get_gateway_config(GatewayProviderEnum.PAYPHONE)
            if not payphone_cfg or not payphone_cfg.enabled:
                raise HTTPException(status_code=400, detail="PayPhone no está habilitado para generar checkout")
            checkout_url, provider_reference, provider = await self._create_payphone_checkout(payment, payphone_cfg)
            payment.provider = provider
            payment.provider_reference = provider_reference
            payment.checkout_url = checkout_url
            await self.db.flush()

        detail = "Orden de cobro custom creada. Activación manual requerida tras validación interna."
        if payment.checkout_url:
            detail = "Orden de cobro custom creada con checkout PayPhone. Activación manual requerida."

        return CustomOrderOut(
            id_pago=payment.id_pago,
            order_number=custom_order.order_number,
            status=payment.status,
            amount=Decimal(str(payment.amount)),
            currency=payment.currency,
            checkout_url=payment.checkout_url,
            detail=detail,
        )

    async def activate_custom_order(
        self,
        *,
        id_pago: int,
        current_user: Usuario,
    ) -> ActivateCustomOrderOut:
        payment_result = await self.db.execute(select(PaymentTransaction).where(PaymentTransaction.id_pago == id_pago))
        payment = payment_result.scalar_one_or_none()
        if not payment:
            raise HTTPException(status_code=404, detail="Pago no encontrado")

        if payment.plan_tier != PlanTierEnum.CUSTOM:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Solo órdenes personalizadas (CUSTOM) pueden activarse manualmente. "
                    "Los planes estándar se activan automáticamente via webhook de PayPhone."
                ),
            )

        if payment.status != PaymentStatusEnum.PENDING:
            raise HTTPException(
                status_code=400,
                detail=f"El pago ya ha sido procesado. Estado actual: {payment.status}",
            )
        if payment.id_empresa is None:
            raise HTTPException(status_code=400, detail="La orden custom no está asociada a una empresa")

        payment.status = PaymentStatusEnum.PAID
        payment.paid_at = datetime.now(timezone.utc)

        custom_order_result = await self.db.execute(select(CustomOrder).where(CustomOrder.id_pago == payment.id_pago))
        custom_order = custom_order_result.scalar_one_or_none()
        if custom_order:
            custom_order.status = CustomOrderStatusEnum.ACTIVATED
            custom_order.approved_by_user_id = current_user.id_usuario

        await self.db.flush()

        activated = await self._activate_subscription_for_paid_payment(payment, allow_custom=True)
        if not activated:
            raise HTTPException(status_code=500, detail="No se pudo activar la suscripción. Verifica los datos del plan.")

        sub_result = await self.db.execute(
            select(EmpresaSubscription).where(
                EmpresaSubscription.id_empresa == payment.id_empresa,
                EmpresaSubscription.plan_tier == payment.plan_tier,
            )
        )
        subscription = sub_result.scalar_one_or_none()
        if not subscription:
            raise HTTPException(status_code=500, detail="No se encontró la suscripción activada")

        return ActivateCustomOrderOut(
            id_pago=payment.id_pago,
            id_empresa=payment.id_empresa,
            plan_tier=subscription.plan_tier,
            status=subscription.status,
            features=_parse_features_json(subscription.features_json),
            detail="Orden de cobro personalizada activada exitosamente",
        )

    async def list_payment_requests(self, *, limit: int) -> list[PaymentTransactionOut]:
        result = await self.db.execute(
            select(PaymentTransaction).order_by(PaymentTransaction.created_at.desc()).limit(limit)
        )
        rows = list(result.scalars().all())
        return [PaymentTransactionOut.model_validate(row, from_attributes=True) for row in rows]

    async def list_pending_custom_orders(self, *, limit: int) -> list[PendingCustomOrderOut]:
        result = await self.db.execute(
            select(CustomOrder).where(CustomOrder.status == CustomOrderStatusEnum.PENDING).order_by(CustomOrder.created_at.desc()).limit(limit)
        )
        orders = list(result.scalars().all())
        if not orders:
            return []

        company_ids = sorted({order.id_empresa for order in orders})
        company_result = await self.db.execute(select(Empresa).where(Empresa.id_cliente.in_(company_ids)))
        company_map = {empresa.id_cliente: empresa.razon_social for empresa in company_result.scalars().all()}

        return [
            PendingCustomOrderOut(
                id_order=order.id_order,
                order_number=order.order_number,
                id_pago=order.id_pago,
                id_empresa=order.id_empresa,
                empresa_nombre=company_map.get(order.id_empresa, f"Empresa #{order.id_empresa}"),
                billing_cycle=order.billing_cycle,
                amount=Decimal(str(order.amount)),
                currency=order.currency,
                status=order.status,
                created_at=order.created_at,
            )
            for order in orders
        ]
