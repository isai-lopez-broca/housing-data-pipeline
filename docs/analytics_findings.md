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

Durante enero-junio de 2025, el segmento formado por Estado de México, organismo CONAVI y destino Mejoramientos registró 80,818 acciones.

La distribución mensual observada fue:

* Febrero: 47,763 acciones.
* Mayo: 33,055 acciones.

También se identificaron registros en septiembre, octubre y diciembre de 2025. En el periodo comparable de enero-junio de 2024, el mismo segmento registró 2,982 acciones en febrero y no presentó filas para los demás meses en los resultados consultados.

La distribución municipal de 2025 mostró concentraciones importantes en Valle de Chalco Solidaridad, Ecatepec de Morelos, Ixtapaluca, Nezahualcóyotl y Chalco.

Estos resultados describen los registros disponibles en la fuente. Por sí solos no permiten determinar la causa del comportamiento observado ni confirmar que cada acción corresponda a una vivienda única.

## 4. Consideraciones sobre la calidad e interpretación

* Los meses sin filas en una consulta agregada se consideran periodos sin registros observados para esa combinación de dimensiones; no se convierten automáticamente en ceros.
* La variable `acciones` conserva el significado reportado por la fuente y no se interpreta automáticamente como viviendas, créditos o personas únicas.
* La variable `monto` se conserva con la precisión disponible en la fuente. Su unidad debe confirmarse antes de asignarle una etiqueta monetaria específica.
* Los datos de 2026 cubren únicamente enero-junio.
* Los datos históricos del SNIIV pueden ser revisados por la fuente; las cifras pueden cambiar entre extracciones.
* Las diferencias observadas describen asociaciones y patrones, no causas demostradas.

## 5. Próximos pasos

1. Automatizar la ejecución de las consultas analíticas.
2. Incorporar pruebas que validen las agregaciones y el grano de la tabla de hechos.
3. Analizar diferencias por organismo, destino y sexo.
4. Documentar la fecha de extracción y la evolución de los datos históricos.
5. Evaluar la publicación de resultados y visualizaciones en el README del repositorio.
