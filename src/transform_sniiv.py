import json
import math
import os
import re
import tempfile
from numbers import Integral, Real

import pandas as pd

from src.config import SNIIV_PROCESSED_DIR, SNIIV_RAW_DIR, SNIIV_YEARS

EXPECTED_COLUMNS = [
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
]

TEXT_COLUMNS = [
    "mes",
    "estado",
    "municipio",
    "organismo",
    "destino_credito",
    "sexo",
    "clave_municipio",
    "clave_estado",
]

MONTH_MAP = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

INT64_MAX = 2**63 - 1


def validate_year_argument(year: int) -> None:
    """Valida el año solicitado para procesar un archivo."""

    if (
        isinstance(year, bool)
        or not isinstance(year, int)
        or not 1900 <= year <= 2200
    ):
        raise ValueError(
            "El año debe ser un entero entre 1900 y 2200."
        )


def normalize_year(value: object) -> int:
    """Convierte un año válido a entero sin aceptar decimales."""

    if isinstance(value, bool):
        raise ValueError("Año booleano inválido.")  # noqa: TRY004

    if isinstance(value, Integral):
        year = int(value)
    elif isinstance(value, str):
        text = value.strip()

        if not re.fullmatch(r"[0-9]+", text):
            raise ValueError("Formato de año inválido.")

        year = int(text)
    else:
        raise ValueError("Tipo de año inválido.")  # noqa: TRY004

    if not 1900 <= year <= 2200:
        raise ValueError("Año fuera del rango permitido.")

    return year


def normalize_actions(value: object) -> int:
    """Valida acciones como entero no negativo dentro de int64."""

    if isinstance(value, bool):
        raise ValueError("Acciones booleanas inválidas.")  # noqa: TRY004

    if isinstance(value, Integral):
        number = int(value)
    elif isinstance(value, str):
        text = value.strip()

        if not re.fullmatch(r"[0-9]+", text):
            raise ValueError("Formato de acciones inválido.")

        number = int(text)
    elif isinstance(value, Real):
        if not math.isfinite(value) or not value.is_integer():
            raise ValueError("Acciones no enteras o no finitas.")

        number = int(value)
    else:
        raise ValueError("Tipo de acciones inválido.")  # noqa: TRY004

    if not 0 <= number <= INT64_MAX:
        raise ValueError("Acciones fuera del rango de int64.")

    return number


def normalize_amount(value: object) -> float:
    """Valida monto como número finito no negativo."""

    if isinstance(value, bool):
        raise ValueError("Monto booleano inválido.")  # noqa: TRY004

    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Monto no numérico.") from exc

    if not math.isfinite(number) or number < 0:
        raise ValueError("Monto no finito o negativo.")

    return number


def normalize_month(value: object) -> int:
    """Normaliza nombres y números enteros de mes."""

    if isinstance(value, bool) or pd.isna(value):
        raise ValueError("Mes inválido.")

    text = str(value).strip().lower()

    if text in MONTH_MAP:
        return MONTH_MAP[text]

    if not re.fullmatch(r"[0-9]+", text):
        raise ValueError("Formato de mes inválido.")

    month = int(text)

    if not 1 <= month <= 12:
        raise ValueError("Mes fuera de rango.")

    return month


def normalize_column(
    series: pd.Series,
    normalizer,
    error_prefix: str,
) -> pd.Series:
    """Aplica una validación y reporta los valores incorrectos."""

    normalized = []

    for value in series:
        try:
            normalized.append(normalizer(value))
        except (ValueError, TypeError, OverflowError) as exc:
            raise ValueError(
                f"{error_prefix}: {value!r}"
            ) from exc

    return pd.Series(normalized, index=series.index)


def load_raw_data(year: int) -> pd.DataFrame:
    """Carga los registros raw de un año."""

    validate_year_argument(year)

    file_path = (
        SNIIV_RAW_DIR
        / str(year)
        / f"mexico_{year}.json"
    )

    if not file_path.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo raw de {year}: {file_path}"
        )

    with file_path.open("r", encoding="utf-8") as file:
        records = json.load(file)

    if not isinstance(records, list):
        raise ValueError(  # noqa: TRY004
            f"El archivo raw de {year} debe contener una lista."
        )

    if not records:
        raise ValueError(
            f"El archivo raw de {year} no contiene registros."
        )

    if not all(isinstance(record, dict) for record in records):
        raise ValueError(
            f"El archivo raw de {year} contiene registros inválidos."
        )

    return pd.DataFrame(records)


