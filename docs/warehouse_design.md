# Diseño del Data Warehouse — Housing Data Pipeline

## 1. Objetivo

El Data Warehouse permite analizar la evolución del financiamiento de vivienda registrado por el Sistema Nacional de Información e Indicadores de Vivienda (SNIIV), comparar su distribución territorial y estudiar las diferencias por organismo ejecutor, destino del financiamiento, sexo y periodo.

**Pregunta principal del proyecto:**

> ¿Cómo está evolucionando el financiamiento de vivienda en México y qué diferencias existen entre territorios, periodos y características del financiamiento?

El alcance se limita a las acciones y los montos reportados por la fuente. No pretende medir directamente la construcción de viviendas ni identificar viviendas o personas únicas.

## 2. Arquitectura dimensional

Se utiliza un modelo dimensional tipo estrella implementado en PostgreSQL.

La tabla central es `fact_financiamiento`, relacionada mediante claves foráneas con cinco dimensiones:

- `dim_fecha`
- `dim_territorio`
- `dim_organismo`
- `dim_destino`
- `dim_sexo`

### Esquema conceptual

```text
                    dim_fecha
                        |
                        |
dim_territorio ---- fact_financiamiento ---- dim_organismo
                        |
                        |
                  dim_destino
                        |
                        |
                     dim_sexo
```

## 3. Grano de la tabla de hechos

El grano representa el nivel de detalle de cada registro de la tabla de hechos.

En este proyecto, cada registro corresponde a una combinación única de:

- Clave de fecha que representa el periodo mensual del registro.
- Territorio.
- Organismo ejecutor.
- Destino del financiamiento.
- Sexo reportado.

La restricción `uq_fact_grain` protege esta combinación mediante una restricción `UNIQUE` sobre las cinco claves dimensionales.

Esta unicidad evita duplicar la misma combinación dimensional dentro del almacén. No demuestra que cada acción represente una vivienda única.

## 4. Tabla de hechos: `fact_financiamiento`

La tabla contiene las claves de las cinco dimensiones y las métricas utilizadas en el análisis.

| Columna | Tipo de dato | Descripción |
|---|---|---|
| `financiamiento_key` | `BIGINT` | Clave primaria sustituta generada automáticamente. |
| `fecha_key` | `INTEGER` | Referencia a `dim_fecha`. |
| `territorio_key` | `INTEGER` | Referencia a `dim_territorio`. |
| `organismo_key` | `INTEGER` | Referencia a `dim_organismo`. |
| `destino_key` | `INTEGER` | Referencia a `dim_destino`. |
| `sexo_key` | `SMALLINT` | Referencia a `dim_sexo`. |
| `acciones` | `BIGINT` | Número de acciones de financiamiento o subsidios reportadas. |
| `monto` | `NUMERIC(30,12)` | Importe monetario reportado por el organismo ejecutor, interpretado en MXN. |

### Reglas de integridad

- Las cinco claves dimensionales son obligatorias.
- Las claves foráneas deben apuntar a registros existentes en sus dimensiones.
- `acciones` no puede ser negativo.
- `monto` no puede ser negativo.
- La combinación de las cinco claves dimensionales debe ser única.

Estas reglas se implementan en `sql/02_create_fact.sql`.

## 5. Dimensiones

### `dim_fecha`

Permite analizar los datos por periodo.

- `fecha_key`: clave primaria.
- `anio`: año.
- `mes_numero`: número de mes, restringido al intervalo de 1 a 12.
- `mes_nombre`: nombre del mes.

### `dim_territorio`

Permite analizar la distribución territorial a nivel estatal y municipal.

- `territorio_key`: clave primaria sustituta.
- `clave_estado`: clave del estado.
- `estado`: nombre del estado.
- `clave_municipio`: clave del municipio.
- `municipio`: nombre del municipio.

La combinación de `clave_estado` y `clave_municipio` es única dentro de la dimensión.

### `dim_organismo`

Identifica al organismo que reporta el financiamiento.

- `organismo_key`: clave primaria sustituta.
- `organismo`: nombre del organismo, con restricción de unicidad.

### `dim_destino`

Permite analizar las categorías de destino del financiamiento.

- `destino_key`: clave primaria sustituta.
- `destino_credito`: categoría de destino, con restricción de unicidad.

### `dim_sexo`

Permite segmentar los registros según la categoría de sexo reportada por la fuente.

- `sexo_key`: clave primaria sustituta.
- `sexo`: categoría reportada, con restricción de unicidad.

Las categorías conservan el significado proporcionado por la fuente.

## 6. Métricas e interpretación

### Acciones

Representan las acciones de financiamiento o subsidios reportadas por el organismo ejecutor. Su significado específico puede variar según el organismo y el tipo de financiamiento.

No deben interpretarse automáticamente como viviendas únicas ni como personas beneficiarias.

### Monto

Representa el recurso monetario ejercido reportado por el organismo ejecutor. Se interpreta en pesos mexicanos (MXN), sin asumir un año base de precios que no esté especificado en la documentación consultada.

### Monto por acción

Se calcula como el monto agregado dividido entre las acciones agregadas, siempre que el denominador sea distinto de cero.

Es un indicador descriptivo de los registros analizados, no una estimación automática del precio promedio de una vivienda ni del importe promedio de un crédito individual.

## 7. Consultas analíticas

Las consultas SQL se encuentran en `sql/analytics/`.

- `01_evolucion_mensual.sql`: compara las acciones y los montos mensuales de CONAVI para el destino Mejoramientos en el Estado de México entre 2024 y 2025.
- `02_ranking_territorial.sql`: agrega acciones, montos y monto por acción por estado y año.

El segundo análisis debe considerar que 2026 contiene únicamente los meses disponibles en la extracción, de enero a junio.

## 8. Archivos de implementación

- `sql/01_create_dimensions.sql`: definición de las dimensiones.
- `sql/02_create_fact.sql`: definición de la tabla de hechos y sus restricciones.
- `src/create_warehouse.py`: creación del almacén de datos.
- `src/load_warehouse.py`: carga del almacén de datos.

## 9. Fuentes y limitaciones

La fuente principal es el cubo de financiamiento del SNIIV, administrado por SEDATU.

- SNIIV — Datos abiertos: https://sniiv.sedatu.gob.mx/Reporte/Datos_abiertos
- CONAVI — Diccionario de variables de los módulos SNIIV: https://www.conavi.gob.mx/documentos/Fracc_XLVIII/Modulos%20SNIIV%20Variables.pdf

Los datos históricos pueden ser revisados por la fuente. Los resultados dependen de la extracción utilizada y deben interpretarse considerando la cobertura temporal y las definiciones originales de las variables.
