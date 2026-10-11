"""Rutas del repositorio, archivos de datos y sistemas de coordenadas.

Las rutas se calculan desde la ubicación de este archivo, así que los cuadernos funcionan sin importar la carpeta
desde la que se abran.
"""

from pathlib import Path

# ------------------------------------------------------------------------------------------ carpetas
RAIZ = Path(__file__).resolve().parents[1]
DATOS = RAIZ / 'datos'
FIGURAS = RAIZ / 'figuras'
MANIFIESTO = DATOS / 'manifiesto.csv'

# ------------------------------------------------------------------------------------------ coordenadas
CRS_GEO = 'EPSG:4326'               # WGS 84 geográficas (así llegan casi todas las fuentes)
CRS_UTM = 'EPSG:32718'              # WGS 84 / UTM 18S (sistema de trabajo: distancias en metros)

# ------------------------------------------------------------------------------------------ archivos
ARCHIVOS = {
    # Área de estudio y contexto
    'aoi': DATOS / 'area_estudio' / 'AOI.shp',
    'departamentos': DATOS / 'contexto' / 'departamentos.shp',
    'provincias': DATOS / 'contexto' / 'provincias.shp',
    'capitales': DATOS / 'contexto' / 'capitales.shp',
    # Gravedad: dos fuentes de la misma variable (anomalía de Bouguer)
    'gravedad_estaciones': DATOS / 'gravedad' / 'gravimetria_estaciones.shp',
    'gravedad_xgm2019e': DATOS / 'gravedad' / 'gravedad_XGM2019e_bouguer.tif',
    # Uranio en roca: cinco fuentes
    'litogeoquimica': DATOS / 'geoquimica' / 'litogeoquimica_roca.shp',
    'bdg_2022': DATOS / 'geoquimica' / 'rocas_BDG_2022.shp',
    'ge27': DATOS / 'geoquimica' / 'materia_critica_U.shp',
    'ipen': DATOS / 'geoquimica' / 'ipen_san_ramon.shp',
    'b74': DATOS / 'geoquimica' / 'carpio2021_B74.shp',
    # Otras variables
    'sedimentos': DATOS / 'geoquimica' / 'sedimentos_quebrada.shp',
    'dem_90m': DATOS / 'elevacion' / 'dem_copernicus_90m.tif',
}
