# extract_inversion.py
# Extract: descarga la base "Detalle de inversiones" del Portal de Datos Abiertos
# del MEF y conserva solo las inversiones del departamento de PIURA.
#
# Página del dataset : https://datosabiertos.mef.gob.pe/dataset/detalle-de-inversiones
# Recurso principal  : DETALLE_INVERSIONES.csv  (~235 MB, todo el país)
# Diccionario        : Detalle_Inversiones_Diccionario.csv
#
# Método: descarga directa del CSV (método 1 del cuaderno de semana 5). La API
# datastore_search devuelve "records": null para este recurso, por eso no se usa.

import logging
import time
import unicodedata
from io import BytesIO

import pandas as pd
import requests

log = logging.getLogger(__name__)

URL_CSV = "https://fs.datosabiertos.mef.gob.pe/datastorefiles/DETALLE_INVERSIONES.csv"
HEADERS = {"User-Agent": "Mozilla/5.0 (curso universitario; uso educativo)"}

# Departamento asignado al grupo y su código UBIGEO (INEI: Piura = 20)
DEPARTAMENTO = "PIURA"
UBIGEO_DEP = "20"

# Columnas que se conservan (nombres tal como figuran en el diccionario del MEF)
COLUMNAS = [
    "CODIGO_UNICO",          # CUI
    "NOMBRE_INVERSION",
    "NOMBRE_UEI",            # Unidad Ejecutora de Inversiones (ejecutora)
    "NIVEL",                 # nivel de gobierno (GN, GR, GL)
    "SECTOR",
    "FUNCION",
    "ESTADO",
    "SITUACION",
    "DEPARTAMENTO",
    "UBIGEO",                # para verificar que la localización es Piura
    "COSTO_ACTUALIZADO",     # costo del proyecto
    "MONTO_VIABLE",          # respaldo si el costo actualizado falta
    "DEVEN_ACUMUL_ANIO_ANT", # devengado acumulado hasta el año anterior
    "DEV_ANIO_ACTUAL",       # devengado del año actual
    "AVANCE_FISICO",         # % avance físico
    "AVANCE_EJECUCION",      # % avance de ejecución (financiero)
    "FEC_INI_EJECUCION",     # fecha de inicio (Formato 08)
    "FEC_FIN_EJECUCION",     # fecha de fin (Formato 08)
    "FEC_INI_EJEC_FISICA",   # respaldo de inicio (Formato 12-B)
    "FEC_FIN_EJEC_FISICA",   # respaldo de fin (Formato 12-B)
    "PRIMER_DEVENGADO",      # periodo del primer devengado (SIAF)
    "ULTIMO_DEVENGADO",      # periodo del último devengado = fecha de última ejecución
    "ULT_FEC_DECLA_ESTIM",   # respaldo: última declaración de avance físico
]


def normalizar_texto(x):
    """Mayúsculas y sin tildes, para comparar nombres de departamentos."""
    x = unicodedata.normalize("NFKD", str(x)).encode("ascii", "ignore").decode()
    return " ".join(x.split()).upper()


def descargar_csv(url=URL_CSV, intentos=3, espera=10):
    """
    Descarga el CSV completo a memoria (sin guardarlo en disco).
    Reintenta si el servidor del MEF falla o corta la descarga.
    """
    for intento in range(1, intentos + 1):
        print(f"Descargando (intento {intento}/{intentos})", url, "...")
        try:
            respuesta = requests.get(url, headers=HEADERS, timeout=600)
            if respuesta.status_code == 404:
                # El archivo no existe en el servidor: reintentar no sirve
                raise RuntimeError(
                    "El servidor del MEF respondió 404 (archivo no encontrado) "
                    f"para {url}. Revise la página del dataset por si cambió el "
                    "enlace, o intente más tarde.")
            respuesta.raise_for_status()  # otros errores HTTP (500, 503...)
            print(f"   Descargados {len(respuesta.content) / 1e6:.1f} MB")
            return respuesta.content
        except requests.RequestException as e:
            print(f"   Falló la descarga: {e}")
            if intento < intentos:
                time.sleep(espera)
    raise RuntimeError(f"No se pudo descargar {url} tras {intentos} intentos")


def detectar_encoding(contenido):
    """Prueba utf-8 y, si falla, latin-1 (habitual en archivos del MEF)."""
    muestra = contenido[:2_000_000]
    try:
        muestra.decode("utf-8-sig")
        return "utf-8-sig"
    except UnicodeDecodeError as e:
        # Si el error está al final, solo se cortó una letra con tilde: es UTF-8
        if e.start >= len(muestra) - 3:
            return "utf-8-sig"
        return "latin-1"


def extract_inversion(url=URL_CSV, chunksize=50_000):
    """
    Devuelve un DataFrame con las inversiones localizadas en PIURA.

    url       : URL directa del CSV de Detalle de inversiones
    chunksize : filas por bloque (el archivo nacional es muy pesado)
    """
    contenido = descargar_csv(url)
    encoding = detectar_encoding(contenido)

    # Revisa que las columnas esperadas existan (el MEF puede cambiarlas)
    cabecera = pd.read_csv(BytesIO(contenido), encoding=encoding, nrows=0).columns
    faltantes = [c for c in COLUMNAS if c not in cabecera]
    if faltantes:
        log.warning("Columnas no encontradas en el CSV: %s", faltantes)
    usar = [c for c in COLUMNAS if c in cabecera]

    # Lee por bloques y se queda solo con las inversiones de Piura
    lista_df = []
    for bloque in pd.read_csv(BytesIO(contenido), encoding=encoding, usecols=usar,
                              dtype=str, chunksize=chunksize, low_memory=False):
        dep = bloque["DEPARTAMENTO"].map(normalizar_texto, na_action="ignore")
        lista_df.append(bloque[dep == DEPARTAMENTO])

    df = pd.concat(lista_df, ignore_index=True)
    print(f"   Inversiones de {DEPARTAMENTO}: {len(df)}")
    if df.empty:
        raise ValueError("No se encontraron inversiones de PIURA en el CSV")

    # Verificación cruzada: el UBIGEO de Piura empieza con "20"
    if "UBIGEO" in df:
        ubigeo = df["UBIGEO"].astype("string").str.strip().str.zfill(6)
        fuera = ubigeo.notna() & ~ubigeo.str.startswith(UBIGEO_DEP)
        if fuera.any():
            log.warning("%d inversiones con DEPARTAMENTO=PIURA pero UBIGEO que no"
                        " empieza con %s", int(fuera.sum()), UBIGEO_DEP)
    return df
