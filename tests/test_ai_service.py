import json
import pytest

from app.services.ai_service import AIService, AIServiceError


def make_response_content(json_obj):
    return {"choices": [{"message": {"content": json.dumps(json_obj)}}]}


def test_identify_best_moments_no_api_key():
    svc = AIService()
    with pytest.raises(AIServiceError):
        svc.identify_best_moments("some transcription")


def test_clean_json_response_extracts_object():
    svc = AIService()
    text = '```json\n{"moments": [{"start": 1, "end": 4, "label": "a"}, {"start": 10, "end": 14, "label": "b"}]}\n```'
    cleaned = svc._clean_json_response(text)
    parsed = json.loads(cleaned)
    assert "moments" in parsed


def test_extract_first_json_object_with_extra_text():
    svc = AIService()
    text = 'Some explanation before {"moments": [{"start":0,"end":3,"label":"x"}], "extra": 1} and after'
    obj = svc._extract_first_json_object(text)
    assert obj is not None
    parsed = json.loads(obj)
    assert parsed.get("moments")
