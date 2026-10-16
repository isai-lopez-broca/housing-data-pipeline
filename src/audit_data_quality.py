from src.database import create_connection


def evaluate_check(name: str, count: int, level: str = "error") -> dict:
    """
    Clasifica un resultado de calidad de datos.

    error: una incidencia representa un fallo de calidad.
    warning: una incidencia requiere investigación, pero no
    demuestra por sí sola que los datos sean incorrectos.
    """
    if count == 0:
        status = "OK"
    elif level == "warning":
        status = "ADVERTENCIA"
    else:
        status = "ERROR"

    return {
        "name": name,
        "count": count,
        "level": level,
        "status": status,
    }


def find_missing_months(months: list[int]) -> list[int]:
    """
    Identifica los meses ausentes entre el primer y el último
    mes observado, sin asumir que el año debe estar completo.
    """

    if not months:
        return []

    observed_months = set(months)

    first_month = min(observed_months)
    last_month = max(observed_months)

    return [
        month
        for month in range(first_month, last_month + 1)
        if month not in observed_months
    ]


def collect_quality_metrics(connection) -> tuple[list[dict], list[tuple]]:
    """Consulta las métricas de calidad y la cobertura temporal."""

    checks = []

    with connection.cursor() as cursor:
        # 1. Integridad básica de las medidas.
        cursor.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE acciones < 0),
                COUNT(*) FILTER (WHERE monto < 0),
                COUNT(*) FILTER (WHERE acciones IS NULL),
                COUNT(*) FILTER (WHERE monto IS NULL)
            FROM fact_financiamiento;
            """
        )

        negative_actions, negative_amounts, null_actions, null_amounts = (
            cursor.fetchone()
        )

        checks.extend(
            [
                evaluate_check("Acciones negativas", negative_actions),
                evaluate_check("Montos negativos", negative_amounts),
                evaluate_check("Acciones nulas", null_actions),
                evaluate_check("Montos nulos", null_amounts),
            ]
        )

        # 2. Duplicados en la granularidad de la tabla de hechos.
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT
                    fecha_key,
                    territorio_key,
                    organismo_key,
                    destino_key,
                    sexo_key
                FROM fact_financiamiento
                GROUP BY
                    fecha_key,
                    territorio_key,
                    organismo_key,
                    destino_key,
                    sexo_key
                HAVING COUNT(*) > 1
            ) AS duplicated_grain;
            """
        )
        duplicate_grains = cursor.fetchone()[0]

        checks.append(
            evaluate_check(
                "Combinaciones duplicadas en la tabla de hechos",
                duplicate_grains,
            )
        )

        # 3. Integridad referencial: cada clave debe existir en su dimensión.
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM fact_financiamiento f
            LEFT JOIN dim_fecha d
                ON d.fecha_key = f.fecha_key
            LEFT JOIN dim_territorio t
                ON t.territorio_key = f.territorio_key
            LEFT JOIN dim_organismo o
                ON o.organismo_key = f.organismo_key
            LEFT JOIN dim_destino de
                ON de.destino_key = f.destino_key
            LEFT JOIN dim_sexo s
                ON s.sexo_key = f.sexo_key
            WHERE
                d.fecha_key IS NULL
                OR t.territorio_key IS NULL
                OR o.organismo_key IS NULL
                OR de.destino_key IS NULL
                OR s.sexo_key IS NULL;
            """
        )
        orphan_rows = cursor.fetchone()[0]

        checks.append(
            evaluate_check(
                "Registros con claves sin dimensión correspondiente",
                orphan_rows,
            )
        )

        # 4. Combinaciones que necesitan investigación, no eliminación automática.
        cursor.execute(
            """
            SELECT
                COUNT(*) FILTER (
                    WHERE acciones = 0 AND monto > 0
                ),
                COUNT(*) FILTER (
                    WHERE acciones > 0 AND monto = 0
                )
            FROM fact_financiamiento;
            """
        )
        zero_actions_with_amount, actions_without_amount = cursor.fetchone()

        checks.extend(
            [
                evaluate_check(
                    "Registros con cero acciones y monto positivo",
                    zero_actions_with_amount,
                    level="warning",
                ),
                evaluate_check(
                    "Registros con acciones positivas y monto cero",
                    actions_without_amount,
                    level="warning",
                ),
            ]
        )

        # 5. Cobertura temporal: identificar meses faltantes
        # entre el primer y el último mes observado.
        cursor.execute(
            """
            SELECT
                anio,
                ARRAY_AGG(
                    DISTINCT mes_numero
                    ORDER BY mes_numero
                ) AS meses_observados,
                COUNT(DISTINCT mes_numero) AS meses_con_datos,
                MIN(mes_numero) AS primer_mes,
                MAX(mes_numero) AS ultimo_mes,
                COUNT(*) AS registros
            FROM fact_financiamiento f
            JOIN dim_fecha d
                ON d.fecha_key = f.fecha_key
            GROUP BY anio
            ORDER BY anio;
            """
        )
        coverage = cursor.fetchall()

    return checks, coverage


def print_report(checks: list[dict], coverage: list[tuple]) -> None:
    """Muestra el resultado de la auditoría en la terminal."""

    print("\n" + "=" * 64)
    print("MONITOR DE CALIDAD DE DATOS — HOUSING DATA PIPELINE")
    print("=" * 64)

    for check in checks:
        print(
            f"[{check['status']}] {check['name']}: "
            f"{check['count']:,}"
        )

    print("\n--- Cobertura temporal ---")

    if not coverage:
        print("No se encontraron registros en la tabla de hechos.")
    else:
        for (
            year,
            observed_months,
            months,
            first_month,
            last_month,
            records,
        ) in coverage:
            missing_months = find_missing_months(observed_months or [])

            print(
                f"{year}: {months} meses con datos "
                f"(mes {first_month} a {last_month}); "
                f"{records:,} registros"
            )

            if missing_months:
                missing_labels = ", ".join(
                    f"{month:02d}" for month in missing_months
                )
                print(
                    f"  [ADVERTENCIA] Meses faltantes dentro "
                    f"del periodo observado: {missing_labels}"
                )
            else:
                print(
                    "  [OK] Sin huecos dentro del periodo observado."
                )

    errors = sum(check["status"] == "ERROR" for check in checks)
    warnings = sum(
        check["status"] == "ADVERTENCIA" for check in checks
    )

    print("\n--- Resumen ---")
    print(f"Errores: {errors}")
    print(f"Advertencias: {warnings}")

    if errors:
        print("Resultado final: ERROR — revisar antes de continuar.")
    elif warnings:
        print("Resultado final: ADVERTENCIAS — investigar los hallazgos.")
    else:
        print("Resultado final: OK — no se detectaron incidencias.")


def main() -> int:
    connection = create_connection()

    try:
        checks, coverage = collect_quality_metrics(connection)
        print_report(checks, coverage)
        has_errors = any(check["status"] == "ERROR" for check in checks)
        return 1 if has_errors else 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
