import json
from pathlib import Path

import pandas as pd

from src.config import SNIIV_PROCESSED_DIR, SNIIV_RAW_DIR


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


def load_raw_data(year: int) -> pd.DataFrame:
    """
    Carga los datos raw de un año y los convierte
    en un DataFrame de pandas.
    """

    file_path = (
        SNIIV_RAW_DIR
        / str(year)
        / f"mexico_{year}.json"
    )

    with file_path.open("r", encoding="utf-8") as file:
        records = json.load(file)

    return pd.DataFrame(records)


def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforma los datos raw del SNIIV para dejarlos
    listos para las siguientes etapas del pipeline.
    """

    df = df.copy()

    # ==========================================
    # SELECCIONAR COLUMNAS
    # ==========================================

    df = df[EXPECTED_COLUMNS]

    # ==========================================
    # CONVERTIR TIPOS DE DATOS
    # ==========================================

    df["año"] = pd.to_numeric(
        df["año"],
        errors="raise",
    ).astype("int64")

    df["acciones"] = pd.to_numeric(
        df["acciones"],
        errors="raise",
    ).astype("int64")

    df["monto"] = pd.to_numeric(
        df["monto"],
        errors="raise",
    )

    # ==========================================
    # NORMALIZAR COLUMNAS DE TEXTO
    # ==========================================

    text_columns = [
        "mes",
        "estado",
        "municipio",
        "organismo",
        "destino_credito",
        "sexo",
        "clave_municipio",
        "clave_estado",
    ]

    for column in text_columns:
        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
        )

    # ==========================================
    # CREAR CLAVE DE FECHA
    # ==========================================

    month_map = {
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

    df["mes_numero"] = (
        df["mes"]
        .str.lower()
        .map(month_map)
    )

    df["fecha_key"] = (
        df["año"] * 100
        + df["mes_numero"]
    )

    return df


def transform_year(year: int) -> pd.DataFrame:
    """
    Ejecuta la transformación completa para un año.
    """

    print(f"\n[TRANSFORM] Procesando {year}...")

    df = load_raw_data(year)

    print(
        f"[TRANSFORM] Registros cargados: {len(df):,}"
    )

    df_transformed = transform_data(df)

    print(
        f"[TRANSFORM] Registros transformados: "
        f"{len(df_transformed):,}"
    )

    SNIIV_PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        SNIIV_PROCESSED_DIR
        / f"sniiv_{year}.parquet"
    )

    df_transformed.to_parquet(
        output_file,
        index=False,
    )

    print(
        f"[TRANSFORM] Parquet guardado: "
        f"{output_file}"
    )

    print(
        f"[TRANSFORM] Columnas finales: "
        f"{list(df_transformed.columns)}"
    )

    return df_transformed



if __name__ == "__main__":
    for year in [2023, 2024, 2025, 2026]:
        transform_year(year)
