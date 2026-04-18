from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator

from ai_engine.application.use_cases.update_api_key_use_case import UpdateApiKeyUseCase
from ai_engine.application.use_cases.update_dashscope_url_use_case import (
    UpdateDashscopeUrlUseCase,
)
from ai_engine.application.use_cases.update_icd10_enrich_use_case import (
    UpdateICD10EnrichUseCase,
)
from ai_engine.application.use_cases.update_model_use_case import UpdateModelUseCase

router = APIRouter(prefix="/v1/config", tags=["config"])


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


class ConfigResponse(BaseModel):
    dashscope_base_url: str
    models: dict[str, str]
    icd10_enrich_enabled: bool


class UpdateICD10EnrichRequest(BaseModel):
    enabled: bool


# ---------------------------------------------------------------------------
# Dependency injection (deferred imports to avoid circular imports)
# ---------------------------------------------------------------------------


def _get_update_key_use_case() -> UpdateApiKeyUseCase:
    from ai_engine.main import get_update_api_key_use_case  # noqa: PLC0415

    return get_update_api_key_use_case()


def _get_update_url_use_case() -> UpdateDashscopeUrlUseCase:
    from ai_engine.main import get_update_dashscope_url_use_case  # noqa: PLC0415

    return get_update_dashscope_url_use_case()


def _get_update_model_use_case() -> UpdateModelUseCase:
    from ai_engine.main import get_update_model_use_case  # noqa: PLC0415

    return get_update_model_use_case()


def _get_config_repo():
    from ai_engine.main import get_config_repo  # noqa: PLC0415

    return get_config_repo()


def _get_update_icd10_enrich_use_case() -> UpdateICD10EnrichUseCase:
    from ai_engine.main import get_update_icd10_enrich_use_case  # noqa: PLC0415

    return get_update_icd10_enrich_use_case()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.patch(
    "/dashscope-api-key",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Update the DashScope API key at runtime",
    description=(
        "Replaces the active DashScope API key in-process **and** persists it "
        "to a config file on the mounted volume so that the new key survives "
        "a container restart.  No restart required."
    ),
)
def update_dashscope_api_key(
    body: UpdateDashscopeApiKeyRequest,
    use_case: UpdateApiKeyUseCase = Depends(_get_update_key_use_case),
) -> None:
    try:
        use_case.execute(body.api_key)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.patch(
    "/dashscope-url",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Update the DashScope base HTTP API URL at runtime",
    description=(
        "Replaces the active DashScope base URL in-process **and** persists it. "
        "Use this to switch between the international endpoint "
        "(``https://dashscope-intl.aliyuncs.com/api/v1``) and the CN endpoint. "
        "No restart required."
    ),
)
def update_dashscope_url(
    body: UpdateDashscopeUrlRequest,
    use_case: UpdateDashscopeUrlUseCase = Depends(_get_update_url_use_case),
) -> None:
    try:
        use_case.execute(body.base_url)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.patch(
    "/model",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Override the model ID for a pipeline task at runtime",
    description=(
        "Persists a model override for the given task (``scribe``, ``clinical``, etc.). "
        "``ModelSelector`` will pick it up on the next request — no restart required. "
        "Valid tasks: ``asr``, ``scribe``, ``clinical``, ``clinical_complex``."
    ),
)
def update_model(
    body: UpdateModelRequest,
    use_case: UpdateModelUseCase = Depends(_get_update_model_use_case),
) -> None:
    try:
        use_case.execute(body.task, body.model_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=ConfigResponse,
    summary="Get current runtime configuration",
    description="Returns the active DashScope base URL, per-task model overrides, and ICD-10 enrichment toggle.",
)
def get_config(
    config_repo=Depends(_get_config_repo),
) -> ConfigResponse:
    data = config_repo.get_all_config()
    return ConfigResponse(
        dashscope_base_url=data["dashscope_base_url"],
        models=data["models"],
        icd10_enrich_enabled=data.get("icd10_enrich_enabled", False),
    )


@router.patch(
    "/icd10-enrich",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Enable or disable ICD-10 context enrichment at runtime",
    description=(
        "Toggles ICD-10 enrichment for the TWO_STEP consultation pipeline. "
        "When enabled, a lightweight LLM call selects the most relevant ICD-10 "
        "codes from the catalogue and injects treatment guidelines into the "
        "clinical agent prompt.  Change takes effect on the next request — "
        "no restart required."
    ),
)
def update_icd10_enrich(
    body: UpdateICD10EnrichRequest,
    use_case: UpdateICD10EnrichUseCase = Depends(_get_update_icd10_enrich_use_case),
) -> None:
    use_case.execute(enabled=body.enabled)
