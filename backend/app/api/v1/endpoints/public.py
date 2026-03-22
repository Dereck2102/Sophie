from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.platform_catalog import LAYERS, PLAN_DEFINITIONS
from app.schemas.platform import PlatformLayerOut, PublicLandingOut, PublicPlanOut

router = APIRouter(prefix="/public", tags=["Public Layer"])


@router.get("/plans", response_model=list[PublicPlanOut])
async def list_public_plans() -> list[PublicPlanOut]:
    return [
        PublicPlanOut(
            key=plan.key,
            name=plan.name,
            tier=plan.tier.value,
            description=plan.description,
            monthly_price_usd=Decimal(str(plan.monthly_price_usd)) if plan.monthly_price_usd is not None else None,
            yearly_price_usd=Decimal(str(plan.yearly_price_usd)) if plan.yearly_price_usd is not None else None,
            modules=plan.modules,
        )
        for plan in PLAN_DEFINITIONS
    ]


@router.get("/landing", response_model=PublicLandingOut)
async def get_public_landing() -> PublicLandingOut:
    settings = get_settings()
    return PublicLandingOut(
        platform_name=settings.APP_NAME,
        platform_version=settings.APP_VERSION,
        layers=[
            PlatformLayerOut(key=layer.key, name=layer.name, description=layer.description)
            for layer in LAYERS
        ],
        plans=[
            PublicPlanOut(
                key=plan.key,
                name=plan.name,
                tier=plan.tier.value,
                description=plan.description,
                monthly_price_usd=Decimal(str(plan.monthly_price_usd)) if plan.monthly_price_usd is not None else None,
                yearly_price_usd=Decimal(str(plan.yearly_price_usd)) if plan.yearly_price_usd is not None else None,
                modules=plan.modules,
            )
            for plan in PLAN_DEFINITIONS
        ],
    )