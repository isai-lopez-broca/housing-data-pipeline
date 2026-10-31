from pathlib import Path

import pandas as pd
import pytest

PROCESSED_DIR = Path("data/processed/sniiv")

YEARS = [2023, 2024, 2025, 2026]


@pytest.fixture
def processed_parquet_files(tmp_path, monkeypatch):
    """
    Crea archivos Parquet temporales para probar
    las reglas de calidad sin depender de datos locales.
    """

    processed_dir = tmp_path / "processed" / "sniiv"
    processed_dir.mkdir(parents=True)

    monkeypatch.setitem(
        globals(),
        "PROCESSED_DIR",
        processed_dir,
    )

    for year in YEARS:
        df = pd.DataFrame({
            "año": [year],
            "mes": ["enero"],
            "estado": ["Quintana Roo"],
            "municipio": ["Benito Juárez"],
            "organismo": ["CONAVI"],
            "destino_credito": ["Mejoramiento"],
            "sexo": ["No especificado"],
            "clave_municipio": ["005"],
            "clave_estado": ["23"],
            "acciones": [10],
            "monto": [1000.0],
            "mes_numero": [1],
            "fecha_key": [year * 100 + 1],
        })

        file_path = processed_dir / f"sniiv_{year}.parquet"

        df.to_parquet(file_path, index=False)


def load_parquet(year: int) -> pd.DataFrame:
    """
    Carga el Parquet procesado de un año.
    """

    file_path = PROCESSED_DIR / f"sniiv_{year}.parquet"

    assert file_path.exists(), (
        f"No existe el archivo esperado: {file_path}"
    )

    return pd.read_parquet(file_path)


def test_processed_files_exist(processed_parquet_files):
    """
    Verifica que exista un Parquet para cada año.
    """

    for year in YEARS:
        file_path = PROCESSED_DIR / f"sniiv_{year}.parquet"

        assert file_path.exists()


def test_no_nulls_in_critical_columns(processed_parquet_files):
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


def test_month_number_is_valid(processed_parquet_files):
    """
    Verifica que mes_numero esté entre 1 y 12.
    """

    for year in YEARS:
        df = load_parquet(year)

        assert df["mes_numero"].between(1, 12).all(), (
            f"mes_numero inválido en {year}."
        )


def test_actions_are_non_negative(processed_parquet_files):
    """
    Verifica que acciones nunca sea negativa.
    """

    for year in YEARS:
        df = load_parquet(year)

        assert (df["acciones"] >= 0).all(), (
            f"Se encontraron acciones negativas en {year}."
        )


def test_amounts_are_non_negative(processed_parquet_files):
    """
    Verifica que monto nunca sea negativo.
    """

    for year in YEARS:
        df = load_parquet(year)

        assert (df["monto"] >= 0).all(), (
            f"Se encontraron montos negativos en {year}."
        )


def test_natural_grain_is_unique(processed_parquet_files):
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


def test_fecha_key_matches_year_and_month(processed_parquet_files):
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
