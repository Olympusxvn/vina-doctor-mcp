from __future__ import annotations

from uuid import UUID


class DomainError(Exception):
    """Base class for all domain errors."""


class NotFoundError(DomainError):
    def __init__(self, entity: str, entity_id: UUID | str) -> None:
        super().__init__(f"{entity} '{entity_id}' not found.")
        self.entity = entity
        self.entity_id = entity_id


class AccessDeniedError(DomainError):
    def __init__(self, message: str = "Access denied.") -> None:
        super().__init__(message)


class DuplicateEmailError(DomainError):
    def __init__(self, email: str) -> None:
        super().__init__(f"Email '{email}' is already registered.")
        self.email = email
