-- ¿Cómo se distribuyen las acciones y el monto de financiamiento entre los estados de México a lo largo del tiempo?
-- Ranking territorial anual de financiamiento SNIIV.
-- 2026 contiene únicamente datos de enero a junio.

SELECT
    d.anio,
    t.estado,
    SUM(f.acciones) AS total_acciones,
    SUM(f.monto) AS total_monto,
    ROUND(
        SUM(f.monto) / NULLIF(SUM(f.acciones), 0),
        2
    ) AS monto_por_accion
FROM fact_financiamiento f
JOIN dim_fecha d
    ON f.fecha_key = d.fecha_key
JOIN dim_territorio t
    ON f.territorio_key = t.territorio_key
GROUP BY
    d.anio,
    t.estado
ORDER BY
    d.anio,
    total_acciones DESC;
