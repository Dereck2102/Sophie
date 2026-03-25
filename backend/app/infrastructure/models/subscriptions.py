from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PlanTierEnum(str, enum.Enum):
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class BillingCycleEnum(str, enum.Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


class SubscriptionStatusEnum(str, enum.Enum):
    ACTIVE = "active"
    TRIAL = "trial"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    PENDING = "pending"


class PaymentStatusEnum(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELED = "canceled"


class GatewayProviderEnum(str, enum.Enum):
    PAYPHONE = "payphone"
    STRIPE = "stripe"


class CustomOrderStatusEnum(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    ACTIVATED = "activated"
    CANCELED = "canceled"


class EmpresaSubscription(Base):
    __tablename__ = "empresa_subscription"

    id_empresa: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresa.id_cliente", ondelete="CASCADE"), primary_key=True
    )
    plan_tier: Mapped[PlanTierEnum] = mapped_column(Enum(PlanTierEnum), nullable=False, default=PlanTierEnum.STARTER)
    billing_cycle: Mapped[BillingCycleEnum] = mapped_column(
        Enum(BillingCycleEnum), nullable=False, default=BillingCycleEnum.MONTHLY
    )
    status: Mapped[SubscriptionStatusEnum] = mapped_column(
        Enum(SubscriptionStatusEnum), nullable=False, default=SubscriptionStatusEnum.PENDING
    )
    price_usd: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    features_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    custom_notes: Mapped[str | None] = mapped_column(String(800), nullable=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("usuario.id_usuario"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    empresa = relationship("Empresa")
    updated_by = relationship("Usuario")


class UserSubscription(Base):
    __tablename__ = "user_subscription"

    id_usuario: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuario.id_usuario", ondelete="CASCADE"), primary_key=True
    )
    plan_tier: Mapped[PlanTierEnum] = mapped_column(Enum(PlanTierEnum), nullable=False, default=PlanTierEnum.STARTER)
    billing_cycle: Mapped[BillingCycleEnum] = mapped_column(
        Enum(BillingCycleEnum), nullable=False, default=BillingCycleEnum.MONTHLY
    )
    status: Mapped[SubscriptionStatusEnum] = mapped_column(
        Enum(SubscriptionStatusEnum), nullable=False, default=SubscriptionStatusEnum.PENDING
    )
    price_usd: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    features_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    custom_notes: Mapped[str | None] = mapped_column(String(800), nullable=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("usuario.id_usuario"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    usuario = relationship("Usuario", foreign_keys=[id_usuario])
    updated_by = relationship("Usuario", foreign_keys=[updated_by_user_id])


class PaymentTransaction(Base):
    __tablename__ = "payment_transaction"

    id_pago: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    id_empresa: Mapped[int | None] = mapped_column(Integer, ForeignKey("empresa.id_cliente", ondelete="SET NULL"), nullable=True)
    id_usuario_owner: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuario.id_usuario", ondelete="SET NULL"),
        nullable=True,
    )
    plan_tier: Mapped[PlanTierEnum] = mapped_column(Enum(PlanTierEnum), nullable=False)
    billing_cycle: Mapped[BillingCycleEnum] = mapped_column(Enum(BillingCycleEnum), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")
    provider_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    checkout_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[PaymentStatusEnum] = mapped_column(Enum(PaymentStatusEnum), nullable=False, default=PaymentStatusEnum.PENDING)
    customer_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    customer_email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    custom_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    empresa = relationship("Empresa")
    usuario_owner = relationship("Usuario")


class CustomOrder(Base):
    __tablename__ = "custom_order"

    id_order: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    id_empresa: Mapped[int] = mapped_column(Integer, ForeignKey("empresa.id_cliente", ondelete="CASCADE"), nullable=False)
    id_pago: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("payment_transaction.id_pago", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
    )
    billing_cycle: Mapped[BillingCycleEnum] = mapped_column(Enum(BillingCycleEnum), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    status: Mapped[CustomOrderStatusEnum] = mapped_column(
        Enum(CustomOrderStatusEnum), nullable=False, default=CustomOrderStatusEnum.PENDING
    )
    custom_requirements: Mapped[str] = mapped_column(Text, nullable=False)
    feature_overrides_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("usuario.id_usuario"), nullable=True)
    approved_by_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("usuario.id_usuario"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    empresa = relationship("Empresa")
    payment = relationship("PaymentTransaction")
    created_by = relationship("Usuario", foreign_keys=[created_by_user_id])
    approved_by = relationship("Usuario", foreign_keys=[approved_by_user_id])


class PaymentWebhookEvent(Base):
    __tablename__ = "payment_webhook_event"
    __table_args__ = (
        UniqueConstraint("provider", "event_key", name="uq_payment_webhook_provider_event_key"),
    )

    id_event: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    event_key: Mapped[str] = mapped_column(String(150), nullable=False)
    payment_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("payment_transaction.id_pago", ondelete="SET NULL"), nullable=True)
    status_received: Mapped[str] = mapped_column(String(40), nullable=False)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed: Mapped[bool] = mapped_column(nullable=False, default=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    payment = relationship("PaymentTransaction")


class PaymentGatewayConfig(Base):
    __tablename__ = "payment_gateway_config"

    id_config: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    provider: Mapped[GatewayProviderEnum] = mapped_column(Enum(GatewayProviderEnum), unique=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(nullable=False, default=False)
    public_key: Mapped[str | None] = mapped_column(String(250), nullable=True)
    secret_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("usuario.id_usuario"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    updated_by = relationship("Usuario")
