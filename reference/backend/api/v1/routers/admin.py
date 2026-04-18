from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator

from backend.api.v1.deps import get_ai_engine_client, get_current_user_id
from backend.infrastructure.clients.ai_engine_protocol import (
    AiEngineClientProtocol,
    AiEngineConfigData,
)

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class UpdateDashscopeApiKeyRequest(BaseModel):
    api_key: str

    @field_validator("api_key")
    @classmethod
    def must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("api_key must not be blank.")
        return v.strip()


class UpdateDashscopeUrlRequest(BaseModel):
    base_url: str

    @field_validator("base_url")
    @classmethod
    def must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("base_url must not be blank.")
        return v.strip()


class UpdateModelRequest(BaseModel):
    task: str
    model_id: str

    @field_validator("task", "model_id")
    @classmethod
    def must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field must not be blank.")
        return v.strip()


class UpdateIcd10EnrichRequest(BaseModel):
    enabled: bool


class ConfigResponse(BaseModel):
    dashscope_base_url: str
    models: dict[str, str]
    icd10_enrich_enabled: bool


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post(
    "/config/dashscope-api-key",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Update the DashScope API key at runtime",
    description=(
        "Proxies the new key to the AI engine service, which applies it "
        "in-process immediately and persists it to a volume-mounted file so "
        "it survives a container restart.  Requires a valid Bearer JWT."
    ),
)
async def update_dashscope_api_key(
    body: UpdateDashscopeApiKeyRequest,
    _user_id: str = Depends(get_current_user_id),
    ai_engine: AiEngineClientProtocol = Depends(get_ai_engine_client),
) -> None:
    try:
        await ai_engine.update_dashscope_key(body.api_key)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to update API key in ai_engine: {exc}",
        ) from exc


@router.patch(
    "/config/dashscope-url",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Update the DashScope base URL at runtime",
    description=(
        "Proxies the new base URL to the AI engine service. "
        "Use to switch between international and CN endpoints without a restart. "
        "Requires a valid Bearer JWT."
    ),
)
async def update_dashscope_url(
    body: UpdateDashscopeUrlRequest,
    _user_id: str = Depends(get_current_user_id),
    ai_engine: AiEngineClientProtocol = Depends(get_ai_engine_client),
) -> None:
    try:
        await ai_engine.update_dashscope_url(body.base_url)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to update DashScope URL in ai_engine: {exc}",
        ) from exc


@router.patch(
    "/config/model",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Override the model ID for a pipeline task at runtime",
    description=(
        "Proxies a per-task model override to the AI engine service. "
        "Valid tasks: ``scribe``, ``clinical``, ``asr``, ``clinical_complex``. "
        "Requires a valid Bearer JWT."
    ),
)
async def update_model(
    body: UpdateModelRequest,
    _user_id: str = Depends(get_current_user_id),
    ai_engine: AiEngineClientProtocol = Depends(get_ai_engine_client),
) -> None:
    try:
        await ai_engine.update_model(body.task, body.model_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to update model in ai_engine: {exc}",
        ) from exc


@router.patch(
    "/config/icd10-enrich",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Toggle ICD-10 context injection at runtime",
    description=(
        "Proxies the toggle to the AI engine service, enabling or disabling "
        "ICD-10 enrichment in the Clinical Agent pipeline without a restart. "
        "Requires a valid Bearer JWT."
    ),
)
async def update_icd10_enrich(
    body: UpdateIcd10EnrichRequest,
    _user_id: str = Depends(get_current_user_id),
    ai_engine: AiEngineClientProtocol = Depends(get_ai_engine_client),
) -> None:
    try:
        await ai_engine.update_icd10_enrich(body.enabled)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to update ICD-10 enrich setting in ai_engine: {exc}",
        ) from exc


@router.get(
    "/config",
    response_model=ConfigResponse,
    summary="Get current AI engine runtime configuration",
    description=(
        "Returns the active DashScope base URL and per-task model overrides "
        "from the AI engine.  Requires a valid Bearer JWT."
    ),
)
async def get_config(
    _user_id: str = Depends(get_current_user_id),
    ai_engine: AiEngineClientProtocol = Depends(get_ai_engine_client),
) -> ConfigResponse:
    try:
        data: AiEngineConfigData = await ai_engine.get_config()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch config from ai_engine: {exc}",
        ) from exc
    return ConfigResponse(
        dashscope_base_url=data.dashscope_base_url,
        models=data.models,
        icd10_enrich_enabled=data.icd10_enrich_enabled,
    )
