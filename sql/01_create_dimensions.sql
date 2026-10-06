-- =========================================================
-- DIMENSIONES DEL DATA WAREHOUSE
-- Housing Data Pipeline
-- =========================================================


-- =========================================================
-- DIM_FECHA
-- =========================================================

CREATE TABLE IF NOT EXISTS dim_fecha (
    fecha_key INTEGER PRIMARY KEY,
    anio SMALLINT NOT NULL,
    mes_numero SMALLINT NOT NULL,
    mes_nombre VARCHAR(20) NOT NULL,

    CONSTRAINT chk_dim_fecha_mes
        CHECK (mes_numero BETWEEN 1 AND 12)
);


-- =========================================================
-- DIM_TERRITORIO
-- =========================================================

CREATE TABLE IF NOT EXISTS dim_territorio (
    territorio_key INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    clave_estado VARCHAR(2) NOT NULL,
    estado VARCHAR(100) NOT NULL,
    clave_municipio VARCHAR(3) NOT NULL,
    municipio VARCHAR(150) NOT NULL,

    CONSTRAINT uq_dim_territorio_codigo
        UNIQUE (clave_estado, clave_municipio)
);


-- =========================================================
-- DIM_ORGANISMO
-- =========================================================

CREATE TABLE IF NOT EXISTS dim_organismo (
    organismo_key INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    organismo VARCHAR(150) NOT NULL,

    CONSTRAINT uq_dim_organismo_nombre
        UNIQUE (organismo)
);


-- =========================================================
-- DIM_DESTINO
-- =========================================================

CREATE TABLE IF NOT EXISTS dim_destino (
    destino_key INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    destino_credito VARCHAR(150) NOT NULL,

    CONSTRAINT uq_dim_destino_nombre
        UNIQUE (destino_credito)
);


-- =========================================================
-- DIM_SEXO
-- =========================================================

CREATE TABLE IF NOT EXISTS dim_sexo (
    sexo_key SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sexo VARCHAR(30) NOT NULL,

    CONSTRAINT uq_dim_sexo_nombre
        UNIQUE (sexo)
);
