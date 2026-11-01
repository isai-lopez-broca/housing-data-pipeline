# Housing Data Pipeline

**Pipeline de ingeniería de datos para analizar el financiamiento de vivienda en México a partir de información del Sistema Nacional de Información e Indicadores de Vivienda (SNIIV).**

Este proyecto integra datos públicos, aplica validaciones de calidad, transforma archivos JSON a Parquet y carga la información en un almacén de datos dimensional en PostgreSQL. El objetivo es facilitar el análisis de la evolución temporal y las diferencias territoriales del financiamiento de vivienda en México.

## Objetivo del proyecto

Responder la siguiente pregunta de negocio:

> ¿Cómo está evolucionando el financiamiento de vivienda en México y qué diferencias existen entre territorios, periodos y características del financiamiento?

Para responderla, el proyecto construye un flujo de procesamiento reproducible que convierte datos de una fuente pública en información estructurada para consultas analíticas.

## Características principales

- **Ingesta de datos:** extracción de información desde la API del SNIIV.
- **Resiliencia en la extracción:** reintentos ante determinados errores HTTP y fallos temporales de conexión.
- **Validación de datos:** comprobaciones de estructura, valores, periodos y registros duplicados.
- **Transformación:** limpieza y normalización de datos mediante Python y pandas.
- **Formato analítico:** almacenamiento de los datos procesados en archivos Parquet.
- **Data Warehouse:** modelo dimensional en PostgreSQL mediante un esquema en estrella.
- **Carga transaccional:** carga de dimensiones y hechos con confirmación o reversión de la transacción.
- **Control de calidad:** detección de errores, advertencias, problemas de integridad referencial y posibles meses faltantes.
- **Pruebas automatizadas:** suite de pruebas con pytest.
- **Integración continua:** ejecución automática de pruebas mediante GitHub Actions.

## Arquitectura

El proyecto utiliza una arquitectura de procesamiento por lotes (*batch processing*).

```text
             SNIIV / SEDATU
                    |
                    v
             API de financiamiento
                    |
                    v
           Extracción con Python
                    |
                    v
          Datos originales en JSON
                    |
                    v
           Validación de datos
                    |
                    v
        Transformación con pandas
                    |
                    v
           Archivos Parquet
                    |
                    v
       Creación del Data Warehouse
                    |
                    v
         Carga dimensional y hechos
                    |
                    v
              PostgreSQL
                    |
                    v
        Auditoría de calidad de datos
                    |
                    v
          Consultas de análisis SQL
```

El flujo está coordinado por `src/run_pipeline.py`, que ejecuta las etapas del procesamiento y detiene el flujo cuando una etapa crítica falla.

### Etapas del pipeline

| Etapa | Módulo | Responsabilidad |
|---|---|---|
| Configuración | `src/config.py` | Define rutas, directorios y años de procesamiento. |
| Extracción | `src/extract_sniiv.py` | Obtiene datos de la API y guarda los archivos originales. |
| Validación | `src/validate_sniiv.py` | Comprueba estructura, valores y duplicados. |
| Transformación | `src/transform_sniiv.py` | Normaliza los datos y genera archivos Parquet. |
| Creación del almacén | `src/create_warehouse.py` | Ejecuta los scripts SQL para crear dimensiones y hechos. |
| Carga | `src/load_warehouse.py` | Carga las dimensiones y la tabla de hechos. |
| Auditoría | `src/audit_data_quality.py` | Revisa la calidad y la integridad de los datos. |
| Orquestación | `src/run_pipeline.py` | Coordina las etapas del pipeline. |

## Tecnologías utilizadas

| Tecnología | Uso |
|---|---|
| Python 3.12 | Implementación del pipeline. |
| pandas | Manipulación y transformación de datos tabulares. |
| Requests | Comunicación HTTP con la API. |
| PostgreSQL | Base de datos relacional y Data Warehouse. |
| psycopg2 | Conexión y operaciones con PostgreSQL desde Python. |
| Parquet | Almacenamiento columnar de los datos procesados. |
| PyArrow | Soporte para lectura y escritura de Parquet. |
| SQL | Modelado dimensional y consultas analíticas. |
| pytest | Pruebas automatizadas. |
| Git y GitHub | Control de versiones y colaboración. |
| GitHub Actions | Integración continua y ejecución automatizada de pruebas. |

## Fuente de datos

El proyecto utiliza el servicio de financiamiento del SNIIV, perteneciente al ámbito de la Secretaría de Desarrollo Agrario, Territorial y Urbano (SEDATU).

- **Fuente:** Sistema Nacional de Información e Indicadores de Vivienda.
- **Servicio utilizado:** `GetFinanciamiento`.
- **URL del servicio:** https://sniiv.sedatu.gob.mx/api/CuboAPI/GetFinanciamiento
- **Periodo de estudio:** 2023–2026.
- **Cobertura de 2026 documentada en el análisis:** enero a junio.

Los archivos originales se almacenan en formato JSON y posteriormente se transforman a Parquet.

