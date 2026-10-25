# main_inversion.py
# Controla el flujo del ETL de la cartera de inversión pública de PIURA:
# 1) extracción  2) transformación  3) carga.

from pathlib import Path

from extract_inversion import extract_inversion
from transform_inversion import a_long, transform_agregado, transform_detalle
from load_inversion import load_inversion

# Ruta relativa: carpeta donde está este archivo (funciona en cualquier computadora)
CARPETA_PROYECTO = Path(__file__).resolve().parent
CARPETA_SALIDA = CARPETA_PROYECTO / "output"


def main():
    print("1) Extrayendo Detalle de inversiones de PIURA (Datos Abiertos MEF)...")
    df_raw = extract_inversion()

    print("2) Transformando...")
    detalle = transform_detalle(df_raw)
    agregado = transform_agregado(detalle)
    print(agregado.to_string(index=False))

    print("3) Guardando en Parquet...")
    load_inversion(detalle, "inversion_detalle", CARPETA_SALIDA)
    load_inversion(agregado, "inversion_agregado", CARPETA_SALIDA)
    load_inversion(a_long(agregado), "inversion_agregado_long", CARPETA_SALIDA)

    print("Proceso terminado.")


if __name__ == "__main__":
    main()
