
WITH calendario AS (
    SELECT
        anio,
        mes_numero,
        mes_nombre
    FROM dim_fecha
    WHERE anio IN (2024, 2025)
),
resumen_mensual AS (
    SELECT
        d.anio,
        d.mes_numero,
        SUM(f.acciones) AS total_acciones,
        SUM(f.monto) AS total_monto
    FROM fact_financiamiento f
    JOIN dim_fecha d
        ON f.fecha_key = d.fecha_key
    JOIN dim_territorio t
        ON f.territorio_key = t.territorio_key
    JOIN dim_organismo o
        ON f.organismo_key = o.organismo_key
    JOIN dim_destino dc
        ON f.destino_key = dc.destino_key
    WHERE t.estado = 'México'
      AND o.organismo = 'CONAVI'
      AND dc.destino_credito = 'Mejoramientos'
      AND d.anio IN (2024, 2025)
    GROUP BY
        d.anio,
        d.mes_numero
)
SELECT
    c.mes_numero,
    c.mes_nombre,
    MAX(r.total_acciones)
        FILTER (WHERE c.anio = 2024) AS acciones_2024,
    MAX(r.total_acciones)
        FILTER (WHERE c.anio = 2025) AS acciones_2025,
    MAX(r.total_monto)
        FILTER (WHERE c.anio = 2024) AS monto_2024,
    MAX(r.total_monto)
        FILTER (WHERE c.anio = 2025) AS monto_2025
FROM calendario c
LEFT JOIN resumen_mensual r
    ON r.anio = c.anio
   AND r.mes_numero = c.mes_numero
GROUP BY
    c.mes_numero,
    c.mes_nombre
ORDER BY
    c.mes_numero;
