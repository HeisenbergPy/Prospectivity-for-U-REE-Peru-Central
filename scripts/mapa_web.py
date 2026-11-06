"""Mapa interactivo de los resultados de GC04 para GitHub Pages (carpeta docs/).

Lee los GeoTIFF que genera GC04 en `resultados/`, los reproyecta a Web Mercator (EPSG:3857, la proyección de los
mapas web), los colorea como en el cuaderno y los guarda como PNG transparentes en `docs/capas/`. Escribe también las
rocas positivas y los límites en GeoJSON y la página `docs/index.html` (Leaflet).

Uso, desde la carpeta del repositorio y después de ejecutar GC04:
    uv run python scripts/mapa_web.py
"""

import json
import shutil

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.colors import to_hex, to_rgb
from PIL import Image
from rasterio.warp import Resampling, calculate_default_transform, reproject, transform_bounds

import cmcrameri  # noqa: F401  (registra 'cmc.batlow')
from geocomp import lectura, modelo
from geocomp.rutas import ARCHIVOS, RAIZ, RESULTADOS

DOCS = RAIZ / 'docs'
CAPAS = DOCS / 'capas'
WEB = 'EPSG:3857'

COLOR_CLASE = {3: '#d62828', 2: '#f4a261', 1: '#ffe8a3'}
COLOR_CRUCE = {4: '#79326e', 3: '#bd5888', 2: '#f7aa5f', 1: '#a79acd'}


def a_web(ruta, categorico):
    """Matriz reproyectada a EPSG:3857 y sus límites en grados (sur, oeste, norte, este) para Leaflet."""
    with rasterio.open(ruta) as src:
        transform, ancho, alto = calculate_default_transform(src.crs, WEB, src.width, src.height, *src.bounds)
        destino = np.full((alto, ancho), np.nan, dtype='float32')
        reproject(rasterio.band(src, 1), destino, src_nodata=np.nan, dst_nodata=np.nan, dst_transform=transform,
                  dst_crs=WEB, resampling=Resampling.nearest if categorico else Resampling.bilinear)
    oeste, sur, este, norte = transform_bounds(WEB, 'EPSG:4326', transform.c, transform.f + alto * transform.e,
                                               transform.c + ancho * transform.a, transform.f)
    return destino, [[sur, oeste], [norte, este]]


def png_continuo(matriz, nombre, cmap='cmc.batlow', opacidad=1.0):
    rgba = plt.get_cmap(cmap)(np.clip(np.nan_to_num(matriz) / 100, 0, 1))
    rgba[..., 3] = np.where(np.isfinite(matriz), opacidad, 0)
    Image.fromarray((rgba * 255).astype('uint8')).save(CAPAS / nombre, optimize=True)


def png_categorico(matriz, colores, nombre, opacidad=1.0):
    rgba = np.zeros(matriz.shape + (4,))
    for k, c in colores.items():
        rgba[matriz == k] = [*to_rgb(c), opacidad]
    Image.fromarray((rgba * 255).astype('uint8')).save(CAPAS / nombre, optimize=True)


def main():
    CAPAS.mkdir(parents=True, exist_ok=True)
    capas = []
    for etiqueta, titulo in [('U', 'Uranio'), ('SREE', 'Tierras raras (ΣREE)')]:
        m, limites = a_web(RESULTADOS / f'{etiqueta}_mediana.tif', categorico=False)
        png_continuo(m, f'{etiqueta}_percentil.png')
        capas.append({'id': f'{etiqueta}_percentil', 'titulo': f'{titulo}: percentil de favorabilidad',
                      'archivo': f'capas/{etiqueta}_percentil.png', 'limites': limites, 'tipo': 'percentil'})
        m, limites = a_web(RESULTADOS / f'{etiqueta}_clase.tif', categorico=True)
        png_categorico(m, COLOR_CLASE, f'{etiqueta}_clase.png')
        capas.append({'id': f'{etiqueta}_clase', 'titulo': f'{titulo}: clases A, B y C',
                      'archivo': f'capas/{etiqueta}_clase.png', 'limites': limites, 'tipo': 'clase'})
    m, limites = a_web(RESULTADOS / 'cruce_U_SREE.tif', categorico=True)
    png_categorico(m, COLOR_CRUCE, 'cruce_U_SREE.png')
    capas.append({'id': 'cruce', 'titulo': 'Zonas prioritarias U + ΣREE', 'archivo': 'capas/cruce_U_SREE.png',
                  'limites': limites, 'tipo': 'cruce'})

    '''Vectores en GeoJSON (WGS 84): área de estudio, franja de prueba y rocas positivas'''
    aoi = lectura.cargar_aoi().to_crs('EPSG:4326')
    franja = gpd.read_file(ARCHIVOS['franja_prueba']).to_crs('EPSG:4326')
    tabla = modelo.cargar_rocas()
    puntos = gpd.GeoDataFrame(tabla[['fuente', 'U_ppm', 'SREE_ppm', 'U_pos', 'SREE_pos']],
                              geometry=gpd.points_from_xy(tabla.x, tabla.y), crs='EPSG:32718').to_crs('EPSG:4326')
    puntos = puntos[(puntos.U_pos == 1) | (puntos.SREE_pos == 1)].round({'U_ppm': 1, 'SREE_ppm': 0})
    vectores = {'aoi': json.loads(aoi[['geometry']].to_json()), 'franja': json.loads(franja[['geometry']].to_json()),
                'positivas': json.loads(puntos.to_json(drop_id=True))}

    '''Logos de la cabecera del panel'''
    for logo in ('logo_andeanx.png', 'logo_pucp.png'):
        shutil.copy(RAIZ / 'recursos' / 'imagenes' / logo, DOCS / logo)

    plantilla = (RAIZ / 'scripts' / 'plantilla_mapa_web.html').read_text(encoding='utf-8')
    rampa = ', '.join(to_hex(plt.get_cmap('cmc.batlow')(t)) for t in np.linspace(0, 1, 9))
    html = plantilla.replace('/*RAMPA*/#011959, #faccfa', rampa)
    html = html.replace('/*CAPAS*/[]', json.dumps(capas, ensure_ascii=False)).replace(
        '/*VECTORES*/{}', json.dumps(vectores, ensure_ascii=False, separators=(',', ':')))
    (DOCS / 'index.html').write_text(html, encoding='utf-8')
    print(f'{len(capas)} capas y {len(puntos)} rocas positivas en {DOCS}')


if __name__ == '__main__':
    main()
