# load_inversion.py
# Load: guarda la base detallada y el agregado anual en formato Parquet.

from pathlib import Path


def load_inversion(df, nombre, carpeta):
    '''
    Guarda un DataFrame como <carpeta>/<nombre>.parquet

    df      : DataFrame transformado
    nombre  : nombre del archivo sin extensión
    carpeta : carpeta de salida (ruta relativa al proyecto)
    '''
    ruta = Path(carpeta)
    ruta.mkdir(parents=True, exist_ok=True)   # la crea si no existe

    archivo = ruta / f"{nombre}.parquet"
    df.to_parquet(archivo, index=False)

    print("   Archivo guardado en:", archivo.resolve())
    return archivo
