from src.audit_data_quality import main as run_quality_monitor
from src.config import SNIIV_YEARS
from src.create_warehouse import create_warehouse
from src.extract_sniiv import extract_year
from src.load_warehouse import load_warehouse
from src.transform_sniiv import transform_year
from src.validate_sniiv import validate_year


class PipelineExecutionError(RuntimeError):
    """Indica que una etapa crítica del pipeline falló."""


def execute_stage(stage_name: str, action, year: int | None = None):
    """Ejecuta una etapa e identifica dónde ocurrió un fallo."""

    context = f" para {year}" if year is not None else ""

    print(f"\n{'=' * 60}")
    print(f"[START] {stage_name}{context}")
    print("=" * 60)

    try:
        result = action()
    except Exception as exc:
        message = f"Falló la etapa '{stage_name}'{context}: {exc}"
        print(f"[ERROR] {message}")
        raise PipelineExecutionError(message) from exc

    print(f"[SUCCESS] {stage_name}{context}")
    return result


def validate_year_or_raise(year: int) -> None:
    """Detiene el pipeline cuando un año tiene errores de validación."""

    errors = validate_year(year)

    if errors:
        print(f"[VALIDATION] {len(errors)} errores en {year}:")

        for error in errors[:10]:
            print(f"  - {error}")

        if len(errors) > 10:
            print(f"  ... y {len(errors) - 10} errores adicionales.")

        raise ValueError(
            f"La validación de {year} encontró {len(errors)} errores."
        )

    print(f"[VALIDATION] {year}: sin errores.")


def run_quality_monitor_or_raise() -> None:
    """Detiene el pipeline si la monitorización detecta errores críticos."""

    quality_status = run_quality_monitor()

    if quality_status != 0:
        raise PipelineExecutionError(
            "La monitorización detectó errores críticos."
        )


def run_pipeline(years: list[int] | None = None) -> None:
    """Ejecuta el pipeline completo de financiamiento SNIIV."""

    selected_years = list(SNIIV_YEARS if years is None else years)

    if not selected_years:
        raise ValueError("No hay años configurados para procesar.")

    print("\n" + "#" * 60)
    print("HOUSING DATA PIPELINE")
    print(f"Años seleccionados: {selected_years}")
    print("#" * 60)

    # 1. Extraer, validar y transformar cada año.
    for year in selected_years:
        execute_stage(
            "Extracción",
            lambda year=year: extract_year(year),
            year,
        )

        execute_stage(
            "Validación",
            lambda year=year: validate_year_or_raise(year),
            year,
        )

        execute_stage(
            "Transformación",
            lambda year=year: transform_year(year),
            year,
        )

    # 2. Crear el esquema y cargar el Data Warehouse.
    execute_stage(
        "Creación del Data Warehouse",
        create_warehouse,
    )

    execute_stage(
        "Carga del Data Warehouse",
        load_warehouse,
    )

    # 3. Revisar la calidad del almacén cargado.
    execute_stage(
        "Monitorización de calidad",
        run_quality_monitor_or_raise,
    )

    
    print("\n" + "#" * 60)
    print("PIPELINE FINALIZADO CORRECTAMENTE")
    print("#" * 60)


def main() -> int:
    try:
        run_pipeline()
    except Exception as exc:
        print(f"\n[PIPELINE FAILED] {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())