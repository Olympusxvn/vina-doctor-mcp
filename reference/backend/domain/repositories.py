from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from backend.domain.entities import Consultation, Report, User
from backend.domain.value_objects import ConsultationStatus


class UserRepository(ABC):
    @abstractmethod
    async def save(self, user: User) -> User: ...

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def update(self, user: User) -> User: ...


class ConsultationRepository(ABC):
    @abstractmethod
    async def save(self, consultation: Consultation) -> Consultation: ...

    @abstractmethod
    async def get_by_id(self, consultation_id: UUID) -> Consultation: ...

    @abstractmethod
    async def list_by_doctor(
        self,
        doctor_id: UUID,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Consultation]: ...

    @abstractmethod
    async def update_status(
        self,
        consultation_id: UUID,
        status: ConsultationStatus,
    ) -> Consultation: ...


class ReportRepository(ABC):
    @abstractmethod
    async def save(self, report: Report) -> Report: ...

    @abstractmethod
    async def get_by_consultation(self, consultation_id: UUID) -> Report: ...
