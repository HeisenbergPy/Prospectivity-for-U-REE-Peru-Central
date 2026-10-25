"""Descarga de nuevo las fuentes públicas y las compara con la copia de `datos/`.

Los datos del repositorio son una copia fija (con huella sha256) para que el análisis sea reproducible. Este script
muestra de dónde salió cada archivo: vuelve a pedirlo a su fuente, lo guarda en `descargas/` (carpeta que no se sube)
y comprueba que coincida con la copia. Nunca modifica `datos/`.

Fuentes:
    geocatmin  cinco capas de INGEMMET (estaciones, sedimentos, litogeoquímica, BDG 2022 y GE27) dentro del área
    dem        teselas del Copernicus DEM GLO-90 (AWS), recortadas a la misma grilla de la copia
    icgem      coeficientes de XGM2019e_2159 y etopo1-2250 (420 MB), que usa scripts/sintesis_xgm2019e.py

Las tablas del IPEN y del Boletín B-74 no se descargan: se transcribieron de los informes en PDF (ver datos/LEEME.md).

Uso:
    uv run python scripts/descargar_datos.py                    # todas las fuentes
    uv run python scripts/descargar_datos.py --fuentes geocatmin dem
"""

import argparse
import sys

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.merge import merge
from rasterio.windows import from_bounds
from scipy.spatial import cKDTree

from geocomp import acceso, lectura
from geocomp.rutas import ARCHIVOS, CRS_UTM, RAIZ

DESCARGAS = RAIZ / 'descargas'

# Caja del mosaico regional (lon_min, lat_min, lon_max, lat_max) del que se recortó el DEM de datos/
MOSAICO_REGIONAL = (-77.6, -13.8, -73.8, -9.7)


def comparar_puntos(nueva, copia, tolerancia_m=1.0):
    """Cuántos puntos de la descarga tienen un punto de la copia a menos de `tolerancia_m` metros (en UTM)."""
    a, b = nueva.to_crs(CRS_UTM), copia.to_crs(CRS_UTM)
    arbol = cKDTree(np.column_stack([b.geometry.x, b.geometry.y]))
    d, _ = arbol.query(np.column_stack([a.geometry.x, a.geometry.y]))
    return int((d <= tolerancia_m).sum())


def descargar_geocatmin():
    """Descarga cada capa de GEOCATMIN dentro de la caja del área y la compara con la copia."""
    caja = tuple(lectura.cargar_aoi(crs='EPSG:4326').total_bounds)
    filas = []
    for clave, capa in acceso.CAPAS_GEOCATMIN.items():
        print(f'  {clave}: {capa}')
        nueva = acceso.descargar_capa(capa, caja)
        nueva.to_file(DESCARGAS / 'geocatmin' / f'{clave}.gpkg', driver='GPKG')
        copia = gpd.read_file(ARCHIVOS[clave])
        filas.append({'capa': clave, 'servicio': capa, 'descargadas': len(nueva), 'en datos/': len(copia),
                      'mismo lugar (< 1 m)': comparar_puntos(nueva, copia)})
    return pd.DataFrame(filas)


def descargar_dem():
    """Une las teselas del DEM y recorta la ventana de la copia.

    La copia se recortó de un mosaico regional cuya grilla empieza en (-77,6; -9,7), medio píxel corrida respecto
    de la de las teselas. Por eso el mosaico se arma en esa misma grilla y luego se toma la ventana del área: si se
    armara directamente en la caja del área, el desempate del vecino más cercano en ese medio píxel elegiría la fila
    vecina en el 40 % de las celdas.
    """
    with rasterio.open(ARCHIVOS['dem_90m']) as copia:
        bounds, original = copia.bounds, copia.read(1, masked=True)
        caja = (bounds.left, bounds.bottom, bounds.right, bounds.top)
    teselas = ['/vsicurl/' + url for url in acceso.teselas_dem(caja)]
    print(f'  {len(teselas)} teselas de Copernicus GLO-90')
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR'):
        mosaico, regional = merge(teselas, bounds=MOSAICO_REGIONAL, nodata=-9999.0)
    ventana = from_bounds(*caja, transform=regional).round_offsets().round_lengths()
    filas, columnas = ventana.toslices()
    nuevo = np.ma.masked_equal(mosaico[0][filas, columnas], -9999.0)
    transformacion = rasterio.windows.transform(ventana, regional)
    perfil = dict(driver='GTiff', dtype='float32', nodata=-9999.0, width=nuevo.shape[1], height=nuevo.shape[0],
                  count=1, crs='EPSG:4326', transform=transformacion, compress='deflate')
    with rasterio.open(DESCARGAS / 'dem_copernicus_90m.tif', 'w', **perfil) as destino:
        destino.write(nuevo.filled(-9999.0).astype('float32'), 1)
    iguales = nuevo.shape == original.shape
    diferencia = float(np.abs(nuevo - original).max()) if iguales else np.nan
    return pd.DataFrame([{'capa': 'dem_90m', 'servicio': 'Copernicus GLO-90 (AWS)',
                          'celdas': nuevo.count(), 'en datos/': original.count(),
                          'diferencia máxima (m)': diferencia}])


def descargar_icgem():
    """Coeficientes de los modelos de ICGEM para la síntesis (no hay copia en datos/: pesan 420 MB)."""
    filas = []
    for nombre, url in acceso.MODELOS_ICGEM.items():
        print(f'  {nombre}')
        ruta = acceso.descargar_archivo(url, DESCARGAS / 'icgem' / nombre)
        filas.append({'capa': nombre, 'servicio': 'ICGEM (GFZ Potsdam)', 'MB': round(ruta.stat().st_size / 1e6)})
    return pd.DataFrame(filas)


FUENTES = {'geocatmin': descargar_geocatmin, 'dem': descargar_dem, 'icgem': descargar_icgem}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--fuentes', nargs='+', choices=FUENTES, default=list(FUENTES))
    args = parser.parse_args()
    (DESCARGAS / 'geocatmin').mkdir(parents=True, exist_ok=True)

    correcto = True
    for fuente in args.fuentes:
        print(f'\n{fuente.upper()}')
        try:
            resumen = FUENTES[fuente]()
        except Exception as error:                  # una fuente caída no detiene a las demás
            print(f'  No se pudo descargar ({type(error).__name__}: {error})')
            correcto = False
            continue
        print(resumen.to_string(index=False))
        if fuente == 'geocatmin':
            correcto &= bool((resumen['descargadas'] == resumen['en datos/']).all())
        if fuente == 'dem':
            correcto &= bool((resumen['diferencia máxima (m)'] < 0.01).all())
    print('\nTodo coincide con datos/.' if correcto else '\nHay diferencias o fuentes sin respuesta: revisar arriba.')
    return 0 if correcto else 1


if __name__ == '__main__':
    sys.exit(main())
