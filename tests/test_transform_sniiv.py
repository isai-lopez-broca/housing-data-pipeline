import pandas as pd

from src.transform_sniiv import transform_data


def create_sample_data() -> pd.DataFrame:
    """
    Crea datos pequeños para probar la transformación.
    """

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


def test_transform_creates_month_number():
    """
    Verifica que el nombre del mes se convierta
    correctamente a número.
    """

    df = create_sample_data()

    result = transform_data(df)

    assert result["mes_numero"].tolist() == [1, 2]


def test_transform_creates_fecha_key():
    """
    Verifica que fecha_key tenga formato YYYYMM.
    """

    df = create_sample_data()

    result = transform_data(df)

    assert result["fecha_key"].tolist() == [202401, 202402]


def test_transform_preserves_row_count():
    """
    Verifica que la transformación no elimine registros.
    """

    df = create_sample_data()

    result = transform_data(df)

    assert len(result) == len(df)


def test_transform_preserves_expected_columns():
    """
    Verifica que las columnas originales y las nuevas
    estén presentes.
    """

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

