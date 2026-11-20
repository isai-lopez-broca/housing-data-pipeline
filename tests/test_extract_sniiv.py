import json
import pathlib

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


def test_extract_saves_valid_json_and_metadata(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
):
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
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
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
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
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
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
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
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
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

    assert output_file.read_text(encoding="utf-8") == original_content

    temporary_file = output_file.with_suffix(".json.tmp")

    assert not temporary_file.exists()


def test_extract_retries_after_temporary_http_error(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
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

    def fake_get(url, **kwargs):
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


def test_connection_error_retries_and_recovers(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(extraction.time, "sleep", lambda _: None)

    responses = [
        requests.exceptions.ConnectionError(
            "Conexión interrumpida"
        ),
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

    monkeypatch.setattr(
        extraction.requests,
        "get",
        fake_get,
    )

    response = extraction.get_sniiv_response(
        "https://example.com"
    )

    assert response.status_code == 200
    assert len(calls) == 2


def test_http_retries_stop_after_max_attempts(
    monkeypatch: pytest.MonkeyPatch,
):
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

    monkeypatch.setattr(
        extraction.requests,
        "get",
        fake_get,
    )

    with pytest.raises(
        requests.exceptions.HTTPError,
        match="HTTP 503",
    ):
        extraction.get_sniiv_response(
            "https://example.com"
        )

    assert len(calls) == extraction.MAX_HTTP_ATTEMPTS
    assert delays == [2, 4]


def test_non_retryable_http_error_fails_immediately(
    monkeypatch: pytest.MonkeyPatch,
):
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)

        return FakeResponse(
            text="Recurso no encontrado",
            status_code=404,
        )

    monkeypatch.setattr(
        extraction.requests,
        "get",
        fake_get,
    )

    with pytest.raises(
        requests.exceptions.HTTPError,
        match="HTTP 404",
    ):
        extraction.get_sniiv_response(
            "https://example.com"
        )

    assert len(calls) == 1


@pytest.mark.parametrize(
    "invalid_year",
    [
        2025,
        2026.0,
        True,
        "2025",
    ],
)
def test_extract_rejects_invalid_year(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_year,
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

    invalid_record = {
        "año": invalid_year,
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
        text=json.dumps([invalid_record], ensure_ascii=False),
        parsed_data=[invalid_record],
    )

    monkeypatch.setattr(
        extraction.requests,
        "get",
        lambda url, timeout: response,
    )

    with pytest.raises(
        ValueError,
        match="año inválido|distinto del solicitado",
    ):
        extraction.extract_year(2026, force=True)

    assert output_file.read_text(encoding="utf-8") == original_content


def test_extract_rejects_duplicate_natural_key(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(extraction, "SNIIV_RAW_DIR", tmp_path)

    record = {
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

    records = [record, record.copy()]

    response = FakeResponse(
        text=json.dumps(records, ensure_ascii=False),
        parsed_data=records,
    )

    monkeypatch.setattr(
        extraction.requests,
        "get",
        lambda url, timeout: response,
    )

    with pytest.raises(
        ValueError,
        match="clave natural duplicada",
    ):
        extraction.extract_year(2026)


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("acciones", -1),
        ("acciones", 1.5),
        ("monto", -100.0),
        ("monto", float("nan")),
    ],
)
def test_extract_rejects_invalid_numeric_values(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    field,
    invalid_value,
):
    monkeypatch.setattr(extraction, "SNIIV_RAW_DIR", tmp_path)

    record = {
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

    record[field] = invalid_value

    response = FakeResponse(
        text=json.dumps([record], ensure_ascii=False),
        parsed_data=[record],
    )

    monkeypatch.setattr(
        extraction.requests,
        "get",
        lambda url, timeout: response,
    )

    with pytest.raises(ValueError):
        extraction.extract_year(2026)

    output_file = tmp_path / "2026" / "mexico_2026.json"

    assert not output_file.exists()


def test_extract_restores_previous_files_when_metadata_promotion_fails(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(extraction, "SNIIV_RAW_DIR", tmp_path)

    output_dir = tmp_path / "2026"
    output_dir.mkdir()

    output_file = output_dir / "mexico_2026.json"
    metadata_file = output_dir / "mexico_2026_metadata.json"

    original_json = '[{"dato": "original"}]'
    original_metadata = '{"status": "previous"}'

    output_file.write_text(original_json, encoding="utf-8")
    metadata_file.write_text(original_metadata, encoding="utf-8")

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

    original_replace = extraction.os.replace
    failed = False

    def fake_replace(source, destination):
        nonlocal failed

        source = str(source)
        destination = str(destination)

        if (
            source.endswith("mexico_2026_metadata.json.tmp")
            and destination.endswith("mexico_2026_metadata.json")
            and not failed
        ):
            failed = True
            raise OSError(
                "Fallo simulado al promover metadatos"
            )

        return original_replace(source, destination)

    monkeypatch.setattr(
        extraction.os,
        "replace",
        fake_replace,
    )

    with pytest.raises(
        OSError,
        match="Fallo simulado al promover metadatos",
    ):
        extraction.extract_year(2026, force=True)

    assert output_file.read_text(encoding="utf-8") == original_json
    assert metadata_file.read_text(encoding="utf-8") == original_metadata

    assert not (output_dir / "mexico_2026.json.tmp").exists()
    assert not (output_dir / "mexico_2026_metadata.json.tmp").exists()

    assert not (output_dir / "mexico_2026.json.bak").exists()
    assert not (output_dir / "mexico_2026_metadata.json.bak").exists()


def test_extract_attempts_metadata_restore_when_json_restore_fails(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
):
    output_dir = tmp_path / "2026"
    output_dir.mkdir()

    output_file = output_dir / "mexico_2026.json"
    metadata_file = output_dir / "mexico_2026_metadata.json"

    backup_file = output_dir / "mexico_2026.json.bak"
    backup_metadata = output_dir / "mexico_2026_metadata.json.bak"

    output_file.write_text(
        '[{"dato": "json anterior"}]',
        encoding="utf-8",
    )

    metadata_file.write_text(
        '{"version": "anterior"}',
        encoding="utf-8",
    )

    monkeypatch.setattr(extraction, "SNIIV_RAW_DIR", tmp_path)

    valid_record = {
        "año": 2026,
        "mes": 1,
        "estado": "Quintana Roo",
        "municipio": "Benito Juárez",
        "organismo": "INFONAVIT",
        "destino_credito": "Nueva",
        "sexo": "Total",
        "clave_municipio": 23005,
        "clave_estado": 23,
        "acciones": 10,
        "monto": 1000,
    }

    response = FakeResponse(
        text=json.dumps([valid_record], ensure_ascii=False),
        parsed_data=[valid_record],
    )

    monkeypatch.setattr(
        extraction,
        "get_sniiv_response",
        lambda url: response,
    )

    original_replace = extraction.os.replace

    def simulated_replace(source, destination):
        source = pathlib.Path(source)
        destination = pathlib.Path(destination)

        if (
            source.name == "mexico_2026_metadata.json.tmp"
            and destination == metadata_file
        ):
            raise OSError(
                "Fallo simulado al promover metadatos"
            )

        if source == backup_file and destination == output_file:
            raise OSError(
                "Fallo simulado al recuperar el JSON"
            )

        return original_replace(source, destination)

    monkeypatch.setattr(
        extraction.os,
        "replace",
        simulated_replace,
    )

    with pytest.raises(
        OSError,
        match="Fallo simulado al promover metadatos",
    ):
        extraction.extract_year(2026, force=True)

    assert backup_file.exists()

    assert metadata_file.exists()
    assert metadata_file.read_text(encoding="utf-8") == (
        '{"version": "anterior"}'
    )

    assert not backup_metadata.exists()

    assert not list(output_dir.glob("*.tmp"))


def test_extract_removes_new_json_when_metadata_promotion_fails(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
):
    output_dir = tmp_path / "2026"
    output_dir.mkdir()

    output_file = output_dir / "mexico_2026.json"
    metadata_file = output_dir / "mexico_2026_metadata.json"

    monkeypatch.setattr(extraction, "SNIIV_RAW_DIR", tmp_path)

    valid_record = {
        "año": 2026,
        "mes": 1,
        "estado": "Quintana Roo",
        "municipio": "Benito Juárez",
        "organismo": "INFONAVIT",
        "destino_credito": "Nueva",
        "sexo": "Total",
        "clave_municipio": 23005,
        "clave_estado": 23,
        "acciones": 10,
        "monto": 1000,
    }

    response = FakeResponse(
        text=json.dumps([valid_record], ensure_ascii=False),
        parsed_data=[valid_record],
    )

    monkeypatch.setattr(
        extraction,
        "get_sniiv_response",
        lambda url: response,
    )

    original_replace = extraction.os.replace

    def simulated_replace(source, destination):
        source = pathlib.Path(source)
        destination = pathlib.Path(destination)

        if (
            source.name == "mexico_2026_metadata.json.tmp"
            and destination == metadata_file
        ):
            raise OSError(
                "Fallo simulado al promover metadatos"
            )

        return original_replace(source, destination)

    monkeypatch.setattr(
        extraction.os,
        "replace",
        simulated_replace,
    )

    with pytest.raises(
        OSError,
        match="Fallo simulado al promover metadatos",
    ):
        extraction.extract_year(2026, force=True)

    assert not output_file.exists()
    assert not metadata_file.exists()

    assert not (output_dir / "mexico_2026.json.bak").exists()
    assert not (output_dir / "mexico_2026_metadata.json.bak").exists()

    assert not list(output_dir.glob("*.tmp"))


@pytest.mark.parametrize(
    "backup_name",
    [
        "mexico_2026.json.bak",
        "mexico_2026_metadata.json.bak",
    ],
)
def test_extract_does_not_overwrite_existing_backup(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    backup_name: str,
):
    output_dir = tmp_path / "2026"
    output_dir.mkdir()

    output_file = output_dir / "mexico_2026.json"
    metadata_file = output_dir / "mexico_2026_metadata.json"
    backup_file = output_dir / backup_name

    output_file.write_text(
        '[{"dato": "json anterior"}]',
        encoding="utf-8",
    )

    metadata_file.write_text(
        '{"version": "anterior"}',
        encoding="utf-8",
    )

    backup_file.write_text(
        '{"respaldo": "no sobrescribir"}',
        encoding="utf-8",
    )

    original_json = output_file.read_text(encoding="utf-8")
    original_metadata = metadata_file.read_text(encoding="utf-8")
    original_backup = backup_file.read_text(encoding="utf-8")

    monkeypatch.setattr(extraction, "SNIIV_RAW_DIR", tmp_path)

    def unexpected_request(url):
        raise AssertionError(
            "No debe realizarse una petición si existe un respaldo pendiente."
        )

    monkeypatch.setattr(
        extraction,
        "get_sniiv_response",
        unexpected_request,
    )

    with pytest.raises(
        FileExistsError,
        match="respaldos pendientes",
    ):
        extraction.extract_year(2026, force=True)

    assert output_file.read_text(encoding="utf-8") == original_json
    assert metadata_file.read_text(encoding="utf-8") == original_metadata
    assert backup_file.read_text(encoding="utf-8") == original_backup

    assert not list(output_dir.glob("*.tmp"))



# ==========================================
# FALLOS DURANTE LA CREACIÓN DE BACKUPS
# ==========================================

@pytest.mark.parametrize(
    "failed_backup",
    ["json", "metadata"],
)
def test_extract_restores_files_when_backup_creation_fails(
    tmp_path,
    monkeypatch,
    failed_backup,
):
    import json
    import os

    import src.extract_sniiv as extraction

    year = 2026
    output_dir = tmp_path / str(year)
    output_dir.mkdir(parents=True)

    output_file = output_dir / f"mexico_{year}.json"
    metadata_file = (
        output_dir / f"mexico_{year}_metadata.json"
    )

    backup_file = output_dir / f"mexico_{year}.json.bak"
    backup_metadata = (
        output_dir / f"mexico_{year}_metadata.json.bak"
    )

    old_json = b'{"previous": "json"}'
    old_metadata = b'{"previous": "metadata"}'

    output_file.write_bytes(old_json)
    metadata_file.write_bytes(old_metadata)

    # Utilizar la misma estructura de registros válidos
    # que emplean las pruebas existentes.
    records = [
        {
            "año": 2026,
            "mes": "enero",
            "estado": "Quintana Roo",
            "municipio": "Benito Juárez",
            "organismo": "INFONAVIT",
            "destino_credito": "Compra",
            "sexo": "Hombre",
            "clave_municipio": "005",
            "clave_estado": "23",
            "acciones": 10,
            "monto": 1000000,
        }
    ]

    class FakeResponse:
        def json(self):
            return records

    monkeypatch.setattr(
        extraction,
        "SNIIV_RAW_DIR",
        tmp_path,
    )

    monkeypatch.setattr(
        extraction,
        "get_sniiv_response",
        lambda url: FakeResponse(),
    )

    real_replace = os.replace

    target_backup = (
        backup_file
        if failed_backup == "json"
        else backup_metadata
    )

    def fail_selected_backup(source, destination):
        if str(destination) == str(target_backup):
            raise OSError(
                f"Simulated {failed_backup} backup failure"
            )

        return real_replace(source, destination)

    monkeypatch.setattr(
        extraction.os,
        "replace",
        fail_selected_backup,
    )

    with pytest.raises(
        OSError,
        match=f"Simulated {failed_backup} backup failure",
    ):
        extraction.extract_year(year, force=True)

    # Los archivos anteriores deben permanecer intactos.
    assert output_file.read_bytes() == old_json
    assert metadata_file.read_bytes() == old_metadata

    # No deben quedar respaldos ni temporales
    # cuando la recuperación se completa.
    assert not backup_file.exists()
    assert not backup_metadata.exists()

    assert not (
        output_dir / f"mexico_{year}.json.tmp"
    ).exists()

    assert not (
        output_dir / f"mexico_{year}_metadata.json.tmp"
    ).exists()
