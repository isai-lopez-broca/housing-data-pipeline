# Hallazgos analíticos — Financiamiento de vivienda en México

## 1. Objetivo

Analizar la evolución temporal y la distribución territorial de las acciones y los montos de financiamiento registrados por el Sistema Nacional de Información e Indicadores de Vivienda (SNIIV), utilizando datos de 2023 a 2026.

La pregunta de investigación es:

**¿Cómo está evolucionando el financiamiento de vivienda en México y qué diferencias existen entre territorios, periodos y características del financiamiento?**

Fuente: API de financiamiento del SNIIV, SEDATU.

## 2. Alcance y metodología

* Periodo disponible: enero de 2023 a junio de 2026.
* Granularidad analítica: mes, territorio, organismo, destino del financiamiento y sexo.
* Almacenamiento analítico: PostgreSQL, mediante un esquema dimensional en estrella.
* Consultas reproducibles: `sql/analytics/01_evolucion_mensual.sql` y `sql/analytics/02_ranking_territorial.sql`.

El análisis utiliza las dimensiones y la tabla de hechos del almacén de datos para agregar las métricas por periodo y territorio.

## 3. Hallazgos principales

### 3.1. Evolución nacional

Los resultados agregados muestran un crecimiento de las acciones registradas entre 2023 y 2025:

* 2023: 762,769 acciones.
* 2024: 881,447 acciones.
* 2025: 998,804 acciones.
* 2026: 427,755 acciones entre enero y junio.

Los años 2023, 2024 y 2025 cubren doce meses. El dato de 2026 es parcial y no debe compararse directamente con los totales anuales completos.

### 3.2. Diferencias territoriales

Los estados presentan diferencias tanto en el total de acciones como en el monto agregado. El ranking territorial permite identificar los estados con mayor volumen registrado y comparar su posición entre años.

El monto por acción se utiliza como indicador descriptivo, calculado dividiendo el monto agregado entre las acciones agregadas. No debe interpretarse automáticamente como el valor promedio de una vivienda, un crédito o una persona beneficiaria.

### 3.3. Caso de estudio: CONAVI y Mejoramientos en el Estado de México

Durante enero-junio de 2025, el segmento formado por Estado de México, organismo CONAVI y destino Mejoramientos registró 80,818 acciones, distribuidas entre febrero y mayo:

- Febrero: 47,763 acciones.
- Mayo: 33,055 acciones.

La suma de ambos meses coincide con el total observado para el primer semestre. En la consulta realizada no se encontraron registros para enero, marzo, abril ni junio de 2025 para esta combinación de dimensiones.

Al ampliar la revisión a todo 2025, también se identificaron registros en julio (17,120 acciones), septiembre (12), octubre (1,354) y diciembre (810).

En 2024, la misma combinación registró 2,982 acciones en febrero y 11 en julio. No se encontraron registros en los demás meses de ese año en la consulta realizada.

La distribución municipal de 2025 mostró concentraciones importantes en Valle de Chalco Solidaridad, Ecatepec de Morelos, Ixtapaluca, Nezahualcóyotl y Chalco.

Estos resultados describen los registros disponibles en el almacén para la extracción analizada. No permiten determinar por sí solos las causas de las variaciones observadas ni confirmar que cada acción corresponda a una vivienda única.

## 4. Consideraciones sobre la calidad e interpretación

* La variable `acciones` representa el número de acciones de financiamiento o subsidios reportadas por el organismo ejecutor. Su interpretación específica puede variar según el organismo y el tipo de financiamiento. No debe asumirse que cada acción equivale a una vivienda única o a una persona beneficiaria.
* La variable `monto` representa el recurso monetario ejercido reportado por el organismo ejecutor. Para este proyecto se interpreta en pesos mexicanos (MXN), no como un conteo de viviendas. La documentación consultada no especifica un año base de precios; por ello, no se debe asumir que los montos están ajustados por inflación.
* Los registros con `acciones = 0` y `monto > 0`, o con `acciones > 0` y `monto = 0`, no se eliminan automáticamente. Se conservan para su análisis y deben interpretarse según el organismo, el destino y la definición de las variables en la fuente.
* Los meses sin filas en una consulta agregada se consideran periodos sin registros observados para esa combinación de dimensiones; no se convierten automáticamente en ceros.
* Los datos de 2026 cubren únicamente enero-junio.
* Los datos históricos del SNIIV pueden ser revisados por la fuente; las cifras pueden cambiar entre extracciones.
* Las diferencias observadas describen asociaciones y patrones, no causas demostradas.

