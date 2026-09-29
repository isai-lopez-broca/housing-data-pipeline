from datetime import datetime, timezone
from pathlib import Path
import json

import requests

from src.config import SNIIV_RAW_DIR, SNIIV_YEARS


BASE_URL = "https://sniiv.sedatu.gob.mx/api/CuboAPI/GetFinanciamiento"

DIMENSIONS = (
    "anio,mes,estado,municipio,"
    "organismo,destino_credito,genero"
)


def build_url(year: int) -> str:
    """
    Construye la URL de consulta al API de financiamiento del SNIIV.
    """

    return f"{BASE_URL}/{year}/00/000/{DIMENSIONS}"


def extract_year(year: int, force: bool = False) -> Path:
    """
    Descarga los datos mensuales de un año y los guarda
    como JSON dentro del directorio raw correspondiente.

    Si el archivo ya existe, no se vuelve a descargar,
    a menos que force=True.

    También genera un archivo de metadata con información
    sobre la extracción realizada.
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

    response = requests.get(
        url,
        timeout=120,
    )

    response.raise_for_status()

    output_file.write_text(
        response.text,
        encoding="utf-8",
    )

    records = response.json()

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

    print(
        f"[OK] {year}: archivo guardado -> "
        f"{output_file}"
    )

    print(
        f"[OK] {year}: metadata guardada -> "
        f"{metadata_file}"
    )

    return output_file


def main() -> None:
    """
    Ejecuta la extracción para todos los años configurados.
    """

    for year in SNIIV_YEARS:
        extract_year(year)


if __name__ == "__main__":
    main()
