from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.v1.deps import get_login_use_case, get_register_use_case
from backend.api.v1.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from backend.application.use_cases.auth_use_cases import (
    LoginUseCase,
    RegisterUserUseCase,
)
from backend.domain.errors import AccessDeniedError, DuplicateEmailError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new doctor account",
)
async def register(
    body: RegisterRequest,
    use_case: RegisterUserUseCase = Depends(get_register_use_case),
    login_use_case: LoginUseCase = Depends(get_login_use_case),
) -> TokenResponse:
    try:
        await use_case.execute(
            email=body.email,
            plain_password=body.password,
            full_name=body.full_name,
        )
    except DuplicateEmailError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc

    # Auto-login after registration
    token = await login_use_case.execute(email=body.email, plain_password=body.password)
    return TokenResponse(access_token=token)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Obtain a JWT access token",
)
async def login(
    body: LoginRequest,
    use_case: LoginUseCase = Depends(get_login_use_case),
) -> TokenResponse:
    try:
        token = await use_case.execute(email=body.email, plain_password=body.password)
    except AccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return TokenResponse(access_token=token)
