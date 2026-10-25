# transform_inversion.py
# Transform: fechas a datetime, limpieza del avance, tratamiento de nulos,
# cartera 2016-2021 de PIURA y agregado anual departamental.

import logging

import numpy as np
import pandas as pd

from extract_inversion import DEPARTAMENTO, normalizar_texto

log = logging.getLogger(__name__)

ANIO_INI, ANIO_FIN = 2016, 2021
FECHA_MIN, FECHA_MAX = pd.Timestamp("1990-01-01"), pd.Timestamp("2040-12-31")
ESTADOS_CERRADOS = "CERRAD|CULMINAD|LIQUIDAD|DESACTIV"


# ---------------------------------------------------------------- utilidades
def a_numero(s):
    """Texto a número: quita símbolos y separadores de miles."""
    s = s.astype("string").str.strip().str.replace(r"[^\d,.\-]", "", regex=True)
    tiene_punto = s.str.contains(".", regex=False, na=False)
    s = s.where(~tiene_punto, s.str.replace(",", "", regex=False))  # 1,500.00
    s = s.where(tiene_punto, s.str.replace(",", ".", regex=False))  # 80,5
    return pd.to_numeric(s, errors="coerce").astype("float64")


def a_fecha(s):
    """
    Convierte a datetime aceptando los formatos que aparecen en el MEF:
    AAAAMMDD, AAAAMM (periodos del SIAF), aaaa-mm-dd y dd/mm/aaaa.
    Las fechas fuera de 1990-2040 se consideran errores y pasan a NaT.
    """
    s = s.astype("string").str.strip().str.slice(0, 19)
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")

    m8 = s.str.fullmatch(r"\d{8}", na=False)          # 20190315
    out[m8] = pd.to_datetime(s[m8], format="%Y%m%d", errors="coerce")

    m6 = s.str.fullmatch(r"\d{6}", na=False)          # 201903 (periodo)
    out[m6] = pd.to_datetime(s[m6], format="%Y%m", errors="coerce")

    iso = s.str.match(r"\d{4}-\d{2}(-\d{2})?", na=False)  # 2019-03-15 / 2019-03
    out[iso] = pd.to_datetime(s[iso].str.slice(0, 10), format="mixed",
                              errors="coerce")

    resto = ~m8 & ~m6 & ~iso & s.notna()               # 15/03/2019
    out[resto] = pd.to_datetime(s[resto], dayfirst=True, format="mixed",
                                errors="coerce")

    fuera = (out < FECHA_MIN) | (out > FECHA_MAX)
    if fuera.any():
        log.warning("%d fechas fuera de rango -> NaT", int(fuera.sum()))
    return out.mask(fuera)


def a_porcentaje(s):
    """Lleva el avance a escala 0-100 (si viniera en 0-1, lo multiplica por 100)."""
    x = a_numero(s)
    validos = x.dropna()
    if len(validos) and validos.quantile(0.95) <= 1.0:
        x = x * 100
    return x


# ------------------------------------------------------------- base detallada
def renombrar(df):
    """Nombres homogéneos en minúscula."""
    return df.rename(columns={
        "CODIGO_UNICO": "cui", "NOMBRE_INVERSION": "nombre",
        "NOMBRE_UEI": "ejecutora", "NIVEL": "nivel_gobierno",
        "SECTOR": "sector", "FUNCION": "funcion", "ESTADO": "estado",
        "SITUACION": "situacion", "DEPARTAMENTO": "departamento",
        "COSTO_ACTUALIZADO": "costo", "MONTO_VIABLE": "monto_viable",
        "AVANCE_FISICO": "avance_fisico", "AVANCE_EJECUCION": "avance_financiero",
    })