## 5. Próximos pasos

1. Automatizar la ejecución de las consultas analíticas.
2. Incorporar pruebas que validen las agregaciones y el grano de la tabla de hechos.
3. Analizar diferencias por organismo, destino y sexo.
4. Documentar la fecha de extracción y la evolución de los datos históricos.
5. Evaluar la publicación de resultados y visualizaciones en el README del repositorio.

## 6. Fuentes y definiciones de las variables

1. **SNIIV — Datos abiertos, SEDATU.** Fuente de los datos de financiamiento utilizados en el proyecto: https://sniiv.sedatu.gob.mx/Reporte/Datos_abiertos
2. **CONAVI — Diccionario de variables de los módulos SNIIV.** Define `Monto` como el recurso ejercido por el organismo ejecutor y `Acciones` como el número de acciones de financiamiento o subsidios ejercidos: https://www.conavi.gob.mx/documentos/Fracc_XLVIII/Modulos%20SNIIV%20Variables.pdf

Las definiciones se interpretan en el contexto del cubo de financiamiento utilizado por el proyecto. Las unidades monetarias se documentan como pesos mexicanos; no se atribuye a los montos un año base de precios que no esté especificado en la documentación consultada.

Fecha de consulta de las fuentes: octubre de 2026.

## Discrepancia entre SNIIV y el reporte de CONAVI: Ecatepec, 2025

### Contexto

Durante el análisis del incremento de acciones de mejoramiento de vivienda en el Estado de México, se compararon los datos de la combinación CONAVI + Mejoramientos para enero-junio de 2025 con el reporte semestral de CONAVI.

### Resultados de la validación

Para el conjunto de datos almacenado en el proyecto, los siguientes resultados coinciden:

| Etapa | Acciones | Monto |
|---|---:|---:|
| JSON original de SNIIV | 80,818 | $3,232,720,000.00 |
| Parquet procesado | 80,818 | $3,232,720,000.00 |
| PostgreSQL | 80,818 | $3,232,720,000.00 |

La comparación por mes, municipio y sexo para la combinación investigada no encontró diferencias entre Parquet y PostgreSQL en 2024 ni en 2025.

### Diferencia observada en Ecatepec

En el reporte semestral de CONAVI se identificaron 80,819 acciones por $3,232,760,000.00 para el conjunto de municipios considerado. La comparación municipal mostró que 15 municipios coinciden con el cuadro consultado, mientras que Ecatepec presenta una diferencia:

| Fuente | Acciones | Monto |
|---|---:|---:|
| Datos del proyecto | 12,456 | $498,240,000.00 |
| Reporte semestral de CONAVI | 12,457 | $498,280,000.00 |
| Diferencia (proyecto menos reporte) | -1 | -$40,000.00 |

La revisión del JSON original, el Parquet y PostgreSQL confirma que las tres etapas contienen el mismo resultado para Ecatepec: 12,456 acciones y $498,240,000.00.

### Interpretación y limitaciones

La diferencia no se explica por una discrepancia detectada entre las tres etapas del pipeline. La causa de la diferencia entre el conjunto publicado por SNIIV y el reporte de CONAVI permanece sin confirmar.

SIESCO advierte que su padrón de beneficiarios contiene datos acumulados y que puede presentar variaciones frente a lo reportado en cada trimestre. Esta advertencia es contexto relevante, pero no demuestra la causa específica de la diferencia observada.

No se añadieron registros ni se modificaron cifras para forzar la coincidencia entre fuentes. Hasta contar con una aclaración oficial o evidencia adicional, ambas cifras deben conservarse con su fuente y periodo de referencia.

### Fuentes

- SNIIV, Datos abiertos: https://sniiv.sedatu.gob.mx/Reporte/Datos_abiertos
- SIESCO, Padrón de beneficiarios y reportes de autoevaluación: https://siesco.conavi.gob.mx/Siesco/Padron
- Reporte de CONAVI consultado: segundo trimestre de 2025.
- CONAVI, Reporte del segundo trimestre de 2025: https://siesco.conavi.gob.mx/doc/mensual/202506.pdf