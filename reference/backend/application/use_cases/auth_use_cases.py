from __future__ import annotations

from backend.domain.entities import User
from backend.domain.errors import AccessDeniedError, DuplicateEmailError
from backend.domain.repositories import UserRepository


class RegisterUserUseCase:
    def __init__(
        self,
        user_repo: UserRepository,
        hash_password,  # injected callable: (plain: str) -> str
    ) -> None:
        self._user_repo = user_repo
        self._hash_password = hash_password

    async def execute(self, email: str, plain_password: str, full_name: str) -> User:
        existing = await self._user_repo.get_by_email(email)
        if existing is not None:
            raise DuplicateEmailError(email)

        user = User(
            email=email,
            hashed_password=self._hash_password(plain_password),
            full_name=full_name,
        )
        return await self._user_repo.save(user)


class LoginUseCase:
    def __init__(
        self,
        user_repo: UserRepository,
        verify_password,  # (plain: str, hashed: str) -> bool
        create_token,  # (user_id: str) -> str
    ) -> None:
        self._user_repo = user_repo
        self._verify_password = verify_password
        self._create_token = create_token

    async def execute(self, email: str, plain_password: str) -> str:
        user = await self._user_repo.get_by_email(email)
        if user is None or not self._verify_password(
            plain_password, user.hashed_password
        ):
            raise AccessDeniedError("Invalid email or password.")
        return self._create_token(str(user.id))
