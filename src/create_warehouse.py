from pathlib import Path

from src.config import SQL_DIR
from src.database import create_connection


def execute_sql_file(
    connection,
    sql_file: Path,
) -> None:
    """
    Ejecuta un archivo SQL completo dentro de PostgreSQL.
    """

    sql = sql_file.read_text(
        encoding="utf-8",
    )

    with connection.cursor() as cursor:
        cursor.execute(sql)


def create_warehouse() -> None:
    """
    Crea las dimensiones y la tabla de hechos
    del Data Warehouse.
    """

    connection = create_connection()

    try:
        dimensions_file = SQL_DIR / "01_create_dimensions.sql"
        fact_file = SQL_DIR / "02_create_fact.sql"

        print("[WAREHOUSE] Creando dimensiones...")
        execute_sql_file(
            connection,
            dimensions_file,
        )

        print("[WAREHOUSE] Creando tabla de hechos...")
        execute_sql_file(
            connection,
            fact_file,
        )

        connection.commit()

        print("[WAREHOUSE] Data Warehouse creado correctamente.")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    create_warehouse()
