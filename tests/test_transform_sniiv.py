import pandas as pd
import pytest

from src.transform_sniiv import transform_data

# ==========================================
# DATOS DE PRUEBA
# ==========================================

def create_sample_data() -> pd.DataFrame:
    """Crea datos pequeños para probar la transformación."""

    return pd.DataFrame(
        [
            {
                "año": 2024,
                "mes": "enero",
                "estado": "Quintana Roo",
                "municipio": "Benito Juárez",
                "organismo": "INFONAVIT",
                "destino_credito": "Adquisición",
                "sexo": "Hombre",
                "clave_municipio": "005",
                "clave_estado": "23",
                "acciones": 10,
                "monto": 100000.0,
            },
            {
                "año": 2024,
                "mes": "febrero",
                "estado": "Quintana Roo",
                "municipio": "Benito Juárez",
                "organismo": "INFONAVIT",
                "destino_credito": "Adquisición",
                "sexo": "Mujer",
                "clave_municipio": "005",
                "clave_estado": "23",
                "acciones": 8,
                "monto": 80000.0,
            },
        ]
    )


# ==========================================
# TRANSFORMACIÓN BÁSICA
# ==========================================

def test_transform_creates_month_number():
    """Verifica que los nombres de los meses se conviertan a números."""

    df = create_sample_data()

    result = transform_data(df)

    assert result["mes_numero"].tolist() == [1, 2]


def test_transform_creates_fecha_key():
    """Verifica que fecha_key tenga formato YYYYMM."""

    df = create_sample_data()

    result = transform_data(df)

    assert result["fecha_key"].tolist() == [202401, 202402]


def test_transform_preserves_row_count():
    """Verifica que la transformación no elimine registros."""

    df = create_sample_data()

    result = transform_data(df)

    assert len(result) == len(df)


