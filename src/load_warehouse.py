
from decimal import Decimal

import pandas as pd
from psycopg2.extras import execute_values

from src.config import SNIIV_PROCESSED_DIR, SNIIV_YEARS
from src.database import create_connection


def load_parquet_files() -> pd.DataFrame:
    """
    Lee los archivos Parquet de los años configurados
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
    """Carga la dimensión fecha."""

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
        execute_values(cursor, sql, rows)

    print(
        f"[LOAD] dim_fecha: "
        f"{len(rows):,} registros"
    )


def load_dim_territorio(
    connection,
    df: pd.DataFrame,
) -> None:
    """Carga la dimensión territorio."""

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
        execute_values(cursor, sql, rows)

    print(
        f"[LOAD] dim_territorio: "
        f"{len(rows):,} registros"
    )


def load_dim_organismo(
    connection,
    df: pd.DataFrame,
) -> None:
    """Carga la dimensión organismo."""

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
        execute_values(cursor, sql, rows)

    print(
        f"[LOAD] dim_organismo: "
        f"{len(rows):,} valores únicos"
    )


def load_dim_destino(
    connection,
    df: pd.DataFrame,
) -> None:
    """Carga la dimensión destino."""

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
        execute_values(cursor, sql, rows)

    print(
        f"[LOAD] dim_destino: "
        f"{len(rows):,} valores únicos"
    )


def load_dim_sexo(
    connection,
    df: pd.DataFrame,
) -> None:
    """Carga la dimensión sexo."""

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
        execute_values(cursor, sql, rows)

    print(
        f"[LOAD] dim_sexo: "
        f"{len(rows):,} valores únicos"
    )


def get_dimension_keys(
    connection,
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Obtiene las claves dimensionales.

    Valida que los JOIN no multipliquen registros
    y que ninguna clave quede sin correspondencia.
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

    original_rows = len(df)

    result = df.merge(
        fecha_df,
        on="fecha_key",
        how="left",
        validate="many_to_one",
    )

    result = result.merge(
        territorio_df,
        on=[
            "clave_estado",
            "clave_municipio",
        ],
        how="left",
        validate="many_to_one",
    )

    result = result.merge(
        organismo_df,
        on="organismo",
        how="left",
        validate="many_to_one",
    )

    result = result.merge(
        destino_df,
        on="destino_credito",
        how="left",
        validate="many_to_one",
    )

    result = result.merge(
        sexo_df,
        on="sexo",
        how="left",
        validate="many_to_one",
    )

    if len(result) != original_rows:
        raise ValueError(
            "La cantidad de registros cambió durante "
            "los cruces dimensionales: "
            f"entrada={original_rows}, "
            f"salida={len(result)}"
        )

    key_columns = [
        "fecha_dimension_key",
        "territorio_key",
        "organismo_key",
        "destino_key",
        "sexo_key",
    ]

    missing_keys = result[key_columns].isna().sum()
    missing_keys = missing_keys[missing_keys > 0]

    if not missing_keys.empty:
        details = ", ".join(
            f"{column}={int(count)}"
            for column, count in missing_keys.items()
        )

        raise ValueError(
            "Se encontraron claves dimensionales "
            f"sin correspondencia: {details}"
        )

    print(
        "[LOAD] Integridad dimensional verificada: "
        f"{len(result):,} registros"
    )

    return result


def load_fact_financiamiento(
    connection,
    df: pd.DataFrame,
) -> None:
    """
    Inserta hechos nuevos y actualiza los existentes.

    No elimina registros.
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
        f"{len(rows):,} registros procesados"
    )


def validate_snapshot(
    df: pd.DataFrame,
    authorized_periods: list[int],
) -> tuple[list[int], list[tuple]]:
    """
    Valida las claves del snapshot y los periodos
    autorizados antes de permitir eliminaciones.

    Esta validación no demuestra por sí sola
    la completitud de una extracción SNIIV.
    """

    if not authorized_periods:
        raise ValueError(
            "Debes autorizar explícitamente "
            "al menos un periodo."
        )

    periods = [int(period) for period in authorized_periods]

    if len(periods) != len(set(periods)):
        raise ValueError(
            "Hay periodos autorizados duplicados."
        )

    for period in periods:
        year = period // 100
        month = period % 100

        if year < 2000 or not 1 <= month <= 12:
            raise ValueError(
                f"Periodo inválido: {period}. "
                "Utiliza el formato AAAAMM."
            )

    if df.empty:
        raise ValueError(
            "No se permite sincronizar "
            "un snapshot vacío."
        )

    key_columns = [
        "fecha_dimension_key",
        "territorio_key",
        "organismo_key",
        "destino_key",
        "sexo_key",
    ]

    if df[key_columns].isna().any().any():
        raise ValueError(
            "El snapshot contiene claves nulas."
        )

    snapshot = df[key_columns].copy()
    snapshot = snapshot.astype("int64")

    if snapshot.duplicated().any():
        raise ValueError(
            "El snapshot contiene claves "
            "de hechos duplicadas."
        )

    available_periods = set(
        snapshot["fecha_dimension_key"].unique()
    )

    missing_periods = set(periods) - available_periods

    if missing_periods:
        raise ValueError(
            "El snapshot no contiene los periodos "
            f"autorizados: {sorted(missing_periods)}"
        )

    snapshot = snapshot[
        snapshot["fecha_dimension_key"].isin(periods)
    ]

    rows = list(
        snapshot.itertuples(
            index=False,
            name=None,
        )
    )

    return periods, rows


