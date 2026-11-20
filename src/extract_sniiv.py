import json
import math
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

from src.config import SNIIV_RAW_DIR, SNIIV_YEARS

# ==========================================
# CONFIGURACIÓN DE LA EXTRACCIÓN
# ==========================================

BASE_URL = (
    "https://sniiv.sedatu.gob.mx/api/CuboAPI/GetFinanciamiento"
)

MAX_HTTP_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2
HTTP_TIMEOUT_SECONDS = 120

RETRYABLE_STATUS_CODES = {
    408,
    429,
    500,
    502,
    503,
    504,
}

DIMENSIONS = (
    "anio,mes,estado,municipio,"
    "organismo,destino_credito,genero"
)

REQUIRED_COLUMNS = {
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
}

GRAIN_COLUMNS = (
    "año",
    "mes",
    "clave_estado",
    "clave_municipio",
    "organismo",
    "destino_credito",
    "sexo",
)

VALID_MONTHS = {
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
}


# ==========================================
# PETICIÓN HTTP CON REINTENTOS
# ==========================================

def get_sniiv_response(url: str) -> requests.Response:
    """
    Realiza una petición HTTP al SNIIV.

    Reintenta errores temporales de conexión, timeout
    y determinados códigos HTTP del servidor.
    """

    for attempt in range(1, MAX_HTTP_ATTEMPTS + 1):
        try:
            response = requests.get(
                url,
                timeout=HTTP_TIMEOUT_SECONDS,
            )

            if (
                response.status_code in RETRYABLE_STATUS_CODES
                and attempt < MAX_HTTP_ATTEMPTS
            ):
                delay = RETRY_BACKOFF_SECONDS * (
                    2 ** (attempt - 1)
                )

                print(
                    f"[RETRY] HTTP {response.status_code}. "
                    f"Intento {attempt}/{MAX_HTTP_ATTEMPTS}. "
                    f"Reintentando en {delay} segundos..."
                )

                time.sleep(delay)
                continue

            response.raise_for_status()
            return response

        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        ) as exc:
            if attempt == MAX_HTTP_ATTEMPTS:
                raise

            delay = RETRY_BACKOFF_SECONDS * (
                2 ** (attempt - 1)
            )

            print(
                f"[RETRY] {type(exc).__name__}. "
                f"Intento {attempt}/{MAX_HTTP_ATTEMPTS}. "
                f"Reintentando en {delay} segundos..."
            )

            time.sleep(delay)

    raise RuntimeError(
        "No se pudo obtener respuesta del SNIIV después de "
        f"{MAX_HTTP_ATTEMPTS} intentos."
    )


# ==========================================
# VALIDACIÓN DE LA RESPUESTA
# ==========================================

def validate_response_schema(records: list[dict]) -> None:
    """
    Comprueba que todos los registros tengan
    las columnas requeridas.
    """

    for index, record in enumerate(records):
        missing_columns = REQUIRED_COLUMNS - set(record.keys())

        if missing_columns:
            raise ValueError(
                "Respuesta inválida del SNIIV: "
                f"registro {index} sin columnas requeridas: "
                f"{sorted(missing_columns)}."
            )


def is_valid_number(value: Any) -> bool:
    """
    Comprueba que el valor sea un número finito.

    Rechaza booleanos, cadenas, NaN e infinitos.
    """

    if isinstance(value, bool):
        return False

    if not isinstance(value, (int, float)):
        return False

    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def normalize_month_for_key(value: Any) -> str:
    """
    Normaliza el mes para construir la clave natural.

    Por ejemplo, 1, "1" y "01" representan el mismo mes.
    Los nombres de meses se normalizan a minúsculas.

    No modifica las demás dimensiones, porque no debemos
    asumir que categorías con distinta escritura son iguales.
    """

    if isinstance(value, bool):
        return str(value).strip()

    if isinstance(value, int):
        return str(value)

    if isinstance(value, str):
        month = value.strip().lower()

        if month in VALID_MONTHS:
            return month

        if month.isdigit():
            return str(int(month))

        return month

    return str(value).strip()


