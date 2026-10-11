"""Acceso a los datos: servicios REST de GEOCATMIN (INGEMMET) y verificación de los archivos con su huella sha256.

GEOCATMIN publica cada capa como un servicio ArcGIS REST (`.../MapServer/<capa>/query`). El servicio no admite
paginación, así que la descarga se hace en dos pasos: primero se piden solo los identificadores (OBJECTID) de las
entidades dentro de una caja y luego se descargan en bloques con `objectIds`.
"""

import hashlib
import io
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import geopandas as gpd
import pandas as pd

from .rutas import CRS_GEO, MANIFIESTO, RAIZ

GEOCATMIN = 'https://geocatmin.ingemmet.gob.pe/arcgis/rest/services/'

# Servicio y número de capa de cada fuente descargada de GEOCATMIN
CAPAS_GEOCATMIN = {
    'gravedad_estaciones': 'SERV_GEOFISICA/MapServer/4',
    'sedimentos': 'SERV_GEOQUIMICA/MapServer/1',
    'bdg_2022': 'SERV_GEOQUIMICA_2022/MapServer/10',
}


# ------------------------------------------------------------------------------------------ GEOCATMIN
def consultar(servicio_capa, parametros, tiempo_max=120):
    """Hace una consulta POST a una capa de GEOCATMIN y devuelve la respuesta JSON como diccionario."""
    url = GEOCATMIN + servicio_capa + '/query'
    pedido = Request(url, data=urlencode(parametros).encode(), headers={'User-Agent': 'Mozilla/5.0'})
    with urlopen(pedido, timeout=tiempo_max) as respuesta:
        return json.load(respuesta)


def _filtro_caja(caja):
    """Filtro espacial para una caja (lon_min, lat_min, lon_max, lat_max) en grados WGS 84."""
    return dict(where='1=1', geometry=','.join(map(str, caja)), geometryType='esriGeometryEnvelope',
                inSR=4326, spatialRel='esriSpatialRelIntersects')


def contar_entidades(servicio_capa, caja):
    """Cuántas entidades de la capa caen dentro de la caja (sin descargarlas)."""
    return consultar(servicio_capa, {**_filtro_caja(caja), 'returnCountOnly': 'true', 'f': 'json'})['count']


def descargar_capa(servicio_capa, caja, bloque=500):
    """Descarga todas las entidades de la capa dentro de la caja, en bloques de `bloque` identificadores."""
    ids = consultar(servicio_capa, {**_filtro_caja(caja), 'returnIdsOnly': 'true', 'f': 'json'})['objectIds']
    ids = sorted(ids or [])
    if not ids:
        return gpd.GeoDataFrame(geometry=[], crs=CRS_GEO)
    partes = []
    for i in range(0, len(ids), bloque):
        parametros = dict(objectIds=','.join(map(str, ids[i:i + bloque])), outFields='*', outSR=4326,
                          returnGeometry='true', f='geojson')
        pedido = Request(GEOCATMIN + servicio_capa + '/query', data=urlencode(parametros).encode(),
                         headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(pedido, timeout=300) as respuesta:
            partes.append(gpd.read_file(io.BytesIO(respuesta.read())))
    capa = gpd.GeoDataFrame(pd.concat(partes, ignore_index=True), crs=CRS_GEO)
    if len(capa) != len(ids):
        raise RuntimeError(f'{servicio_capa}: descarga incompleta ({len(capa)} de {len(ids)} entidades)')
    return capa


# ------------------------------------------------------------------------------------------ integridad
def sha256(ruta):
    """Huella sha256 de un archivo (cambia si cambia un solo byte)."""
    h = hashlib.sha256()
    with Path(ruta).open('rb') as f:
        for bloque in iter(lambda: f.read(1 << 20), b''):
            h.update(bloque)
    return h.hexdigest()


def verificar_manifiesto(manifiesto=MANIFIESTO):
    """Compara la huella de cada archivo de `datos/` con la registrada en el manifiesto.

    Devuelve el manifiesto con dos columnas nuevas: `existe` y `huella_ok`.
    """
    tabla = pd.read_csv(manifiesto)
    rutas = tabla['archivo'].map(lambda a: RAIZ / a)
    tabla['existe'] = rutas.map(Path.exists)
    tabla['huella_ok'] = [e and sha256(r) == h for r, e, h in zip(rutas, tabla['existe'], tabla['sha256'])]
    return tabla
