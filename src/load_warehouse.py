from pathlib import Path
from decimal import Decimal
import pandas as pd
from psycopg2.extras import execute_values

from src.config import SNIIV_PROCESSED_DIR, SNIIV_YEARS
from src.database import create_connection


def load_parquet_files() -> pd.DataFrame:
    """
    Lee los archivos Parquet de todos los años configurados
    y los combina en un único DataFrame.
    """

    dataframes = []

    for year in SNIIV_YEARS:
        file_path = (
            SNIIV_PROCESSED_DIR
            / f"sniiv_{year}.parquet"
        )

        print(
            f"[LOAD] Leyendo Parquet {year}: "
            f"{file_path}"
        )

        df = pd.read_parquet(file_path)

        print(
            f"[LOAD] {year}: "
            f"{len(df):,} registros"
        )

        dataframes.append(df)

    combined_df = pd.concat(
        dataframes,
        ignore_index=True,
    )

    print(
        f"[LOAD] Total de registros: "
        f"{len(combined_df):,}"
    )

    return combined_df


def load_dim_fecha(
    connection,
    df: pd.DataFrame,
) -> None:
    """
    Carga la dimensión fecha.
    """

    dimension = (
        df[
            [
                "fecha_key",
                "año",
                "mes_numero",
                "mes",
            ]
        ]
        .drop_duplicates()
        .rename(
            columns={
                "año": "anio",
                "mes": "mes_nombre",
            }
        )
    )

    rows = [
        (
            int(row.fecha_key),
            int(row.anio),
            int(row.mes_numero),
            row.mes_nombre,
        )
        for row in dimension.itertuples(index=False)
    ]

    sql = """
        INSERT INTO dim_fecha (
            fecha_key,
            anio,
            mes_numero,
            mes_nombre
        )
        VALUES %s
        ON CONFLICT (fecha_key)
        DO UPDATE SET
            anio = EXCLUDED.anio,
            mes_numero = EXCLUDED.mes_numero,
            mes_nombre = EXCLUDED.mes_nombre;
    """

    with connection.cursor() as cursor:
        execute_values(
            cursor,
            sql,
            rows,
        )

    print(
        f"[LOAD] dim_fecha: "
        f"{len(rows):,} registros"
    )


def load_dim_territorio(
    connection,
    df: pd.DataFrame,
) -> None:
    """
    Carga la dimensión territorio.
    """

    dimension = (
        df[
            [
                "clave_estado",
                "estado",
                "clave_municipio",
                "municipio",
            ]
        ]
        .drop_duplicates()
    )

    rows = [
        (
            row.clave_estado,
            row.estado,
            row.clave_municipio,
            row.municipio,
        )
        for row in dimension.itertuples(index=False)
    ]

    sql = """
        INSERT INTO dim_territorio (
            clave_estado,
            estado,
            clave_municipio,
            municipio
        )
        VALUES %s
        ON CONFLICT (
            clave_estado,
            clave_municipio
        )
        DO UPDATE SET
            estado = EXCLUDED.estado,
            municipio = EXCLUDED.municipio;
    """

    with connection.cursor() as cursor:
        execute_values(
            cursor,
            sql,
            rows,
        )

    print(
        f"[LOAD] dim_territorio: "
        f"{len(rows):,} registros"
    )


def load_dim_organismo(
    connection,
    df: pd.DataFrame,
) -> None:
    """
    Carga la dimensión organismo.
    """

    values = (
        df["organismo"]
        .drop_duplicates()
        .tolist()
    )

    rows = [
        (value,)
        for value in values
    ]

    sql = """
        INSERT INTO dim_organismo (
            organismo
        )
        VALUES %s
        ON CONFLICT (organismo)
        DO NOTHING;
    """

    with connection.cursor() as cursor:
        execute_values(
            cursor,
            sql,
            rows,
        )

    print(
        f"[LOAD] dim_organismo: "
        f"{len(rows):,} valores únicos"
    )


def load_dim_destino(
    connection,
    df: pd.DataFrame,
) -> None:
    """
    Carga la dimensión destino.
    """

    values = (
        df["destino_credito"]
        .drop_duplicates()
        .tolist()
    )

    rows = [
        (value,)
        for value in values
    ]

    sql = """
        INSERT INTO dim_destino (
            destino_credito
        )
        VALUES %s
        ON CONFLICT (destino_credito)
        DO NOTHING;
    """

    with connection.cursor() as cursor:
        execute_values(
            cursor,
            sql,
            rows,
        )

    print(
        f"[LOAD] dim_destino: "
        f"{len(rows):,} valores únicos"
    )


def load_dim_sexo(
    connection,
    df: pd.DataFrame,
) -> None:
    """
    Carga la dimensión sexo.
    """

    values = (
        df["sexo"]
        .drop_duplicates()
        .tolist()
    )

    rows = [
        (value,)
        for value in values
    ]

    sql = """
        INSERT INTO dim_sexo (
            sexo
        )
        VALUES %s
        ON CONFLICT (sexo)
        DO NOTHING;
    """

    with connection.cursor() as cursor:
        execute_values(
            cursor,
            sql,
            rows,
        )

    print(
        f"[LOAD] dim_sexo: "
        f"{len(rows):,} valores únicos"
    )


