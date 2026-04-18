from __future__ import annotations

import json
import re

from ai_engine.domain.entities import (
    ClinicalReport,
    ConsultationMetadata,
    MedicalReport,
    Medication,
    MultilingualInstruction,
    MultilingualText,
    NextSteps,
    SOAPNotes,
    TranscriptTurn,
)
from ai_engine.domain.value_objects import SeverityFlag
from ai_engine.processors.text_cleaner import redact_pii

# Strip markdown code fences that the model sometimes wraps around JSON.
_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


class ReporterError(Exception):
    """Raised when the model response cannot be parsed into a MedicalReport."""


class MedicalReporter:
    """Parses the raw LLM response and coerces it into a validated MedicalReport."""

    def parse(self, raw_response: str) -> MedicalReport:
        """Parse *raw_response* into a MedicalReport.

        Args:
            raw_response: Raw string returned by MedicalExtractor.extract().

        Returns:
            A validated MedicalReport domain entity.

        Raises:
            ReporterError: if the response cannot be decoded as JSON.
        """
        cleaned = _CODE_FENCE_RE.sub("", raw_response).strip()
        cleaned = redact_pii(cleaned)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ReporterError(
                f"Model returned non-JSON response: {exc}\n\nRaw: {raw_response[:500]}"
            ) from exc

        return self._build_report(data)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_report(self, data: dict) -> MedicalReport:
        meta_raw = data.get("metadata", {})
        metadata = ConsultationMetadata(
            primary_language=meta_raw.get("primary_language", "unknown"),
            consultation_duration_estimate=meta_raw.get(
                "consultation_duration_estimate"
            ),
            session_id=meta_raw.get("session_id"),
            model=meta_raw.get("model"),
        )

        transcript = [
            TranscriptTurn(
                speaker=t.get("speaker", "Unknown"),
                timestamp=t.get("timestamp"),
                text=t.get("text", ""),
            )
            for t in data.get("transcript", [])
        ]

        cr_raw = data.get("clinical_report", {})
        clinical_report = ClinicalReport(
            chief_complaint=self._multilingual(cr_raw.get("chief_complaint", {})),
            soap_notes=self._soap(cr_raw.get("soap_notes", {})),
            medications=self._medications(cr_raw.get("medications", [])),
            icd10_codes=cr_raw.get("icd10_codes", []),
            severity_flag=self._severity(cr_raw.get("severity_flag", "Low")),
            next_steps=self._next_steps(cr_raw.get("next_steps", {})),
        )

        summary_raw = data.get("multilingual_summary", {})
        multilingual_summary = self._multilingual(summary_raw)

        return MedicalReport(
            metadata=metadata,
            transcript=transcript,
            clinical_report=clinical_report,
            multilingual_summary=multilingual_summary,
        )

    def _multilingual(self, raw: dict) -> MultilingualText:
        return MultilingualText(
            en=raw.get("en") or "Not discussed",
            vn=raw.get("vn") or "Not discussed",
            fr=raw.get("fr") or "Not discussed",
            ar=raw.get("ar") or "Not discussed",
        )

    def _soap(self, raw: dict) -> SOAPNotes:
        return SOAPNotes(
            subjective=self._multilingual(raw.get("subjective", {})),
            objective=self._multilingual(raw.get("objective", {})),
            assessment=self._multilingual(raw.get("assessment", {})),
            plan=self._multilingual(raw.get("plan", {})),
        )

    def _medications(self, raw_list: list) -> list[Medication]:
        meds = []
        for item in raw_list:
            if not isinstance(item, dict):
                continue
            instr_raw = item.get("instructions", {})
            meds.append(
                Medication(
                    name=item.get("name", ""),
                    dosage=item.get("dosage", ""),
                    frequency=item.get("frequency"),
                    route=item.get("route"),
                    instructions=MultilingualInstruction(
                        en=instr_raw.get("en") or "Not discussed",
                        vn=instr_raw.get("vn") or "Not discussed",
                    ),
                )
            )
        return meds

    def _severity(self, raw: str) -> SeverityFlag:
        try:
            return SeverityFlag(raw)
        except ValueError:
            return SeverityFlag.LOW

    def _next_steps(self, raw: dict) -> NextSteps:
        return NextSteps(
            en=raw.get("en") or "Not discussed",
            vn=raw.get("vn") or "Not discussed",
        )
