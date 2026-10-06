# Diseño del Data Warehouse — Housing Data Pipeline

## 1. Objetivo

El Data Warehouse permitirá analizar la evolución del financiamiento de vivienda en México a través del tiempo y comparar diferencias entre territorios, organismos, destinos de crédito y sexo.

Pregunta principal del proyecto:

> ¿Cómo está evolucionando la oferta y el financiamiento de vivienda en México, y qué diferencias existen entre territorios y tipos de vivienda?

---

## 2. Modelo dimensional

Se utilizará un modelo dimensional tipo estrella.

La tabla central será:

- `fact_financiamiento`

Las dimensiones serán:

- `dim_fecha`
- `dim_territorio`
- `dim_organismo`
- `dim_destino`
- `dim_sexo`

Esquema conceptual:

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
