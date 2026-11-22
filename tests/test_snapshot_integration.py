import os

import pandas as pd
import psycopg2
import pytest

from src.load_warehouse import (
    get_dimension_keys,
    load_dim_destino,
    load_dim_fecha,
    load_dim_organismo,
    load_dim_sexo,
    load_dim_territorio,
    load_fact_financiamiento,
    synchronize_snapshot,
)


@pytest.fixture
def connection():
    if os.getenv("DB_NAME") != "housing_test_db":
        pytest.skip(
            "La integración requiere DB_NAME=housing_test_db"
        )

    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT current_database()")
            assert cursor.fetchone()[0] == "housing_test_db"

        yield conn

    finally:
        conn.rollback()
        conn.close()


def make_data(records):
    rows = []

    for municipio, acciones, monto in records:
        rows.append({
            "fecha_key": 202501,
            "año": 2025,
            "mes_numero": 1,
            "mes": "Enero",
            "clave_estado": "01",
            "estado": "Aguascalientes",
            "clave_municipio": municipio,
            "municipio": f"Municipio {municipio}",
            "organismo": "ORGANISMO_PRUEBA",
            "destino_credito": "Compra",
            "sexo": "Hombre",
            "acciones": acciones,
            "monto": monto,
        })

    return pd.DataFrame(rows)


def load_test_data(connection, df):
    load_dim_fecha(connection, df)
    load_dim_territorio(connection, df)
    load_dim_organismo(connection, df)
    load_dim_destino(connection, df)
    load_dim_sexo(connection, df)

    result = get_dimension_keys(connection, df)
    load_fact_financiamiento(connection, result)

    return result


def get_facts(connection):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                t.clave_municipio,
                f.acciones,
                f.monto
            FROM fact_financiamiento f
            JOIN dim_territorio t
                ON t.territorio_key = f.territorio_key
            WHERE f.fecha_key = 202501
              AND t.clave_estado = '01'
              AND t.clave_municipio IN (
                  '991', '992', '993', '994'
              )
            ORDER BY t.clave_municipio;
        """)

        return cursor.fetchall()


def test_snapshot_insert_update_delete_and_rollback(connection):
    # Datos iniciales: A, B y C.
    initial = make_data([
        ("991", 100, 1000),
        ("992", 200, 2000),
        ("993", 300, 3000),
    ])

    load_test_data(connection, initial)

    assert [
        (row[0], row[1])
        for row in get_facts(connection)
    ] == [
        ("991", 100),
        ("992", 200),
        ("993", 300),
    ]

    # Nuevo snapshot:
    # A cambia, B desaparece, C permanece y D aparece.
    updated = make_data([
        ("991", 150, 1500),
        ("993", 300, 3000),
        ("994", 400, 4000),
    ])

    resolved = load_test_data(connection, updated)

    deleted = synchronize_snapshot(
        connection,
        resolved,
        authorized_periods=[202501],
    )

    assert deleted == 1

    assert [
        (row[0], row[1])
        for row in get_facts(connection)
    ] == [
        ("991", 150),
        ("993", 300),
        ("994", 400),
    ]

    # Revertimos toda la transacción.
    connection.rollback()

    assert get_facts(connection) == []


def test_snapshot_rejects_unauthorized_period(connection):
    df = make_data([
        ("991", 100, 1000),
    ])

    resolved = load_test_data(connection, df)

    with pytest.raises(
        ValueError,
        match="no contiene los periodos",
    ):
        synchronize_snapshot(
            connection,
            resolved,
            authorized_periods=[202502],
        )
