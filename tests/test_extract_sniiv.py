import json

import pytest

import src.extract_sniiv as extraction


class FakeResponse:
    def __init__(self, text, parsed_data=None, json_error=None):
        self.text = text
        self.parsed_data = parsed_data
        self.json_error = json_error

    def raise_for_status(self):
        return None

    def json(self):
        if self.json_error:
            raise self.json_error

        return self.parsed_data


def test_extract_saves_valid_json_and_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr(extraction, "SNIIV_RAW_DIR", tmp_path)

    response = FakeResponse(
        text='[{"año": 2026}]',
        parsed_data=[{"año": 2026}],
    )

    monkeypatch.setattr(
        extraction.requests,
        "get",
        lambda url, timeout: response,
    )

    output_file = extraction.extract_year(2026)

    assert output_file.exists()
    assert json.loads(output_file.read_text(encoding="utf-8")) == [
        {"año": 2026}
    ]

    metadata_file = tmp_path / "2026" / "mexico_2026_metadata.json"
    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))

    assert metadata["year"] == 2026
    assert metadata["record_count"] == 1
    assert metadata["status"] == "success"


def test_invalid_json_does_not_replace_existing_file(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(extraction, "SNIIV_RAW_DIR", tmp_path)

    output_dir = tmp_path / "2026"
    output_dir.mkdir()
    output_file = output_dir / "mexico_2026.json"

    original_content = '[{"año": 2026, "dato": "original"}]'
    output_file.write_text(original_content, encoding="utf-8")

    response = FakeResponse(
        text="{json inválido",
        json_error=json.JSONDecodeError(
            "JSON inválido",
            "{json inválido",
            1,
        ),
    )

    monkeypatch.setattr(
        extraction.requests,
        "get",
        lambda url, timeout: response,
    )

    with pytest.raises(json.JSONDecodeError):
        extraction.extract_year(2026, force=True)

    assert output_file.read_text(encoding="utf-8") == original_content


def test_unexpected_json_structure_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(extraction, "SNIIV_RAW_DIR", tmp_path)

    response = FakeResponse(
        text='{"error": "respuesta inesperada"}',
        parsed_data={"error": "respuesta inesperada"},
    )

    monkeypatch.setattr(
        extraction.requests,
        "get",
        lambda url, timeout: response,
    )

    with pytest.raises(ValueError, match="se esperaba una lista"):
        extraction.extract_year(2026)

    output_file = tmp_path / "2026" / "mexico_2026.json"
    assert not output_file.exists()