def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """Valida y transforma los datos raw del SNIIV."""

    if not isinstance(df, pd.DataFrame):
        raise TypeError(
            "transform_data espera un DataFrame de pandas."
        )

    if df.empty:
        raise ValueError(
            "No se puede transformar un DataFrame vacío."
        )

    missing_columns = [
        column
        for column in EXPECTED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Faltan columnas requeridas para la transformación: "
            f"{missing_columns}"
        )

    df = df[EXPECTED_COLUMNS].copy()

    # Validar años.
    df["año"] = normalize_column(
        df["año"],
        normalize_year,
        "Se encontraron años inválidos",
    ).astype("int64")

    # Normalizar textos y validar dimensiones.
    for column in TEXT_COLUMNS:
        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
        )

        invalid_values = (
            df[column].isna()
            | df[column].eq("")
        )

        if invalid_values.any():
            raise ValueError(
                f"Se encontraron valores vacíos en {column}."
            )

    # Validar medidas.
    df["acciones"] = normalize_column(
        df["acciones"],
        normalize_actions,
        "Se encontraron acciones inválidas",
    ).astype("int64")

    df["monto"] = normalize_column(
        df["monto"],
        normalize_amount,
        "Se encontraron montos inválidos",
    ).astype("float64")

    # Normalizar meses.
    df["mes_numero"] = normalize_column(
        df["mes"],
        normalize_month,
        "Se encontraron meses inválidos",
    ).astype("int64")

    # Crear clave temporal YYYYMM.
    df["fecha_key"] = (
        df["año"] * 100 + df["mes_numero"]
    )

    return df


def save_parquet_safely(
    df: pd.DataFrame,
    output_file,
) -> None:
    """
    Escribe y verifica un Parquet temporal antes
    de reemplazar el archivo final.
    """

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=".parquet.tmp",
            prefix=f".{output_file.stem}_",
            dir=output_file.parent,
            delete=False,
        ) as temporary_file:
            temporary_path = temporary_file.name

        df.to_parquet(
            temporary_path,
            index=False,
        )

        # Comprobar que el archivo escrito puede leerse
        # y conserva la estructura esperada.
        verified = pd.read_parquet(temporary_path)

        if (
            len(verified) != len(df)
            or verified.columns.tolist() != df.columns.tolist()
            or not verified.equals(df.reset_index(drop=True))
        ):
            raise ValueError(
                "La verificación del Parquet temporal falló."
            )

        # Reemplazo atómico de un único archivo
        # dentro del mismo sistema de archivos.
        os.replace(temporary_path, output_file)
        temporary_path = None

    finally:
        if temporary_path is not None:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass


def transform_year(year: int) -> pd.DataFrame:
    """Transforma un año y publica su archivo Parquet."""

    validate_year_argument(year)

    print(f"\n[TRANSFORM] Procesando {year}...")

    df = load_raw_data(year)

    print(
        f"[TRANSFORM] Registros cargados: {len(df):,}"
    )

    df_transformed = transform_data(df)

    if not df_transformed["año"].eq(year).all():
        raise ValueError(
            f"El archivo raw de {year} contiene registros "
            "de otros años."
        )

    print(
        f"[TRANSFORM] Registros transformados: "
        f"{len(df_transformed):,}"
    )

    output_file = (
        SNIIV_PROCESSED_DIR
        / f"sniiv_{year}.parquet"
    )

    save_parquet_safely(
        df_transformed,
        output_file,
    )

    print(
        f"[TRANSFORM] Parquet guardado: {output_file}"
    )

    print(
        f"[TRANSFORM] Columnas finales: "
        f"{list(df_transformed.columns)}"
    )

    return df_transformed


def main() -> None:
    """Transforma los años configurados en el pipeline."""

    for year in SNIIV_YEARS:
        transform_year(year)


if __name__ == "__main__":
    main()
