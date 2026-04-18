"""ICD-10 Selector Agent.

Receives a cleaned consultation transcript and returns an enriched context
string containing treatment references for the most relevant ICD-10 conditions.

This is a *text-only* LLM call — no audio attachment.  It sits between
the text-cleaning step and the clinical analysis step in the TWO_STEP pipeline.

Fail-safe design: any exception inside ``enrich()`` is caught and logged; the
pipeline continues without enrichment rather than crashing.

Implements ``ICD10SelectorProtocol``.
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING

from ai_engine.agents.icd10_selector_prompts import (
    ICD10_SELECTOR_SYSTEM_PROMPT,
    ICD10_SELECTOR_USER_PROMPT,
)
from ai_engine.infrastructure.clients.qwen_audio_client import QwenAudioClient

if TYPE_CHECKING:
    from ai_engine.infrastructure.medical.icd10_repository import ICD10Repository

logger = logging.getLogger(__name__)

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)

# Maximum transcript characters sent to the selector LLM.
# Long transcripts are truncated from the *end* — symptoms/complaints tend to
# appear early in doctor-patient exchanges.
_MAX_TRANSCRIPT_CHARS = 3_000


class ICD10SelectorError(Exception):
    """Raised internally; caught by ``enrich()`` so callers never see it."""


class ICD10SelectorAgent:
    """Selects relevant ICD-10 codes via an LLM call, then builds enriched context.

    The agent makes ONE cheap text-only call to determine which ICD-10 codes
    are most relevant, then fetches the full treatment details for those codes
    and formats them as a reference block appended to the clinical prompt.

    Args:
        client:     ``QwenAudioClient`` used for the text-only LLM call.
        repository: ``ICD10Repository`` holding the condition catalogue.
        specialty:  Optional specialty filter — if set, only conditions
                    matching this specialty are included in the catalogue
                    index sent to the LLM.
    """

    def __init__(
        self,
        client: QwenAudioClient,
        repository: "ICD10Repository",
        specialty: str | None = None,
    ) -> None:
        self._client = client
        self._repository = repository
        self._specialty = specialty

    # ------------------------------------------------------------------
    # Public API — implements ICD10SelectorProtocol
    # ------------------------------------------------------------------

    def enrich(self, transcript: str) -> str:
        """Return an ICD-10 treatment reference block for the given transcript.

        If selection or enrichment fails for any reason the error is logged at
        WARNING level and an empty string is returned — the pipeline continues
        unaffected.

        Args:
            transcript: Cleaned doctor-patient transcript text.

        Returns:
            Multi-line treatment reference string, or ``""`` on failure / no match.
        """
        try:
            return self._enrich(transcript)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "ICD-10 selector agent failed — continuing without enrichment: %s",
                exc,
            )
            return ""

    # ------------------------------------------------------------------
    # Private implementation
    # ------------------------------------------------------------------

    def _enrich(self, transcript: str) -> str:
        """Internal (can raise — callers use ``enrich()`` for the safe wrapper)."""
        # Step 1: Build a compact catalogue index for the LLM.
        catalogue_index = self._repository.build_selector_index(
            specialty=self._specialty
        )
        if not catalogue_index.strip():
            return ""

        # Step 2: Truncate transcript to keep token cost reasonable.
        truncated = transcript[:_MAX_TRANSCRIPT_CHARS]

        # Step 3: Call the LLM to get the relevant codes.
        selected_codes = self._select_codes(truncated, catalogue_index)
        if not selected_codes:
            return ""

        # Step 4: Fetch full treatment details for the selected codes.
        conditions = self._repository.get_by_codes(selected_codes)
        if not conditions:
            return ""

        # Step 5: Format as a structured reference block.
        return self._format_reference(conditions)

    def _select_codes(self, transcript: str, catalogue_index: str) -> list[str]:
        """Ask the LLM to pick the relevant ICD-10 codes.

        Returns a (possibly empty) list of code strings.
        Raises ``ICD10SelectorError`` on parse failure.
        """
        user_prompt = ICD10_SELECTOR_USER_PROMPT.format(
            transcript=transcript,
            catalogue_index=catalogue_index,
        )

        messages = [
            {
                "role": "system",
                "content": [{"text": ICD10_SELECTOR_SYSTEM_PROMPT}],
            },
            {
                "role": "user",
                "content": [{"text": user_prompt}],
            },
        ]

        raw = self._client.call(messages)

        # Strip code fences if the model wraps its output anyway.
        cleaned = _CODE_FENCE_RE.sub("", raw).strip()

        try:
            codes = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ICD10SelectorError(
                f"ICD-10 selector returned non-JSON: {exc}\n\nRaw: {raw[:300]}"
            ) from exc

        if not isinstance(codes, list):
            raise ICD10SelectorError(
                f"Expected JSON array of codes, got: {type(codes).__name__}"
            )

        # Normalise: keep only non-empty strings, cap at 3.
        return [str(c).strip() for c in codes if str(c).strip()][:3]

    @staticmethod
    def _format_reference(conditions: list[dict]) -> str:
        """Format selected conditions as a treatment reference block.

        The block is designed to be appended to the ClinicalAgent prompt as
        additional context, framed clearly so the LLM knows it is a reference
        rather than part of the transcript.
        """
        lines: list[str] = [
            "--- ICD-10 Treatment Reference (use as clinical guidance, not prescription) ---",
        ]
        for c in conditions:
            lines.append(
                f"\n{c['code']} — {c['name']} (specialty: {c.get('specialty', 'general')})"
            )

            drugs = c.get("drugs", [])
            if drugs:
                lines.append("  Recommended drugs:")
                for drug in drugs:
                    lines.append(f"    • {drug}")

            protocol = c.get("protocol", "")
            if protocol:
                lines.append(f"  Treatment protocol: {protocol}")

            contraindications = c.get("contraindications", "")
            if contraindications:
                lines.append(f"  Contraindications: {contraindications}")

            notes = c.get("notes", "")
            if notes:
                lines.append(f"  Clinical notes: {notes}")

        lines.append("\n--- End of ICD-10 Reference ---")
        return "\n".join(lines)
