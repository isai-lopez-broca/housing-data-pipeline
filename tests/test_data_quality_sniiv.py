from pathlib import Path

import pandas as pd


PROCESSED_DIR = Path("data/processed/sniiv")

YEARS = [2023, 2024, 2025, 2026]


def load_parquet(year: int) -> pd.DataFrame:
    """
    Carga el Parquet procesado de un año.
    """

    file_path = PROCESSED_DIR / f"sniiv_{year}.parquet"

    assert file_path.exists(), (
        f"No existe el archivo esperado: {file_path}"
    )

    return pd.read_parquet(file_path)


def test_processed_files_exist():
    """
    Verifica que exista un Parquet para cada año.
    """

    for year in YEARS:
        file_path = PROCESSED_DIR / f"sniiv_{year}.parquet"

        assert file_path.exists()


def test_no_nulls_in_critical_columns():
    """
    Verifica que las columnas críticas no tengan valores nulos.
    """

    critical_columns = [
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
        "mes_numero",
        "fecha_key",
    ]

    for year in YEARS:
        df = load_parquet(year)

        assert not df[critical_columns].isnull().any().any(), (
            f"Se encontraron valores nulos en {year}."
        )


def test_month_number_is_valid():
    """
    Verifica que mes_numero esté entre 1 y 12.
    """

    for year in YEARS:
        df = load_parquet(year)

        assert df["mes_numero"].between(1, 12).all(), (
            f"mes_numero inválido en {year}."
        )


def test_actions_are_non_negative():
    """
    Verifica que acciones nunca sea negativa.
    """

    for year in YEARS:
        df = load_parquet(year)

        assert (df["acciones"] >= 0).all(), (
            f"Se encontraron acciones negativas en {year}."
        )


def test_amounts_are_non_negative():
    """
    Verifica que monto nunca sea negativo.
    """

    for year in YEARS:
        df = load_parquet(year)

        assert (df["monto"] >= 0).all(), (
            f"Se encontraron montos negativos en {year}."
        )


def test_natural_grain_is_unique():
    """
    Verifica que no existan duplicados según el grano natural.
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

    for year in YEARS:
        df = load_parquet(year)

        duplicates = df.duplicated(
            subset=grain_columns
        ).sum()

        assert duplicates == 0, (
            f"Se encontraron {duplicates} duplicados en {year}."
        )


def test_fecha_key_matches_year_and_month():
    """
    Verifica que fecha_key corresponda a año y mes_numero.
    """

    for year in YEARS:
        df = load_parquet(year)

        expected_fecha_key = (
            df["año"] * 100
            + df["mes_numero"]
        )

        assert (
            df["fecha_key"] == expected_fecha_key
        ).all(), (
            f"fecha_key incorrecta en {year}."
        )
