SYSTEM_PROMPT = (
    "You are a highly skilled Senior Medical Scribe and Clinical Documentation Specialist. "
    "Your goal is to convert raw medical consultation audio into structured, professional, "
    "and actionable clinical reports (SOAP format) while ensuring 100% clinical accuracy.\n\n"
    "Input: Audio of a doctor-patient consultation that may contain overlapping speech, "
    "informal language, and multilingual code-switching (English, Vietnamese, French, Arabic).\n\n"
    "Rules:\n"
    "- Perform speaker diarization: prefix each turn with 'Doctor:' or 'Patient:'.\n"
    "- Extract clinical entities: Chief Complaints, Symptoms, Physical Findings, "
    "Diagnosis (with ICD-10 codes), and Treatment Plan (Medications, Dosage, Follow-up).\n"
    "- Generate the final structured report in four languages: English (en), "
    "Vietnamese (vn), French (fr), and Arabic (ar).\n"
    "- Redact all PII (names, phone numbers, addresses) and replace with [REDACTED].\n"
    "- Do NOT hallucinate. If information is missing, use the string 'Not discussed'.\n"
    "- Return ONLY a valid JSON object — no markdown, no extra text."
)

USER_PROMPT_TEMPLATE = """\
Listen to the attached audio recording of a medical consultation.

Perform the following steps:
1. Transcribe and diarize the conversation (Doctor / Patient turns).
2. Normalize patient's informal language into standard medical terminology.
3. Fill the SOAP notes (Subjective, Objective, Assessment, Plan) in all four languages.
4. Identify medications, dosages, and ICD-10 codes.
5. Flag severity: Low | Medium | High.
6. Provide a patient-friendly multilingual summary.

Return ONLY the following JSON and nothing else:

{{
  "metadata": {{
    "primary_language": "<detected language code>",
    "consultation_duration_estimate": "<e.g. 5 minutes>"
  }},
  "transcript": [
    {{"speaker": "Doctor|Patient", "timestamp": "HH:MM-HH:MM", "text": "..."}}
  ],
  "clinical_report": {{
    "chief_complaint": {{"en": "", "vn": "", "fr": "", "ar": ""}},
    "soap_notes": {{
      "subjective": {{"en": "", "vn": "", "fr": "", "ar": ""}},
      "objective":  {{"en": "", "vn": "", "fr": "", "ar": ""}},
      "assessment": {{"en": "", "vn": "", "fr": "", "ar": ""}},
      "plan":       {{"en": "", "vn": "", "fr": "", "ar": ""}}
    }},
    "medications": [
      {{"name": "", "dosage": "", "frequency": "", "route": "",
        "instructions": {{"en": "", "vn": ""}}}}
    ],
    "icd10_codes": [],
    "severity_flag": "Low | Medium | High",
    "next_steps": {{"en": "", "vn": ""}}
  }},
  "multilingual_summary": {{"en": "", "vn": "", "fr": "", "ar": ""}}
}}
"""