def validate_snapshot_records(
    records: list[dict],
    expected_year: int,
) -> None:
    """
    Valida el snapshot completo antes de sustituir
    los archivos anteriores.

    Comprueba:
    - Estructura de la respuesta.
    - Columnas requeridas.
    - Año esperado.
    - Dimensiones obligatorias.
    - Mes válido.
    - Acciones enteras, finitas y no negativas.
    - Monto finito y no negativo.
    - Ausencia de duplicados en la clave natural.
    """

    if not isinstance(records, list):
        raise TypeError(
            "Respuesta inesperada del SNIIV: "
            "se esperaba una lista de registros."
        )

    if not records:
        raise ValueError(
            "Respuesta vacía del SNIIV: "
            "se esperaba al menos un registro."
        )

    if not all(isinstance(record, dict) for record in records):
        raise ValueError(
            "Todos los registros deben ser objetos JSON."
        )

    validate_response_schema(records)

    seen_keys = set()

    for index, record in enumerate(records):

        # ------------------------------------------
        # VALIDAR AÑO
        # ------------------------------------------

        year_value = record["año"]

        if isinstance(year_value, bool):
            raise ValueError(  # noqa: TRY004
                f"Registro {index}: año inválido "
                f"({year_value!r})."
            )

        if isinstance(year_value, int):
            record_year = year_value

        elif (
            isinstance(year_value, str)
            and year_value.strip().isdigit()
        ):
            record_year = int(year_value.strip())

        else:
            raise ValueError(
                f"Registro {index}: año inválido "
                f"({year_value!r})."
            )

        if record_year != expected_year:
            raise ValueError(
                f"Registro {index}: año {year_value} "
                f"distinto del solicitado ({expected_year})."
            )

        # ------------------------------------------
        # VALIDAR DIMENSIONES OBLIGATORIAS
        # ------------------------------------------

        for column in REQUIRED_COLUMNS - {"acciones", "monto"}:
            value = record[column]

            if value is None or not str(value).strip():
                raise ValueError(
                    f"Registro {index}: valor vacío en {column}."
                )

        # ------------------------------------------
        # VALIDAR MES
        # ------------------------------------------

        month_value = record["mes"]

        if isinstance(month_value, bool):
            valid_month = False

        elif isinstance(month_value, int):
            valid_month = 1 <= month_value <= 12

        elif isinstance(month_value, str):
            month = month_value.strip().lower()

            valid_month = (
                month in VALID_MONTHS
                or (
                    month.isdigit()
                    and 1 <= int(month) <= 12
                )
            )

        else:
            valid_month = False

        if not valid_month:
            raise ValueError(
                f"Registro {index}: mes inválido "
                f"({month_value!r})."
            )

        # ------------------------------------------
        # VALIDAR ACCIONES
        # ------------------------------------------

        actions = record["acciones"]

        if not is_valid_number(actions) or actions < 0:
            raise ValueError(
                f"Registro {index}: acciones inválidas "
                f"({actions!r})."
            )

        if not float(actions).is_integer():
            raise ValueError(
                f"Registro {index}: acciones debe ser un entero."
            )

        # ------------------------------------------
        # VALIDAR MONTO
        # ------------------------------------------

        amount = record["monto"]

        if not is_valid_number(amount) or amount < 0:
            raise ValueError(
                f"Registro {index}: monto inválido "
                f"({amount!r})."
            )

        # ------------------------------------------
        # VALIDAR GRANULARIDAD NATURAL
        # ------------------------------------------

        natural_key = tuple(
            (
                normalize_month_for_key(record[column])
                if column == "mes"
                else str(record[column]).strip()
            )
            for column in GRAIN_COLUMNS
        )

        if natural_key in seen_keys:
            raise ValueError(
                f"Registro {index}: clave natural duplicada "
                f"{natural_key}."
            )

        seen_keys.add(natural_key)


# ==========================================
# CONSTRUCCIÓN DE LA URL
# ==========================================

def build_url(year: int) -> str:
    """Construye la URL de consulta al API del SNIIV."""

    return f"{BASE_URL}/{year}/00/000/{DIMENSIONS}"


# ==========================================
# UTILIDADES PARA ARCHIVOS
# ==========================================

def remove_file_if_exists(path: Path) -> None:
    """
    Elimina un archivo si existe.

    Si el archivo no puede eliminarse, la excepción
    se propaga al llamador.
    """

    path.unlink(missing_ok=True)


def restore_previous_file(
    backup_path: Path,
    destination_path: Path,
    old_file_moved: bool,
    new_file_promoted: bool,
) -> None:
    """
    Intenta restaurar un archivo anterior.

    Si existía un archivo anterior y fue respaldado,
    intenta restaurarlo.

    Si no había archivo anterior y se publicó uno nuevo,
    intenta retirarlo.
    """

    if old_file_moved:
        os.replace(backup_path, destination_path)

    elif new_file_promoted and destination_path.exists():
        remove_file_if_exists(destination_path)


# ==========================================
# EXTRACCIÓN DE UN AÑO
# ==========================================

