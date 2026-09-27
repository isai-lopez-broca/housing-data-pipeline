import json
from pathlib import Path

from src.config import SNIIV_RAW_DIR


EXPECTED_COLUMNS = {
    "año",
    "mes",
    "estado",
    "municipio",
    "organismo",
    "destino_credito",
    "sexo",
    "clave_municipio",
    "clave_estado",
    "acciones",
    "monto",
}


def load_json(year: int) -> list[dict]:
    """
    Carga el archivo raw de un año y devuelve sus registros.
    """

    file_path = SNIIV_RAW_DIR / str(year) / f"mexico_{year}.json"

    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def validate_columns(records: list[dict]) -> list[str]:
    """
    Verifica que los registros tengan exactamente las columnas esperadas.
    """

    if not records:
        return ["El archivo no contiene registros."]

    actual_columns = set(records[0].keys())

    errors = []

    missing_columns = EXPECTED_COLUMNS - actual_columns
    extra_columns = actual_columns - EXPECTED_COLUMNS

    if missing_columns:
        errors.append(
            f"Columnas faltantes: {sorted(missing_columns)}"
        )

    if extra_columns:
        errors.append(
            f"Columnas inesperadas: {sorted(extra_columns)}"
        )

    return errors


def validate_values(records: list[dict]) -> list[str]:
    """
    Verifica reglas básicas de calidad sobre los valores.
    """

    errors = []

    for index, record in enumerate(records):
        for column, value in record.items():
            if value is None:
                errors.append(
                    f"Registro {index}: valor nulo en '{column}'."
                )

            elif isinstance(value, str) and not value.strip():
                errors.append(
                    f"Registro {index}: valor vacío en '{column}'."
                )

        acciones = record.get("acciones")
        monto = record.get("monto")

        if acciones is not None and acciones < 0:
            errors.append(
                f"Registro {index}: acciones negativas."
            )

        if monto is not None and monto < 0:
            errors.append(
                f"Registro {index}: monto negativo."
            )

    return errors


def validate_duplicates(records: list[dict]) -> list[str]:
    """
    Verifica que no existan registros duplicados
    según el grano natural identificado para el dataset.
    """

    grain_columns = [
        "año",
        "mes",
        "clave_estado",
        "clave_municipio",
        "organismo",
        "destino_credito",
        "sexo",
    ]

    seen = set()
    duplicates = []

    for index, record in enumerate(records):
        key = tuple(record[column] for column in grain_columns)

        if key in seen:
            duplicates.append(
                f"Registro {index}: clave duplicada {key}"
            )
        else:
            seen.add(key)

    if duplicates:
        return duplicates

    return []


def validate_year(year: int) -> list[str]:
    """
    Ejecuta todas las validaciones disponibles para un año.
    """

    records = load_json(year)

    errors = []

    errors.extend(validate_columns(records))
    errors.extend(validate_values(records))
    errors.extend(validate_duplicates(records))

    return errors

if __name__ == "__main__":
    for year in [2023, 2024, 2025, 2026]:
        print(f"\nValidando {year}...")

        errors = validate_year(year)

        if errors:
            print(f"❌ {year}: {len(errors)} errores encontrados.")

            for error in errors[:10]:
                print(f"  - {error}")
        else:
            print(f"✅ {year}: validación correcta.")