def limpiar_detalle(df):
    df = renombrar(df.copy())

    # Identificador y categóricas
    df["cui"] = a_numero(df["cui"]).astype("Int64")
    for c in ["departamento", "ejecutora", "nivel_gobierno", "sector",
              "funcion", "estado", "situacion"]:
        if c in df:
            df[c] = df[c].map(normalizar_texto, na_action="ignore")
    df = df.dropna(subset=["cui"]).drop_duplicates(subset="cui", keep="last")

    # Fechas: se toma la fuente principal y, si falta, la de respaldo
    fechas = {c: a_fecha(df[c]) for c in df.columns
              if c.startswith(("FEC_", "PRIMER_", "ULTIMO_", "ULT_"))}
    vacia = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
    f = lambda c: fechas.get(c, vacia)
    df["fecha_inicio"] = (f("FEC_INI_EJECUCION")
                          .fillna(f("FEC_INI_EJEC_FISICA"))
                          .fillna(f("PRIMER_DEVENGADO")))
    df["fecha_fin"] = f("FEC_FIN_EJECUCION").fillna(f("FEC_FIN_EJEC_FISICA"))
    df["fecha_ult_ejec"] = f("ULTIMO_DEVENGADO").fillna(f("ULT_FEC_DECLA_ESTIM"))

    # Montos
    for c in ["costo", "monto_viable", "DEVEN_ACUMUL_ANIO_ANT", "DEV_ANIO_ACTUAL"]:
        df[c] = a_numero(df[c]) if c in df else np.nan
    df["devengado_acum"] = df[["DEVEN_ACUMUL_ANIO_ANT", "DEV_ANIO_ACTUAL"]].sum(
        axis=1, min_count=1)
    # Costo nulo o <= 0 -> se usa el monto viable
    sin_costo = df["costo"].isna() | (df["costo"] <= 0)
    df.loc[sin_costo, "costo"] = df.loc[sin_costo, "monto_viable"]
    df["costo"] = df["costo"].where(df["costo"] > 0)

    # Avance financiero: el reportado o, si falta, devengado acumulado / costo
    df["avance_financiero"] = a_porcentaje(df["avance_financiero"]).fillna(
        100 * df["devengado_acum"] / df["costo"])
    df["avance_fisico"] = a_porcentaje(df["avance_fisico"])

    # Avance final: físico si existe; si no, financiero
    df["avance"] = df["avance_fisico"]
    df["fuente_avance"] = np.where(df["avance"].notna(), "fisico", None)
    usa_fin = df["avance"].isna() & df["avance_financiero"].notna()
    df.loc[usa_fin, "avance"] = df.loc[usa_fin, "avance_financiero"]
    df.loc[usa_fin, "fuente_avance"] = "financiero"

    # Nulos restantes: cerradas -> 100 ; sin ninguna ejecución -> 0
    cerrada = df["estado"].fillna("").str.contains(ESTADOS_CERRADOS)
    imp_100 = df["avance"].isna() & cerrada
    df.loc[imp_100, ["avance", "fuente_avance"]] = [100.0, "imputado_cerrada"]
    sin_ejec = (df["avance"].isna() & df["fecha_ult_ejec"].isna()
                & (df["devengado_acum"].fillna(0) <= 0))
    df.loc[sin_ejec, ["avance", "fuente_avance"]] = [0.0, "imputado_sin_ejecucion"]
    df["fuente_avance"] = df["fuente_avance"].fillna("sin_dato")

    # Atípicos: avances > 100 % (sobrecostos) se recortan y se marcan
    df["avance_excede_100"] = df["avance"] > 100
    df["avance"] = df["avance"].clip(lower=0, upper=100)

    print("   Fuente del avance:", df["fuente_avance"].value_counts().to_dict())
    return df


def periodo_ejecucion(df):
    """Inicio y fin efectivos para saber en qué años está activa cada inversión."""
    df = df.copy()
    df["inicio_efectivo"] = df["fecha_inicio"].fillna(df["fecha_ult_ejec"])
    df["fin_efectivo"] = df[["fecha_fin", "fecha_ult_ejec"]].max(axis=1)
    # Sin fecha de fin y no cerrada -> sigue en ejecución a la fecha de corte
    abierta = (df["fin_efectivo"].isna()
               & ~df["estado"].fillna("").str.contains(ESTADOS_CERRADOS))
    df.loc[abierta, "fin_efectivo"] = pd.Timestamp.today().normalize()
    return df


def filtrar_cartera(df):
    """Cartera 2016-2021: inversiones cuyo periodo de ejecución toca esos años."""
    ini, fin = pd.Timestamp(f"{ANIO_INI}-01-01"), pd.Timestamp(f"{ANIO_FIN}-12-31")
    m = (df["inicio_efectivo"] <= fin) & (df["fin_efectivo"] >= ini)
    print(f"   Cartera {ANIO_INI}-{ANIO_FIN}: {int(m.sum())} de {len(df)} inversiones"
          f" ({int(df['inicio_efectivo'].isna().sum())} sin fecha de inicio)")
    return df[m].reset_index(drop=True)


def transform_detalle(df_raw):
    df = filtrar_cartera(periodo_ejecucion(limpiar_detalle(df_raw)))
    columnas = ["cui", "nombre", "departamento", "ejecutora", "nivel_gobierno",
                "sector", "funcion", "estado", "situacion", "costo",
                "devengado_acum", "avance_fisico", "avance_financiero", "avance",
                "fuente_avance", "avance_excede_100", "fecha_inicio", "fecha_fin",
                "fecha_ult_ejec", "inicio_efectivo", "fin_efectivo"]
    return df[[c for c in columnas if c in df]]


# ------------------------------------------------------------ agregado anual
def transform_agregado(det):
    """Piura-año: n° de proyectos activos, costo total y avance ponderado."""
    filas = []
    for anio in range(ANIO_INI, ANIO_FIN + 1):
        ini, fin = pd.Timestamp(f"{anio}-01-01"), pd.Timestamp(f"{anio}-12-31")
        activos = det[(det["inicio_efectivo"] <= fin) & (det["fin_efectivo"] >= ini)]
        pond = activos.dropna(subset=["avance", "costo"])
        avance_pond = (np.average(pond["avance"], weights=pond["costo"])
                       if pond["costo"].sum() > 0 else np.nan)
        filas.append({
            "departamento": DEPARTAMENTO,
            "anio": anio,
            "n_proyectos_activos": len(activos),
            "costo_total_mill": activos["costo"].sum() / 1e6,
            "avance_ponderado_pct": avance_pond,
        })
    agg = pd.DataFrame(filas)
    agg["anio"] = agg["anio"].astype("int64")
    assert agg["avance_ponderado_pct"].dropna().between(0, 100).all()
    return agg


def a_long(agg):
    """Formato long: departamento, año, indicador, valor."""
    return agg.melt(id_vars=["departamento", "anio"],
                    var_name="indicador", value_name="valor")