def synchronize_snapshot(
    connection,
    df: pd.DataFrame,
    authorized_periods: list[int],
) -> int:
    """
    Elimina hechos ausentes del snapshot exclusivamente
    en los periodos autorizados.

    Restricción temporal de seguridad:
    solo funciona en housing_test_db.

    Debe ejecutarse dentro de la misma transacción
    que la carga de dimensiones y hechos.
    """

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT current_database();"
        )

        database_name = cursor.fetchone()[0]

    if database_name != "housing_test_db":
        raise RuntimeError(
            "Las eliminaciones están bloqueadas "
            "fuera de housing_test_db."
        )

    periods, rows = validate_snapshot(
        df,
        authorized_periods,
    )

    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE TEMP TABLE snapshot_keys (
                fecha_key INTEGER NOT NULL,
                territorio_key INTEGER NOT NULL,
                organismo_key INTEGER NOT NULL,
                destino_key INTEGER NOT NULL,
                sexo_key SMALLINT NOT NULL,
                PRIMARY KEY (
                    fecha_key,
                    territorio_key,
                    organismo_key,
                    destino_key,
                    sexo_key
                )
            ) ON COMMIT DROP;
        """)

        execute_values(
            cursor,
            """
            INSERT INTO snapshot_keys (
                fecha_key,
                territorio_key,
                organismo_key,
                destino_key,
                sexo_key
            )
            VALUES %s;
            """,
            rows,
            page_size=5000,
        )

        cursor.execute(
            """
            DELETE FROM fact_financiamiento AS fact
            WHERE fact.fecha_key = ANY(%s)
              AND NOT EXISTS (
                  SELECT 1
                  FROM snapshot_keys AS snapshot
                  WHERE
                      snapshot.fecha_key = fact.fecha_key
                      AND snapshot.territorio_key =
                          fact.territorio_key
                      AND snapshot.organismo_key =
                          fact.organismo_key
                      AND snapshot.destino_key =
                          fact.destino_key
                      AND snapshot.sexo_key =
                          fact.sexo_key
              );
            """,
            (periods,),
        )

        deleted_rows = cursor.rowcount

    print(
        f"[LOAD] Snapshot sincronizado: "
        f"{deleted_rows:,} registros obsoletos "
        "eliminados."
    )

    return deleted_rows


def load_warehouse(
    authorized_periods: list[int] | None = None,
) -> None:
    """
    Ejecuta la carga completa del Data Warehouse
    dentro de una única transacción.

    Por defecto:
        INSERT + UPDATE, sin eliminaciones.

    Con authorized_periods:
        INSERT + UPDATE + DELETE controlado,
        exclusivamente en housing_test_db.
    """

    df = load_parquet_files()

    connection = create_connection()

    try:
        print(
            "\n[LOAD] Iniciando transacción de carga..."
        )

        # Protección antes de cualquier escritura.
        if authorized_periods is not None:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT current_database();"
                )

                database_name = cursor.fetchone()[0]

            if database_name != "housing_test_db":
                raise RuntimeError(
                    "La sincronización con eliminaciones "
                    "solo se permite en housing_test_db."
                )

            if not authorized_periods:
                raise ValueError(
                    "Debes indicar periodos autorizados."
                )

        print(
            "\n[LOAD] Cargando dimensiones..."
        )

        load_dim_fecha(connection, df)
        load_dim_territorio(connection, df)
        load_dim_organismo(connection, df)
        load_dim_destino(connection, df)
        load_dim_sexo(connection, df)

        print(
            "\n[LOAD] Obteniendo claves de dimensiones..."
        )

        df_with_keys = get_dimension_keys(
            connection,
            df,
        )

        # Validar antes de cargar hechos cuando
        # se solicita sincronización con eliminaciones.
        if authorized_periods is not None:
            validate_snapshot(
                df_with_keys,
                authorized_periods,
            )

        print(
            "\n[LOAD] Cargando tabla de hechos..."
        )

        load_fact_financiamiento(
            connection,
            df_with_keys,
        )

        if authorized_periods is not None:
            print(
                "\n[LOAD] Sincronizando snapshot..."
            )

            synchronize_snapshot(
                connection,
                df_with_keys,
                authorized_periods,
            )

        # Confirmar todas las operaciones juntas.
        connection.commit()

        print(
            "\n[LOAD] Data Warehouse "
            "cargado correctamente."
        )

    except Exception:
        connection.rollback()

        print(
            "\n[LOAD] Error durante la carga. "
            "Se revirtieron los cambios "
            "de la transacción."
        )

        raise

    finally:
        connection.close()

        print(
            "[LOAD] Conexión cerrada."
        )


if __name__ == "__main__":
    load_warehouse()
