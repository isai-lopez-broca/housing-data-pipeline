from datetime import datetime, timezone
import json
import os

import requests

from src.config import SNIIV_RAW_DIR, SNIIV_YEARS


BASE_URL = "https://sniiv.sedatu.gob.mx/api/CuboAPI/GetFinanciamiento"

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


def validate_response_schema(records: list[dict]) -> None:
    """Comprueba que todos los registros tengan las columnas requeridas."""

    for index, record in enumerate(records):
        missing_columns = REQUIRED_COLUMNS - set(record.keys())

        if missing_columns:
            raise ValueError(
                f"Respuesta inválida del SNIIV: "
                f"registro {index} sin columnas requeridas: "
                f"{sorted(missing_columns)}."
            )


def build_url(year: int) -> str:
    """Construye la URL de consulta al API del SNIIV."""

    return f"{BASE_URL}/{year}/00/000/{DIMENSIONS}"


def extract_year(year: int, force: bool = False):
    """
    Descarga y guarda los datos de un año.

    Comprueba la respuesta antes de modificar el archivo original.
    Utiliza un archivo temporal para sustituir el JSON de forma segura.
    """

    output_dir = SNIIV_RAW_DIR / str(year)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"mexico_{year}.json"
    metadata_file = output_dir / f"mexico_{year}_metadata.json"

    if output_file.exists() and not force:
        print(
            f"[SKIP] {year}: el archivo ya existe -> "
            f"{output_file}"
        )
        return output_file

    url = build_url(year)

    print(f"[EXTRACT] Descargando datos SNIIV para {year}...")
    print(f"[EXTRACT] URL: {url}")

    response = requests.get(url, timeout=120)
    response.raise_for_status()

    # 1. Interpretar y comprobar la respuesta antes de guardar.
    records = response.json()

    if not isinstance(records, list):
        raise ValueError(
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

    # 2. Escribir primero en un archivo temporal.
    temporary_file = output_file.with_suffix(".json.tmp")

    try:
        temporary_file.write_text(
            response.text,
            encoding="utf-8",
        )

        # 3. Sustituir el archivo original solo cuando el temporal
        #    ya se escribió correctamente.
        os.replace(temporary_file, output_file)

    finally:
        # Limpiar el temporal si la escritura o sustitución falla.
        if temporary_file.exists():
            temporary_file.unlink()

    # 4. Registrar los metadatos de la extracción.
    metadata = {
        "year": year,
        "source": "SNIIV",
        "url": url,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
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


def main() -> None:
    """Ejecuta la extracción para todos los años configurados."""

    for year in SNIIV_YEARS:
        extract_year(year)


if __name__ == "__main__":
    main()