def test_transform_preserves_expected_columns():
    """Verifica las columnas originales y las columnas nuevas."""

    df = create_sample_data()

    result = transform_data(df)

    expected_columns = [
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

    assert result.columns.tolist() == expected_columns


# ==========================================
# FORMATOS DE MES
# ==========================================

def test_transform_accepts_numeric_months():
    """Verifica que los meses numéricos se conviertan correctamente."""

    df = create_sample_data()

    df["mes"] = ["1", "7"]

    result = transform_data(df)

    assert result["mes_numero"].tolist() == [1, 7]
    assert result["fecha_key"].tolist() == [202401, 202407]


def test_transform_accepts_mixed_month_formats():
    """Verifica que nombres y números puedan coexistir."""

    df = create_sample_data()

    df["mes"] = ["enero", "7"]

    result = transform_data(df)

    assert result["mes_numero"].tolist() == [1, 7]
    assert result["fecha_key"].tolist() == [202401, 202407]


def test_transform_accepts_month_with_surrounding_spaces():
    """Verifica que los espacios exteriores no impidan normalizar."""

    df = create_sample_data()

    df["mes"] = [" enero ", " febrero "]

    result = transform_data(df)

    assert result["mes_numero"].tolist() == [1, 2]
    assert result["fecha_key"].tolist() == [202401, 202402]


def test_transform_accepts_month_names_in_uppercase():
    """Verifica que los nombres en mayúsculas se reconozcan."""

    df = create_sample_data()

    df["mes"] = ["ENERO", "FEBRERO"]

    result = transform_data(df)

    assert result["mes_numero"].tolist() == [1, 2]


# ==========================================
# VALIDACIÓN DE MESES
# ==========================================

@pytest.mark.parametrize(
    "invalid_month",
    [
        "13",
        "0",
        "-1",
        "1.5",
        "enero-falso",
        "",
        None,
        "nan",
    ],
)
def test_transform_rejects_invalid_month(invalid_month):
    """Verifica que los meses inválidos sean rechazados."""

    df = create_sample_data()

    df["mes"] = ["enero", invalid_month]

    with pytest.raises(ValueError):
        transform_data(df)


def test_transform_rejects_fractional_month():
    """Un mes debe ser un número entero entre 1 y 12."""

    df = create_sample_data()

    df["mes"] = ["1.5", "2"]

    with pytest.raises(ValueError, match="meses inválidos"):
        transform_data(df)


# ==========================================
# VALIDACIÓN DE COLUMNAS
# ==========================================

def test_transform_rejects_missing_column():
    """Verifica que se informe cuando falta una columna requerida."""

    df = create_sample_data()

    df = df.drop(columns=["monto"])

    with pytest.raises(ValueError, match="Faltan columnas requeridas"):
        transform_data(df)


def test_transform_rejects_empty_dataframe():
    """Verifica que un DataFrame vacío no se transforme."""

    df = create_sample_data().iloc[0:0]

    with pytest.raises(ValueError, match="DataFrame vacío"):
        transform_data(df)


# ==========================================
# VALIDACIÓN DEL AÑO
# ==========================================

@pytest.mark.parametrize(
    "invalid_year",
    [
        "abc",
        "2024.5",
        2024.5,
        None,
        1800,
        2300,
    ],
)
def test_transform_rejects_invalid_year(invalid_year):
    """Verifica que los años inválidos sean rechazados."""

    df = create_sample_data()

    # Permite probar valores que no son enteros.
    df["año"] = df["año"].astype(object)
    df.at[0, "año"] = invalid_year

    with pytest.raises(ValueError):
        transform_data(df)


# ==========================================
# VALIDACIÓN DE ACCIONES
# ==========================================

@pytest.mark.parametrize(
    "invalid_actions",
    [
        -1,
        1.5,
        "abc",
        None,
        float("inf"),
        float("nan"),
    ],
)
def test_transform_rejects_invalid_actions(invalid_actions):
    """Verifica que acciones sea un entero finito no negativo."""

    df = create_sample_data()
    df["acciones"] = df["acciones"].astype(object)
    df.at[0, "acciones"] = invalid_actions

    with pytest.raises(ValueError):
        transform_data(df)


# ==========================================
# VALIDACIÓN DE MONTO
# ==========================================

@pytest.mark.parametrize(
    "invalid_amount",
    [
        -1,
        "abc",
        None,
        float("inf"),
        float("-inf"),
        float("nan"),
    ],
)
def test_transform_rejects_invalid_amount(invalid_amount):
    """Verifica que monto sea finito y no negativo."""

    df = create_sample_data()
    df["monto"] = df["monto"].astype(object)
    df.at[0, "monto"] = invalid_amount

    with pytest.raises(ValueError):
        transform_data(df)


# ==========================================
# VALIDACIÓN DE DIMENSIONES
# ==========================================

@pytest.mark.parametrize(
    "column",
    [
        "estado",
        "municipio",
        "organismo",
        "destino_credito",
        "sexo",
        "clave_municipio",
        "clave_estado",
    ],
)
def test_transform_rejects_empty_dimensions(column):
    """Verifica que las dimensiones obligatorias no estén vacías."""

    df = create_sample_data()

    df.loc[0, column] = "   "

    with pytest.raises(ValueError, match="valores vacíos"):
        transform_data(df)

# ==========================================
# CASOS LÍMITE ADICIONALES
# ==========================================

@pytest.mark.parametrize("value", [True, False])
def test_transform_rejects_boolean_actions(value):
    df = create_sample_data()
    df["acciones"] = df["acciones"].astype(object)
    df.at[0, "acciones"] = value

    with pytest.raises(ValueError, match="acciones inválidas"):
        transform_data(df)


@pytest.mark.parametrize("value", [True, False])
def test_transform_rejects_boolean_amount(value):
    df = create_sample_data()
    df["monto"] = df["monto"].astype(object)
    df.at[0, "monto"] = value

    with pytest.raises(ValueError, match="montos inválidos"):
        transform_data(df)


def test_transform_rejects_int64_overflow():
    df = create_sample_data()
    df["acciones"] = df["acciones"].astype(object)
    df.at[0, "acciones"] = 2**63

    with pytest.raises(ValueError, match="acciones inválidas"):
        transform_data(df)


def test_transform_rejects_decimal_month_text():
    df = create_sample_data()
    df.loc[0, "mes"] = "1.0"

    with pytest.raises(ValueError, match="meses inválidos"):
        transform_data(df)


def test_transform_rejects_decimal_year_text():
    df = create_sample_data()
    df["año"] = df["año"].astype(object)
    df.at[0, "año"] = "2024.0"

    with pytest.raises(ValueError, match="años inválidos"):
        transform_data(df)


@pytest.mark.parametrize(
    "year",
    [True, 2024.5, "2024", 1800, 2300],
)
def test_transform_year_rejects_invalid_argument(year):
    from src.transform_sniiv import transform_year

    with pytest.raises(ValueError):
        transform_year(year)


def test_parquet_write_failure_preserves_previous_file(
    tmp_path,
    monkeypatch,
):
    from src.transform_sniiv import save_parquet_safely

    output_file = tmp_path / "sniiv_2024.parquet"
    original = b"previous-file-content"
    output_file.write_bytes(original)

    df = transform_data(create_sample_data())

    def fail_write(*args, **kwargs):
        raise OSError("Simulated write failure")

    monkeypatch.setattr(
        pd.DataFrame,
        "to_parquet",
        fail_write,
    )

    with pytest.raises(OSError, match="Simulated write failure"):
        save_parquet_safely(df, output_file)

    assert output_file.read_bytes() == original
    assert sorted(tmp_path.iterdir()) == [output_file]


def test_parquet_promotion_failure_preserves_previous_file(
    tmp_path,
    monkeypatch,
):
    import os

    from src.transform_sniiv import save_parquet_safely

    output_file = tmp_path / "sniiv_2024.parquet"
    original = b"previous-file-content"
    output_file.write_bytes(original)

    df = transform_data(create_sample_data())

    def fail_replace(*args, **kwargs):
        raise OSError("Simulated promotion failure")

    monkeypatch.setattr(os, "replace", fail_replace)

    with pytest.raises(
        OSError,
        match="Simulated promotion failure",
    ):
        save_parquet_safely(df, output_file)

    assert output_file.read_bytes() == original
    assert sorted(tmp_path.iterdir()) == [output_file]
