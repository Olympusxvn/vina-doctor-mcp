from __future__ import annotations

import json
import re

from ai_engine.agents.clinical_prompts import (
    CLINICAL_SYSTEM_PROMPT,
    CLINICAL_USER_PROMPT,
)
from ai_engine.domain.entities import (
    ClinicalReport,
    ClinicalResult,
    Diagnostics,
    Medication,
    MultilingualInstruction,
    MultilingualText,
    NextSteps,
    SOAPNotes,
)
from ai_engine.domain.value_objects import SeverityFlag, UrgencyLevel
from ai_engine.infrastructure.clients.qwen_audio_client import QwenAudioClient

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


class ClinicalAgentError(Exception):
    """Raised when the Clinical Agent cannot produce a valid ClinicalResult."""


class ClinicalAgent:
    """Analyses a cleaned transcript and produces a structured clinical report.

    Uses the Qwen model with a specialised clinical analysis prompt.
    Implements ``ClinicalAgentProtocol``.
    """

    def __init__(self, client: QwenAudioClient) -> None:
        self._client = client

    def analyze(self, transcript_text: str, model: str | None = None) -> ClinicalResult:
        if model is not None:
            self._client._model = model  # noqa: SLF001

        user_prompt = CLINICAL_USER_PROMPT.format(transcript=transcript_text)

        messages = [
            {
                "role": "system",
                "content": [{"text": CLINICAL_SYSTEM_PROMPT}],
            },
            {
                "role": "user",
                "content": [{"text": user_prompt}],
            },
        ]

        raw = self._client.call(messages)
        return self._parse(raw)

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse(self, raw_response: str) -> ClinicalResult:
        cleaned = _CODE_FENCE_RE.sub("", raw_response).strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ClinicalAgentError(
                f"Clinical model returned non-JSON response: {exc}\n\nRaw: {raw_response[:500]}"
            ) from exc

        cr_raw = data.get("clinical_report", {})

        clinical_report = ClinicalReport(
            chief_complaint=self._multilingual(cr_raw.get("chief_complaint", {})),
            soap_notes=self._soap(cr_raw.get("soap_notes", {})),
            medications=self._medications(cr_raw.get("medications", [])),
            icd10_codes=cr_raw.get("icd10_codes", []),
            severity_flag=self._severity(cr_raw.get("severity_flag", "Low")),
            urgency_level=self._urgency(cr_raw.get("urgency_level", "Low")),
            diagnostics=self._diagnostics(cr_raw.get("diagnostics")),
            next_steps=self._next_steps(cr_raw.get("next_steps", {})),
        )

        summary_raw = data.get("multilingual_summary", {})

        return ClinicalResult(
            clinical_report=clinical_report,
            multilingual_summary=self._multilingual(summary_raw),
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

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
        meds: list[Medication] = []
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

    def _urgency(self, raw: str) -> UrgencyLevel:
        try:
            return UrgencyLevel(raw)
        except ValueError:
            return UrgencyLevel.LOW

    def _diagnostics(self, raw: dict | None) -> Diagnostics | None:
        if not raw or not isinstance(raw, dict):
            return None
        score = raw.get("confidence_score", 0.0)
        try:
            score = float(score)
        except (TypeError, ValueError):
            score = 0.0
        score = max(0.0, min(1.0, score))
        return Diagnostics(
            primary_diagnosis=raw.get("primary_diagnosis", "Not specified"),
            icd10_code=raw.get("icd10_code", ""),
            confidence_score=score,
        )

    def _next_steps(self, raw: dict) -> NextSteps:
        return NextSteps(
            en=raw.get("en") or "Not discussed",
            vn=raw.get("vn") or "Not discussed",
        )