def extract_year(year: int, force: bool = False) -> Path:
    """
    Extrae los datos de un año y publica el snapshot.

    La extracción:
    1. Obtiene los datos del API.
    2. Valida los registros.
    3. Prepara archivos temporales.
    4. Verifica el JSON temporal.
    5. Respalda los archivos anteriores.
    6. Publica el JSON y sus metadatos.
    7. Elimina los respaldos únicamente después del éxito.

    Si falla la publicación, intenta recuperar los archivos
    anteriores y conserva los respaldos que no pueda restaurar.
    """

    if isinstance(year, bool) or not isinstance(year, int):
        raise ValueError(  # noqa: TRY004
            f"El año debe ser un entero válido; se recibió {year!r}."
        )

    if year < 1900 or year > 2200:
        raise ValueError(
            f"El año está fuera del rango permitido: {year}."
        )

    output_dir = SNIIV_RAW_DIR / str(year)

    output_file = output_dir / f"mexico_{year}.json"
    metadata_file = output_dir / f"mexico_{year}_metadata.json"

    temporary_file = output_dir / f"mexico_{year}.json.tmp"
    temporary_metadata = (
        output_dir / f"mexico_{year}_metadata.json.tmp"
    )

    backup_file = output_dir / f"mexico_{year}.json.bak"
    backup_metadata = (
        output_dir / f"mexico_{year}_metadata.json.bak"
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    if output_file.exists() and not force:
        print(
            f"El archivo de {year} ya existe. "
            "Se omite la extracción."
        )
        return output_file

    # No sobrescribir respaldos que podrían ser
    # la única copia recuperable de los datos.
    existing_backups = [
        path
        for path in (backup_file, backup_metadata)
        if path.exists()
    ]

    if existing_backups:
        names = ", ".join(path.name for path in existing_backups)

        raise FileExistsError(
            f"Hay respaldos pendientes ({names}). "
            "Revisa o recupera esos archivos antes de ejecutar "
            "otra extracción."
        )

    url = build_url(year)

    print(f"\n[EXTRACT] Extrayendo datos del año {year}...")

    response = get_sniiv_response(url)
    records = response.json()

    validate_snapshot_records(records, year)

    metadata = {
        "year": year,
        "source": "SNIIV",
        "url": url,
        "extracted_at": datetime.now(UTC).isoformat(),
        "record_count": len(records),
        "status": "success",
    }

    old_json_moved = False
    old_metadata_moved = False

    new_json_promoted = False
    new_metadata_promoted = False

    try:
        # ------------------------------------------
        # PREPARAR JSON TEMPORAL
        # ------------------------------------------

        with temporary_file.open("w", encoding="utf-8") as file:
            json.dump(
                records,
                file,
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            )

        # ------------------------------------------
        # VERIFICAR JSON TEMPORAL
        # ------------------------------------------

        with temporary_file.open("r", encoding="utf-8") as file:
            verified_records = json.load(file)

        validate_snapshot_records(verified_records, year)

        # ------------------------------------------
        # PREPARAR METADATA TEMPORAL
        # ------------------------------------------

        with temporary_metadata.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                metadata,
                file,
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            )

        # ------------------------------------------
        # RESPALDAR ARCHIVOS ANTERIORES
        # ------------------------------------------

        if output_file.exists():
            os.replace(output_file, backup_file)
            old_json_moved = True

        if metadata_file.exists():
            os.replace(metadata_file, backup_metadata)
            old_metadata_moved = True

        # ------------------------------------------
        # PUBLICAR NUEVOS ARCHIVOS
        # ------------------------------------------

        os.replace(temporary_file, output_file)
        new_json_promoted = True

        os.replace(temporary_metadata, metadata_file)
        new_metadata_promoted = True

    except Exception as original_error:
        print(
            f"[ERROR] Falló la publicación del snapshot "
            f"de {year}: {original_error}"
        )

        # Intentar recuperar JSON y metadata de manera
        # independiente para no abandonar la recuperación
        # de metadata si falla la restauración del JSON.
        recovery_errors = []

        try:
            restore_previous_file(
                backup_path=backup_file,
                destination_path=output_file,
                old_file_moved=old_json_moved,
                new_file_promoted=new_json_promoted,
            )

        except OSError as recovery_error:
            recovery_errors.append(
                f"JSON: {recovery_error}"
            )

        try:
            restore_previous_file(
                backup_path=backup_metadata,
                destination_path=metadata_file,
                old_file_moved=old_metadata_moved,
                new_file_promoted=new_metadata_promoted,
            )

        except OSError as recovery_error:
            recovery_errors.append(
                f"metadata: {recovery_error}"
            )

        if recovery_errors:
            print(
                "[CRÍTICO] No se pudo completar la recuperación. "
                "No elimines los archivos .bak. "
                + " | ".join(recovery_errors)
            )

        raise

    finally:
        # La limpieza temporal no debe ocultar el error original.
        for temporary_path in (
            temporary_file,
            temporary_metadata,
        ):
            try:
                remove_file_if_exists(temporary_path)

            except OSError as cleanup_error:
                print(
                    f"[ADVERTENCIA] No se pudo limpiar "
                    f"{temporary_path.name}: {cleanup_error}"
                )

    # La nueva pareja de archivos ya quedó publicada.
    # Los respaldos se eliminan únicamente después del éxito.
    for backup_path in (backup_file, backup_metadata):
        try:
            remove_file_if_exists(backup_path)

        except OSError as cleanup_error:
            print(
                f"[ADVERTENCIA] No se pudo eliminar "
                f"{backup_path.name}: {cleanup_error}"
            )

    print(
        f"[EXTRACT] Extracción de {year} completada correctamente."
    )
    print(f"[EXTRACT] Registros extraídos: {len(records):,}")
    print(f"[EXTRACT] Archivo: {output_file}")

    return output_file


# ==========================================
# EJECUCIÓN PRINCIPAL
# ==========================================

def main() -> None:
    """Ejecuta la extracción para todos los años configurados."""

    for year in SNIIV_YEARS:
        extract_year(year)


if __name__ == "__main__":
    main()