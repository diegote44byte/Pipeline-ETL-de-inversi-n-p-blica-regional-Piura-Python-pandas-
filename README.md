# Pipeline-ETL-de-inversi-n-p-blica-regional-Piura-Python-pandas-


Proyecto del curso Laboratorio de Programación: R y Python (PUCP)

Desarrollé un proceso ETL modular (extract / transform / load) que descarga automáticamente la cartera de inversión pública del Portal de Datos Abiertos del MEF (archivo de 247 MB, más de 150 000 proyectos a nivel nacional).
Procesé el archivo por bloques en memoria y filtré los 2 230 proyectos de Piura activos entre 2016 y 2021, con validaciones de columnas, codificación y ubicación (UBIGEO).
Estandaricé fechas de formatos mixtos, traté valores nulos y atípicos con criterios documentados y construí indicadores anuales: proyectos activos, costo total (S/ 26 700 millones en 2021) y avance ponderado por costo.
Implementé manejo de errores y reintentos ante caídas del servidor de la fuente, y documenté las decisiones metodológicas en un informe técnico.