def get_dimension_keys(
    connection,
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Obtiene las claves sustitutas de las dimensiones
    y las incorpora al DataFrame.
    """

    queries = {
        "dim_fecha": """
            SELECT
                fecha_key,
                fecha_key AS fecha_dimension_key
            FROM dim_fecha;
        """,
        "dim_territorio": """
            SELECT
                territorio_key,
                clave_estado,
                clave_municipio
            FROM dim_territorio;
        """,
        "dim_organismo": """
            SELECT
                organismo_key,
                organismo
            FROM dim_organismo;
        """,
        "dim_destino": """
            SELECT
                destino_key,
                destino_credito
            FROM dim_destino;
        """,
        "dim_sexo": """
            SELECT
                sexo_key,
                sexo
            FROM dim_sexo;
        """,
    }

    with connection.cursor() as cursor:
        cursor.execute(queries["dim_fecha"])
        fecha_rows = cursor.fetchall()

        cursor.execute(queries["dim_territorio"])
        territorio_rows = cursor.fetchall()

        cursor.execute(queries["dim_organismo"])
        organismo_rows = cursor.fetchall()

        cursor.execute(queries["dim_destino"])
        destino_rows = cursor.fetchall()

        cursor.execute(queries["dim_sexo"])
        sexo_rows = cursor.fetchall()

    fecha_df = pd.DataFrame(
        fecha_rows,
        columns=[
            "fecha_key",
            "fecha_dimension_key",
        ],
    )

    territorio_df = pd.DataFrame(
        territorio_rows,
        columns=[
            "territorio_key",
            "clave_estado",
            "clave_municipio",
        ],
    )

    organismo_df = pd.DataFrame(
        organismo_rows,
        columns=[
            "organismo_key",
            "organismo",
        ],
    )

    destino_df = pd.DataFrame(
        destino_rows,
        columns=[
            "destino_key",
            "destino_credito",
        ],
    )

    sexo_df = pd.DataFrame(
        sexo_rows,
        columns=[
            "sexo_key",
            "sexo",
        ],
    )

    result = df.merge(
        fecha_df,
        left_on="fecha_key",
        right_on="fecha_key",
        how="left",
    )

    result = result.merge(
        territorio_df,
        on=[
            "clave_estado",
            "clave_municipio",
        ],
        how="left",
    )

    result = result.merge(
        organismo_df,
        on="organismo",
        how="left",
    )

    result = result.merge(
        destino_df,
        on="destino_credito",
        how="left",
    )

    result = result.merge(
        sexo_df,
        on="sexo",
        how="left",
    )

    return result


def load_fact_financiamiento(
    connection,
    df: pd.DataFrame,
) -> None:
    """
    Carga la tabla de hechos utilizando
    las claves sustitutas de las dimensiones.
    """

    fact = df[
        [
            "fecha_dimension_key",
            "territorio_key",
            "organismo_key",
            "destino_key",
            "sexo_key",
            "acciones",
            "monto",
        ]
    ].copy()

    rows = [
        (
            int(row.fecha_dimension_key),
            int(row.territorio_key),
            int(row.organismo_key),
            int(row.destino_key),
            int(row.sexo_key),
            int(row.acciones),
            Decimal(str(row.monto)),
        )
        for row in fact.itertuples(index=False)
    ]

    sql = """
        INSERT INTO fact_financiamiento (
            fecha_key,
            territorio_key,
            organismo_key,
            destino_key,
            sexo_key,
            acciones,
            monto
        )
        VALUES %s
        ON CONFLICT (
            fecha_key,
            territorio_key,
            organismo_key,
            destino_key,
            sexo_key
        )
        DO UPDATE SET
            acciones = EXCLUDED.acciones,
            monto = EXCLUDED.monto;
    """

    with connection.cursor() as cursor:
        execute_values(
            cursor,
            sql,
            rows,
            page_size=5000,
        )

    print(
        f"[LOAD] fact_financiamiento: "
        f"{len(rows):,} registros"
    )


def load_warehouse() -> None:
    """
    Ejecuta la carga completa del Data Warehouse.
    """

    df = load_parquet_files()

    connection = create_connection()

    try:
        print("\n[LOAD] Cargando dimensiones...")

        load_dim_fecha(
            connection,
            df,
        )

        load_dim_territorio(
            connection,
            df,
        )

        load_dim_organismo(
            connection,
            df,
        )

        load_dim_destino(
            connection,
            df,
        )

        load_dim_sexo(
            connection,
            df,
        )

        connection.commit()

        print("\n[LOAD] Obteniendo claves de dimensiones...")

        df_with_keys = get_dimension_keys(
            connection,
            df,
        )

        print("[LOAD] Cargando tabla de hechos...")

        load_fact_financiamiento(
            connection,
            df_with_keys,
        )

        connection.commit()

        print(
            "\n[LOAD] Data Warehouse cargado correctamente."
        )

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    load_warehouse()
