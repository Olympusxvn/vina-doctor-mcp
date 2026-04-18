from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from backend.api.v1.deps import get_current_user_id, get_user_repo
from backend.api.v1.schemas.user import (
    UserProfileResponse,
    UserProfileUpdateRequest,
)
from backend.domain.repositories import UserRepository

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me", response_model=UserProfileResponse, summary="Get current doctor profile"
)
async def get_me(
    user_id: UUID = Depends(get_current_user_id),
    user_repo: UserRepository = Depends(get_user_repo),
) -> UserProfileResponse:
    user = await user_repo.get_by_id(user_id)
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        specialty=user.specialty,
        license_number=user.license_number,
        phone=user.phone,
        created_at=user.created_at,
    )


@router.patch(
    "/me",
    response_model=UserProfileResponse,
    summary="Update current doctor profile",
)
async def update_me(
    body: UserProfileUpdateRequest,
    user_id: UUID = Depends(get_current_user_id),
    user_repo: UserRepository = Depends(get_user_repo),
) -> UserProfileResponse:
    user = await user_repo.get_by_id(user_id)
    updated = await user_repo.update(
        user.model_copy(
            update={k: v for k, v in body.model_dump().items() if v is not None}
        )
    )
    return UserProfileResponse(
        id=updated.id,
        email=updated.email,
        full_name=updated.full_name,
        specialty=updated.specialty,
        license_number=updated.license_number,
        phone=updated.phone,
        created_at=updated.created_at,
    )
