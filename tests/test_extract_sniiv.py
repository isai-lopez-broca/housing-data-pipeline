import json

import pytest
import requests

import src.extract_sniiv as extraction


class FakeResponse:
    """Simula una respuesta HTTP para las pruebas de extracción."""

    def __init__(
        self,
        text,
        parsed_data=None,
        json_error=None,
        status_code=200,
    ):
        self.text = text
        self.parsed_data = parsed_data
        self.json_error = json_error
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(
                f"HTTP {self.status_code}"
            )

    def json(self):
        if self.json_error:
            raise self.json_error

        return self.parsed_data


def test_extract_saves_valid_json_and_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr(extraction, "SNIIV_RAW_DIR", tmp_path)

    valid_record = {
        "año": 2026,
        "mes": 1,
        "estado": "Quintana Roo",
        "municipio": "Benito Juárez",
        "organismo": "Organismo de prueba",
        "destino_credito": "Adquisición",
        "sexo": "No distribuido",
        "clave_municipio": 23005,
        "clave_estado": 23,
        "acciones": 10,
        "monto": 150000.0,
    }

    response = FakeResponse(
        text=json.dumps([valid_record], ensure_ascii=False),
        parsed_data=[valid_record],
    )

    monkeypatch.setattr(
        extraction.requests,
        "get",
        lambda url, timeout: response,
    )

    output_file = extraction.extract_year(2026)

    assert output_file.exists()

    saved_records = json.loads(
        output_file.read_text(encoding="utf-8")
    )
    assert saved_records == [valid_record]

    metadata_file = (
        tmp_path / "2026" / "mexico_2026_metadata.json"
    )
    metadata = json.loads(
        metadata_file.read_text(encoding="utf-8")
    )

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

    output_file.write_text(
        original_content,
        encoding="utf-8",
    )

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


def test_unexpected_json_structure_is_rejected(
    tmp_path,
    monkeypatch,
):
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

    with pytest.raises(TypeError, match="se esperaba una lista"):
        extraction.extract_year(2026)

    output_file = tmp_path / "2026" / "mexico_2026.json"
    assert not output_file.exists()


def test_empty_response_does_not_replace_existing_file(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(extraction, "SNIIV_RAW_DIR", tmp_path)

    output_dir = tmp_path / "2026"
    output_dir.mkdir()

    output_file = output_dir / "mexico_2026.json"
    original_content = '[{"año": 2026, "dato": "original"}]'

    output_file.write_text(
        original_content,
        encoding="utf-8",
    )

    response = FakeResponse(
        text="[]",
        parsed_data=[],
    )

    monkeypatch.setattr(
        extraction.requests,
        "get",
        lambda url, timeout: response,
    )

    with pytest.raises(ValueError, match="Respuesta vacía"):
        extraction.extract_year(2026, force=True)

    assert output_file.read_text(encoding="utf-8") == original_content

    temporary_file = output_file.with_suffix(".json.tmp")
    assert not temporary_file.exists()


def test_missing_required_column_does_not_replace_existing_file(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(extraction, "SNIIV_RAW_DIR", tmp_path)

    output_dir = tmp_path / "2026"
    output_dir.mkdir()

    output_file = output_dir / "mexico_2026.json"
    original_content = '[{"año": 2026, "dato": "original"}]'

    output_file.write_text(
        original_content,
        encoding="utf-8",
    )

    # Registro incompleto: falta la columna obligatoria "monto".
    incomplete_record = {
        "año": 2026,
        "mes": 1,
        "estado": "Quintana Roo",
        "municipio": "Benito Juárez",
        "organismo": "Organismo de prueba",
        "destino_credito": "Adquisición",
        "sexo": "No distribuido",
        "clave_municipio": 23005,
        "clave_estado": 23,
        "acciones": 10,
    }

    response = FakeResponse(
        text=json.dumps([incomplete_record], ensure_ascii=False),
        parsed_data=[incomplete_record],
    )

    monkeypatch.setattr(
        extraction.requests,
        "get",
        lambda url, timeout: response,
    )

    with pytest.raises(
        ValueError,
        match="registro 0 sin columnas requeridas",
    ):
        extraction.extract_year(2026, force=True)

    # El archivo anterior debe conservarse intacto.
    assert output_file.read_text(encoding="utf-8") == original_content

    # No debe quedar un archivo temporal.
    temporary_file = output_file.with_suffix(".json.tmp")
    assert not temporary_file.exists()


def test_extract_retries_after_temporary_http_error(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(extraction, "SNIIV_RAW_DIR", tmp_path)
    monkeypatch.setattr(extraction.time, "sleep", lambda _: None)

    valid_record = {
        "año": 2026,
        "mes": 1,
        "estado": "Quintana Roo",
        "municipio": "Benito Juárez",
        "organismo": "Organismo de prueba",
        "destino_credito": "Adquisición",
        "sexo": "No distribuido",
        "clave_municipio": 23005,
        "clave_estado": 23,
        "acciones": 10,
        "monto": 150000.0,
    }

    responses = [
        FakeResponse(
            text="Error temporal",
            status_code=503,
        ),
        FakeResponse(
            text=json.dumps([valid_record], ensure_ascii=False),
            parsed_data=[valid_record],
        ),
    ]

    calls = []

    def fake_get(url, **_):
        calls.append(url)
        return responses.pop(0)

    monkeypatch.setattr(
        extraction.requests,
        "get",
        fake_get,
    )

    output_file = extraction.extract_year(2026)

    assert output_file.exists()
    assert len(calls) == 2

    saved_records = json.loads(
        output_file.read_text(encoding="utf-8")
    )
    assert saved_records == [valid_record]


def test_connection_error_retries_and_recovers(monkeypatch):
    monkeypatch.setattr(extraction.time, "sleep", lambda _: None)

    responses = [
        requests.exceptions.ConnectionError("Conexión interrumpida"),
        FakeResponse(
            text="[]",
            parsed_data=[],
        ),
    ]

    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        result = responses.pop(0)

        if isinstance(result, Exception):
            raise result

        return result

    monkeypatch.setattr(extraction.requests, "get", fake_get)

    response = extraction.get_sniiv_response("https://example.com")

    assert response.status_code == 200
    assert len(calls) == 2


def test_http_retries_stop_after_max_attempts(monkeypatch):
    delays = []
    calls = []

    monkeypatch.setattr(
        extraction.time,
        "sleep",
        lambda seconds: delays.append(seconds),
    )

    def fake_get(url, **kwargs):
        calls.append(url)
        return FakeResponse(
            text="Servicio no disponible",
            status_code=503,
        )

    monkeypatch.setattr(extraction.requests, "get", fake_get)

    with pytest.raises(
        requests.exceptions.HTTPError,
        match="HTTP 503",
    ):
        extraction.get_sniiv_response("https://example.com")

    assert len(calls) == extraction.MAX_HTTP_ATTEMPTS
    assert delays == [2, 4]


def test_non_retryable_http_error_fails_immediately(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        return FakeResponse(
            text="Recurso no encontrado",
            status_code=404,
        )

    monkeypatch.setattr(extraction.requests, "get", fake_get)

    with pytest.raises(
        requests.exceptions.HTTPError,
        match="HTTP 404",
    ):
        extraction.get_sniiv_response("https://example.com")

    assert len(calls) == 1
