import json
import os
import time
from datetime import UTC, datetime

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

RETRYABLE_STATUS_CODES = {
    408,  # Request Timeout
    429,  # Too Many Requests
    500,  # Internal Server Error
    502,  # Bad Gateway
    503,  # Service Unavailable
    504,  # Gateway Timeout
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


# ==========================================
# PETICIÓN HTTP CON REINTENTOS
# ==========================================

def get_sniiv_response(url: str) -> requests.Response:
    """
    Realiza una petición HTTP con un máximo de tres intentos.

    Reintenta ante errores de conexión, timeout y determinados
    códigos HTTP transitorios.

    Espera 2 segundos antes del segundo intento y 4 antes del tercero.
    """

    for attempt in range(1, MAX_HTTP_ATTEMPTS + 1):
        try:
            response = requests.get(url, timeout=120)
            status_code = response.status_code

            if (
                status_code in RETRYABLE_STATUS_CODES
                and attempt < MAX_HTTP_ATTEMPTS
            ):
                delay = RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1))

                print(
                    f"[RETRY] HTTP {status_code}. "
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

            delay = RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1))

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
    """Comprueba que todos los registros tengan las columnas requeridas."""

    for index, record in enumerate(records):
        missing_columns = REQUIRED_COLUMNS - set(record.keys())

        if missing_columns:
            raise ValueError(
                "Respuesta inválida del SNIIV: "
                f"registro {index} sin columnas requeridas: "
                f"{sorted(missing_columns)}."
            )


# ==========================================
# CONSTRUCCIÓN DE LA URL
# ==========================================

def build_url(year: int) -> str:
    """Construye la URL de consulta al API del SNIIV."""

    return f"{BASE_URL}/{year}/00/000/{DIMENSIONS}"


# ==========================================
# EXTRACCIÓN DE UN AÑO
# ==========================================

def extract_year(year: int, force: bool = False):
    """
    Descarga y guarda los datos de un año.

    Valida la respuesta antes de modificar el archivo original.
    Utiliza un archivo temporal para sustituir el JSON de forma segura.
    """

    output_dir = SNIIV_RAW_DIR / str(year)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"mexico_{year}.json"
    metadata_file = output_dir / f"mexico_{year}_metadata.json"

    if output_file.exists() and not force:
        print(
            f"[SKIP] {year}: el archivo ya existe -> {output_file}"
        )
        return output_file

    url = build_url(year)

    print(f"[EXTRACT] Descargando datos SNIIV para {year}...")
    print(f"[EXTRACT] URL: {url}")

    response = get_sniiv_response(url)

    # 1. Interpretar y validar la respuesta antes de guardar.
    records = response.json()

    if not isinstance(records, list):
        raise TypeError(
            f"Respuesta inesperada del SNIIV para {year}: "
            "se esperaba una lista de registros."
        )

    if not all(isinstance(record, dict) for record in records):
        raise ValueError(
            f"Respuesta inválida del SNIIV para {year}: "
            "todos los registros deben ser objetos JSON."
        )

    if not records:
        raise ValueError(
            f"Respuesta vacía del SNIIV para {year}: "
            "se esperaba al menos un registro."
        )

    validate_response_schema(records)

    # 2. Escribir en un archivo temporal.
    temporary_file = output_file.with_suffix(".json.tmp")

    try:
        temporary_file.write_text(
            response.text,
            encoding="utf-8",
        )

        # 3. Reemplazar el JSON anterior solo después de escribir
        # correctamente el archivo temporal.
        os.replace(temporary_file, output_file)

    finally:
        # Eliminar el temporal si todavía existe.
        if temporary_file.exists():
            temporary_file.unlink()

    # 4. Registrar los metadatos de la extracción.
    metadata = {
        "year": year,
        "source": "SNIIV",
        "url": url,
        "extracted_at": datetime.now(UTC).isoformat(),
        "record_count": len(records),
        "status": "success",
    }

    metadata_file.write_text(
        json.dumps(
            metadata,
            indent=4,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(f"[OK] {year}: archivo guardado -> {output_file}")
    print(f"[OK] {year}: metadata guardada -> {metadata_file}")

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
