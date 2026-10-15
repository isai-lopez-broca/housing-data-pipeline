import json
import math

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

GRAIN_COLUMNS = [
    "año",
    "mes",
    "clave_estado",
    "clave_municipio",
    "organismo",
    "destino_credito",
    "sexo",
]


def load_json(year: int) -> list[dict]:
    """
    Carga el archivo raw de un año y devuelve sus registros.
    """

    file_path = SNIIV_RAW_DIR / str(year) / f"mexico_{year}.json"

    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def is_valid_number(value) -> bool:
    """
    Comprueba que un valor sea numérico y finito.
    Los booleanos no se consideran números válidos.
    """

    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def validate_columns(records: list[dict]) -> list[str]:
    """
    Verifica que todos los registros tengan exactamente
    las columnas esperadas.
    """

    if not records:
        return ["El archivo no contiene registros."]

    errors = []

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(
                f"Registro {index}: se esperaba un objeto JSON."
            )
            continue

        actual_columns = set(record.keys())

        missing_columns = EXPECTED_COLUMNS - actual_columns
        extra_columns = actual_columns - EXPECTED_COLUMNS

        if missing_columns:
            errors.append(
                f"Registro {index}: columnas faltantes: "
                f"{sorted(missing_columns)}."
            )

        if extra_columns:
            errors.append(
                f"Registro {index}: columnas inesperadas: "
                f"{sorted(extra_columns)}."
            )

    return errors


def validate_values(records: list[dict]) -> list[str]:
    """
    Verifica reglas básicas de calidad sobre los valores.
    """

    errors = []

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            continue

        # 1. Detectar valores nulos y textos vacíos.
        for column, value in record.items():
            if value is None:
                errors.append(
                    f"Registro {index}: valor nulo en '{column}'."
                )

            elif isinstance(value, str) and not value.strip():
                errors.append(
                    f"Registro {index}: valor vacío en '{column}'."
                )

        # 2. Validar año y mes.
        year = record.get("año")

        if year is not None:
            if (
                not isinstance(year, int)
                or isinstance(year, bool)
                or year <= 0
            ):
                errors.append(
                    f"Registro {index}: año no es un entero válido."
                )

        month = record.get("mes")

        if month is not None:
            if (
                not isinstance(month, int)
                or isinstance(month, bool)
                or not 1 <= month <= 12
            ):
                errors.append(
                    f"Registro {index}: mes fuera del rango válido 1-12."
                )

        # 3. Validar acciones.
        actions = record.get("acciones")

        if actions is not None:
            if not is_valid_number(actions):
                errors.append(
                    f"Registro {index}: valor no numérico "
                    "o no finito en 'acciones'."
                )
            elif actions < 0:
                errors.append(
                    f"Registro {index}: acciones negativas."
                )

        # 4. Validar monto.
        amount = record.get("monto")

        if amount is not None:
            if not is_valid_number(amount):
                errors.append(
                    f"Registro {index}: valor no numérico "
                    "o no finito en 'monto'."
                )
            elif amount < 0:
                errors.append(
                    f"Registro {index}: monto negativo."
                )

    return errors


def validate_duplicates(records: list[dict]) -> list[str]:
    """
    Verifica que no existan registros duplicados
    según el grano natural del dataset.
    """

    seen = set()
    errors = []

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            continue

        missing_columns = [
            column
            for column in GRAIN_COLUMNS
            if column not in record
        ]

        if missing_columns:
            errors.append(
                f"Registro {index}: no se puede comprobar "
                f"duplicados; faltan claves: {sorted(missing_columns)}."
            )
            continue

        key = tuple(record[column] for column in GRAIN_COLUMNS)

        try:
            if key in seen:
                errors.append(
                    f"Registro {index}: clave duplicada {key}."
                )
            else:
                seen.add(key)

        except TypeError:
            errors.append(
                f"Registro {index}: las claves del grano "
                "contienen valores no válidos."
            )

    return errors


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