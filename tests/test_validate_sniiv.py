from src.validate_sniiv import (
    EXPECTED_COLUMNS,
    validate_columns,
    validate_values,
    validate_duplicates,
)


def make_valid_record():
    """Construye un registro válido para las pruebas."""

    return {
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


def test_validate_columns_accepts_valid_record():
    record = make_valid_record()

    assert set(record) == EXPECTED_COLUMNS
    assert validate_columns([record]) == []


def test_validate_columns_detects_missing_column_in_second_record():
    first_record = make_valid_record()
    second_record = make_valid_record()
    del second_record["monto"]

    errors = validate_columns([first_record, second_record])

    assert any("Registro 1" in error for error in errors)
    assert any("monto" in error for error in errors)


def test_validate_values_reports_non_numeric_actions():
    record = make_valid_record()
    record["acciones"] = "desconocido"

    errors = validate_values([record])

    assert any("acciones" in error for error in errors)
    assert any("numérico" in error.lower() for error in errors)


def test_validate_values_reports_non_numeric_amount():
    record = make_valid_record()
    record["monto"] = "sin información"

    errors = validate_values([record])

    assert any("monto" in error for error in errors)
    assert any("numérico" in error.lower() for error in errors)


def test_validate_values_rejects_month_outside_valid_range():
    record = make_valid_record()
    record["mes"] = 13

    errors = validate_values([record])

    assert any("mes" in error.lower() for error in errors)


def test_validate_values_rejects_negative_actions():
    record = make_valid_record()
    record["acciones"] = -1

    errors = validate_values([record])

    assert any("acciones negativas" in error.lower() for error in errors)


def test_validate_values_accepts_valid_record():
    record = make_valid_record()

    assert validate_values([record]) == []


def test_validate_duplicates_accepts_unique_records():
    first_record = make_valid_record()
    second_record = make_valid_record()
    second_record["municipio"] = "Otro municipio"
    second_record["clave_municipio"] = 23006

    assert validate_duplicates([first_record, second_record]) == []