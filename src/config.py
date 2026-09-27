from pathlib import Path


# ==========================================
# RUTA BASE DEL PROYECTO
# ==========================================

BASE_DIR = Path(__file__).resolve().parent.parent


# ==========================================
# DIRECTORIOS DE DATOS
# ==========================================

DATA_DIR = BASE_DIR / "data"

RAW_DATA_DIR = DATA_DIR / "raw"

SNIIV_RAW_DIR = RAW_DATA_DIR / "sniiv"


# ==========================================
# DIRECTORIOS DEL PROYECTO
# ==========================================

DOCS_DIR = BASE_DIR / "docs"

SQL_DIR = BASE_DIR / "sql"

TESTS_DIR = BASE_DIR / "tests"


# ==========================================
# AÑOS DISPONIBLES
# ==========================================

SNIIV_YEARS = [2023, 2024, 2025, 2026]