La fuente puede actualizar o revisar sus datos históricos, por lo que los resultados pueden cambiar entre ejecuciones realizadas en diferentes fechas.

## Modelo del Data Warehouse

El almacén utiliza un **esquema en estrella**, con una tabla de hechos central relacionada con cinco dimensiones.

### Tabla de hechos

`fact_financiamiento`

Contiene las medidas de financiamiento y las claves que relacionan cada registro con las dimensiones.

Medidas principales:

- `acciones`
- `monto`

### Dimensiones

| Tabla | Información |
|---|---|
| `dim_fecha` | Año y mes. |
| `dim_territorio` | Estado y municipio. |
| `dim_organismo` | Organismo ejecutor. |
| `dim_destino` | Destino del crédito. |
| `dim_sexo` | Categoría de sexo reportada. |

Las dimensiones permiten analizar las medidas desde diferentes perspectivas temporales, territoriales e institucionales.

La granularidad de la tabla de hechos se define mediante la combinación de las claves de las cinco dimensiones. Esta combinación cuenta con una restricción de unicidad para evitar duplicados en el grano definido.

El diseño detallado se encuentra en [`docs/warehouse_design.md`](docs/warehouse_design.md).

## Calidad de datos y confiabilidad

La calidad de los datos se comprueba en diferentes etapas.

### Durante la extracción

- Validación de la respuesta HTTP.
- Comprobación de la estructura JSON.
- Verificación de las columnas requeridas.
- Reintentos ante determinados errores temporales.
- Escritura mediante un archivo temporal para evitar sustituir directamente el archivo existente con una respuesta inválida.
- Registro de metadatos de extracción.

### Durante la validación

- Comprobación de columnas esperadas.
- Detección de valores nulos y textos vacíos.
- Validación de años y nombres de meses.
- Comprobación de valores numéricos, finitos y no negativos para las medidas.
- Detección de duplicados según el grano natural definido.

### Durante la carga y auditoría

- Uso de transacciones para confirmar o revertir la carga.
- Comprobación de integridad referencial.
- Detección de duplicados y valores problemáticos.
- Identificación de posibles meses faltantes.
- Clasificación de incidencias entre errores y advertencias.

Las advertencias no provocan necesariamente que el pipeline falle. Los errores críticos de calidad sí pueden detenerlo.

## Resultados analíticos

El análisis documentado permite observar la evolución anual de las acciones de financiamiento reportadas por la fuente.

| Año | Acciones reportadas |
|---|---:|
| 2023 | 762,769 |
| 2024 | 881,447 |
| 2025 | 998,804 |
| 2026, enero–junio | 427,755 |

**Importante:** 2026 contiene información parcial. Por lo tanto, sus cifras no deben compararse directamente con las de años completos como si tuvieran la misma cobertura temporal.

El proyecto también contiene consultas para:

- Analizar la evolución mensual de acciones y montos.
- Comparar resultados territoriales por año.
- Identificar concentraciones municipales.
- Explorar diferencias entre organismos y destinos del financiamiento.

Los hallazgos, las discrepancias detectadas y las consideraciones metodológicas están documentados en [`docs/analytics_findings.md`](docs/analytics_findings.md).

### Consideraciones sobre la interpretación

- `acciones` representa las acciones reportadas por el organismo ejecutor; no debe interpretarse automáticamente como número de viviendas únicas, créditos o personas beneficiarias.
- `monto` representa el importe monetario reportado por la fuente. El análisis actual no aplica un ajuste por inflación.
- La razón `monto / acciones` es descriptiva y no equivale necesariamente al precio promedio de una vivienda ni al importe promedio de un crédito.
- La ausencia de registros en un mes no demuestra, por sí sola, que el valor real de ese mes sea cero.
- Los datos de diferentes publicaciones pueden presentar pequeñas discrepancias. Estas deben documentarse e investigarse, no corregirse arbitrariamente.

## Estructura del repositorio

```text
housing-data-pipeline/
├── .github/
│   └── workflows/
│       └── tests.yml
├── data/
│   ├── raw/
│   └── processed/
├── docs/
│   ├── analytics_findings.md
│   └── warehouse_design.md
├── sql/
│   ├── 01_create_dimensions.sql
│   ├── 02_create_fact.sql
│   └── analytics/
│       ├── 01_evolucion_mensual.sql
│       └── 02_ranking_territorial.sql
├── src/
│   ├── __init__.py
│   ├── audit_data_quality.py
│   ├── config.py
│   ├── create_warehouse.py
│   ├── database.py
│   ├── extract_sniiv.py
│   ├── load_warehouse.py
│   ├── run_pipeline.py
│   ├── transform_sniiv.py
│   └── validate_sniiv.py
├── tests/
│   ├── test_data_quality_sniiv.py
│   ├── test_extract_sniiv.py
│   ├── test_load_warehouse.py
│   ├── test_monitor_data_quality.py
│   ├── test_run_pipeline.py
│   ├── test_transform_sniiv.py
│   └── test_validate_sniiv.py
├── .gitignore
└── requirements.txt
```

