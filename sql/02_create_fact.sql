-- =========================================================
-- TABLA DE HECHOS
-- Housing Data Pipeline
-- =========================================================

CREATE TABLE IF NOT EXISTS fact_financiamiento (
    financiamiento_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    fecha_key INTEGER NOT NULL,
    territorio_key INTEGER NOT NULL,
    organismo_key INTEGER NOT NULL,
    destino_key INTEGER NOT NULL,
    sexo_key SMALLINT NOT NULL,

    acciones BIGINT NOT NULL,
    monto NUMERIC(30, 12) NOT NULL,

    -- =====================================================
    -- FOREIGN KEYS
    -- =====================================================

    CONSTRAINT fk_fact_fecha
        FOREIGN KEY (fecha_key)
        REFERENCES dim_fecha (fecha_key),

    CONSTRAINT fk_fact_territorio
        FOREIGN KEY (territorio_key)
        REFERENCES dim_territorio (territorio_key),

    CONSTRAINT fk_fact_organismo
        FOREIGN KEY (organismo_key)
        REFERENCES dim_organismo (organismo_key),

    CONSTRAINT fk_fact_destino
        FOREIGN KEY (destino_key)
        REFERENCES dim_destino (destino_key),

    CONSTRAINT fk_fact_sexo
        FOREIGN KEY (sexo_key)
        REFERENCES dim_sexo (sexo_key),

    -- =====================================================
    -- REGLAS DE CALIDAD
    -- =====================================================

    CONSTRAINT chk_fact_acciones
        CHECK (acciones >= 0),

    CONSTRAINT chk_fact_monto
        CHECK (monto >= 0),

    -- =====================================================
    -- PROTECCIÓN DEL GRANO
    -- =====================================================

    CONSTRAINT uq_fact_grain
        UNIQUE (
            fecha_key,
            territorio_key,
            organismo_key,
            destino_key,
            sexo_key
        )
);
