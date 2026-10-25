# ETL de la cartera de inversión pública – Piura (2016–2021)

Proceso ETL en Python que descarga automáticamente la cartera de inversión pública del
**Portal de Datos Abiertos del MEF**, filtra los proyectos del departamento de **Piura**,
limpia la información y construye un **agregado anual** con el número de proyectos activos,
el costo total de la cartera y el avance ponderado por costo.

> Proyecto desarrollado para el curso *Laboratorio de Programación: R y Python* (PUCP).

---

## Cómo ejecutarlo

### 1. Requisitos
- **Python 3.9 o superior** (sirve Anaconda).
- Conexión a internet: el script descarga el archivo del MEF (~250 MB).

### 2. Descargar el proyecto
Botón verde **Code → Download ZIP** y descomprimirlo, o con git:
```bash
git clone https://github.com/diegote44byte/NOMBRE-DEL-REPOSITORIO.git
cd NOMBRE-DEL-REPOSITORIO
```

### 3. Instalar las librerías (solo la primera vez)
```bash
pip install -r requirements.txt
```

### 4. Ejecutar
```bash
python main_inversion.py
```
En Windows también se puede dar doble clic a `ejecutar.bat` (una vez instaladas las librerías).

La descarga tarda unos minutos. Al terminar se muestra la tabla anual en pantalla y se crea
la carpeta `output/` con los resultados.

---

## Resultados

| Archivo | Contenido |
|---|---|
| `output/inversion_detalle.parquet` | Cartera detallada: un proyecto por fila (CUI, ejecutora, nivel de gobierno, sector, función, costo, avance y fechas) |
| `output/inversion_agregado.parquet` | Agregado anual de Piura (formato ancho) |
| `output/inversion_agregado_long.parquet` | El mismo agregado en formato long |

Los archivos `.parquet` se leen con pandas:
```python
import pandas as pd
pd.read_parquet("output/inversion_agregado.parquet")
```

Resultado obtenido (datos del MEF actualizados al 13/10/2026):

| Año | Proyectos activos | Costo total (S/ millones) | Avance ponderado (%) |
|---|---:|---:|---:|
| 2016 | 344 | 4 718.5 | 69.5 |
| 2017 | 403 | 6 518.1 | 63.4 |
| 2018 | 651 | 9 152.1 | 61.1 |
| 2019 | 987 | 15 791.4 | 54.3 |
| 2020 | 1 382 | 19 939.6 | 58.2 |
| 2021 | 1 793 | 26 737.9 | 57.5 |

Como la fuente se actualiza periódicamente, al ejecutarlo en otra fecha las cifras pueden variar.

---

## Estructura

```
├── main_inversion.py        # Orquesta el proceso: extract → transform → load
├── extract_inversion.py     # Descarga el CSV del MEF y filtra Piura
├── transform_inversion.py   # Fechas, avance, nulos, cartera 2016-2021 y agregado anual
├── load_inversion.py        # Guarda los resultados en Parquet
├── requirements.txt         # Librerías necesarias
├── ejecutar.bat             # Ejecución con doble clic (Windows)
├── Informe_tecnico_modulo_5.pdf   # Informe con las decisiones metodológicas
└── error404.png             # Captura del error 404 del portal del MEF (citada en el informe)
```

---

## Metodología (resumen)

- **Fuente:** dataset *Detalle de inversiones* del [Portal de Datos Abiertos del MEF](https://datosabiertos.mef.gob.pe/dataset/detalle-de-inversiones).
- **Extract:** descarga directa del CSV en memoria, lectura por bloques de 50 000 filas y filtro de Piura (verificado con el UBIGEO `20`). Reintentos automáticos si el servidor falla.
- **Transform:**
  - fechas convertidas a `datetime` (el archivo mezcla formatos `aaaa-mm-dd` y `AAAAMM`);
  - avance: se usa el físico y, si falta, el financiero; los avances mayores a 100 % se recortan y se marcan;
  - un proyecto está **activo en un año** si su periodo de ejecución se superpone con ese año;
  - avance ponderado: `Σ(costo × avance) / Σ costo` de los proyectos activos.
- **Load:** resultados en formato Parquet.

El detalle completo está en `Informe_tecnico_modulo_5.pdf`.

## Limitaciones
- El archivo del MEF solo contiene inversiones en estado **activo**; las cerradas se publican en otro dataset. Por eso la cartera de los primeros años está subestimada.
- El avance corresponde a la fecha de actualización del archivo, no al cierre de cada año.

## Cambiar de departamento
En `extract_inversion.py` modificar:
```python
DEPARTAMENTO = "PIURA"
UBIGEO_DEP = "20"
```