Los archivos JSON originales y los Parquet procesados se generan localmente y se excluyen del control de versiones mediante `.gitignore`.

## Requisitos previos

Antes de ejecutar el proyecto, necesitas:

- Python 3.12.
- PostgreSQL.
- Git.
- Acceso a internet para consultar la API.
- Una terminal compatible con los comandos siguientes.

Los comandos están escritos para Linux o Ubuntu en WSL.

## Instalación y configuración

### 1. Clonar el repositorio

```bash
git clone https://github.com/isai-lopez-broca/housing-data-pipeline.git
cd housing-data-pipeline
```

### 2. Crear y activar el entorno virtual

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar las dependencias

```bash
python -m pip install -r requirements.txt
```

Verifica que las dependencias sean compatibles:

```bash
python -m pip check
```

### 4. Configurar PostgreSQL

Crea una base de datos y un usuario con los permisos necesarios para crear tablas, insertar registros y actualizar datos dentro de la base.

Este proyecto utiliza la configuración de conexión definida en `src/database.py`.

### 5. Configurar las variables de entorno

Crea un archivo `.env` en la raíz del proyecto:

```bash
nano .env
```

Agrega las siguientes variables y sustituye los valores de ejemplo por tus credenciales locales:

```dotenv
DB_HOST=localhost
DB_PORT=5432
DB_NAME=housing_db
DB_USER=housing_user
DB_PASSWORD=your_password
```

Guarda el archivo y cierra el editor.

**Seguridad:** no publiques el archivo `.env`, no incluyas contraseñas reales en el código y no compartas credenciales en commits o capturas de pantalla. El repositorio excluye `.env` mediante `.gitignore`.

## Ejecutar el pipeline

Desde la raíz del repositorio, con el entorno virtual activado y PostgreSQL disponible, ejecuta:

```bash
python -m src.run_pipeline
```

El flujo procesa los años configurados en `src/config.py`, realiza las validaciones y transformaciones correspondientes, prepara el Data Warehouse, carga los datos y ejecuta las comprobaciones de calidad.

El comportamiento de extracción contempla archivos existentes, por lo que una nueva ejecución no implica necesariamente volver a descargar todos los datos. Consulta la implementación de extracción y la configuración antes de forzar una nueva descarga.

## Ejecutar las pruebas

Para ejecutar toda la suite:

```bash
python -m pytest -v
```

Para ejecutar únicamente las pruebas de validación y transformación:

```bash
python -m pytest -v tests/test_validate_sniiv.py tests/test_transform_sniiv.py
```

La suite comprueba aspectos como:

- Validación de registros y columnas.
- Tratamiento de errores de extracción.
- Conversión de meses y creación de claves temporales.
- Comportamiento transaccional de la carga.
- Orden de ejecución del pipeline.
- Detección de problemas de calidad.

**Estado documentado:** 46 pruebas aprobadas después de alinear la validación de los nombres de meses con el formato real de SNIIV.

Las pruebas automatizadas no sustituyen una ejecución completa del pipeline contra la base de datos de cada entorno.

## Consultas analíticas

Las consultas SQL se encuentran en `sql/analytics/`.

Por ejemplo, puedes ejecutar la consulta de evolución mensual desde la raíz del repositorio:

```bash
psql -h localhost -U housing_user -d housing_db \
  -f sql/analytics/01_evolucion_mensual.sql
```

Para consultar el ranking territorial:

```bash
psql -h localhost -U housing_user -d housing_db \
  -f sql/analytics/02_ranking_territorial.sql
```

Estos comandos requieren tener instalado el cliente `psql`, acceso a PostgreSQL y los permisos correspondientes.

## Integración continua

El repositorio utiliza GitHub Actions para ejecutar las pruebas automatizadas en los eventos configurados en `.github/workflows/tests.yml`.

El flujo de integración continua instala las dependencias y ejecuta:

```bash
python -m pytest -v
```

Esto ayuda a detectar regresiones cuando se realizan cambios en el código.

## Alcance actual y siguientes mejoras

El proyecto se centra actualmente en construir un pipeline batch reproducible y un Data Warehouse analítico.

Entre las posibles mejoras futuras se encuentran:

- Mejorar el seguimiento de cambios en los datos históricos de la fuente.
- Incorporar mecanismos de actualización incremental cuando exista una estrategia fiable para detectar cambios y procesar únicamente los datos necesarios.
- Ampliar las pruebas de integración con PostgreSQL.
- Automatizar ejecuciones programadas mediante una herramienta de orquestación cuando el proyecto lo requiera.
- Evaluar opciones de despliegue en la nube según las necesidades de almacenamiento, procesamiento y disponibilidad.

Estas mejoras son propuestas futuras y no forman parte de las capacidades declaradas del pipeline actual.

## Autor

Proyecto personal de portafolio enfocado en ingeniería de datos, procesamiento batch, calidad de datos, modelado dimensional y análisis con SQL.

**Repositorio:** [housing-data-pipeline](https://github.com/isai-lopez-broca/housing-data-pipeline)
