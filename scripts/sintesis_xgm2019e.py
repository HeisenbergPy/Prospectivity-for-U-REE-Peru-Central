"""Síntesis armónica del modelo global de gravedad XGM2019e en el área de estudio.

Calcula, a partir de los coeficientes oficiales de ICGEM (GFZ Potsdam):
    1. la grilla de la anomalía de Bouguer simple de `datos/gravedad/gravedad_XGM2019e_bouguer.tif`
       (paso de 0,025°, sobre el elipsoide GRS80, h = 0), y la compara con la copia del repositorio;
    2. el valor del modelo en cada estación gravimétrica de INGEMMET, sobre el elipsoide (h = 0) y a la altura de la
       estación (cota del DEM + ondulación del geoide), que usa el cuaderno GC02 (`xgm2019e_estaciones.csv`);
    3. la misma grilla evaluada en la superficie del modelo (topografía H + ondulación N en cada nodo), que usa GC03
       (`gravedad_XGM2019e_bouguer_superficie.tif`).

Los coeficientes (420 MB en total) se descargan a `descargas/icgem/`, carpeta que no se sube al repositorio.

Uso:
    uv run python scripts/sintesis_xgm2019e.py               # calcula y compara con datos/ (no modifica nada)
    uv run python scripts/sintesis_xgm2019e.py --actualizar  # además escribe en datos/ la tabla y la grilla de superficie
"""

import argparse
import sys
import time

import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_origin

from geocomp import acceso, espacial, gravedad, lectura
from geocomp.rutas import ARCHIVOS, RAIZ

DESCARGAS = RAIZ / 'descargas'

# Grilla pedida a ICGEM: nodos de -75,700 a -74,400 de longitud y de -11,900 a -10,350 de latitud, cada 0,025°
PASO = 0.025
LONS = np.round(np.arange(-75.700, -74.400 + PASO / 2, PASO), 3)
LATS = np.round(np.arange(-10.350, -11.900 - PASO / 2, -PASO), 3)          # de norte a sur, como las filas del TIF

# Estadísticas que publica ICGEM para la misma grilla (página de resultados del cálculo, 26/09/2026)
ICGEM_BOUGUER = {'mín.': -424.456, 'máx.': -13.506}
ICGEM_TOPOGRAFIA = {'mín.': 155.748, 'máx.': 4866.929}


def leer_modelos():
    """Descarga (si falta) y lee los coeficientes de gravedad y de topografía, ambos hasta el grado 2190."""
    rutas = {nombre: acceso.descargar_archivo(url, DESCARGAS / 'icgem' / nombre)
             for nombre, url in acceso.MODELOS_ICGEM.items()}
    C, S, cabecera = gravedad.leer_gfc(rutas['XGM2019e_2159.gfc'])
    dC = gravedad.restar_campo_normal(C, cabecera)
    Ct, St, cabecera_t = gravedad.leer_gfc(rutas['etopo1-2250.gfc'], grado_max=cabecera['grado'])
    return (dC, S, cabecera), (Ct, St, cabecera_t)


def grilla_bouguer(modelo, topografia):
    """Anomalía de Bouguer simple en la grilla: Δg (h = 0) − 2πGρH."""
    anomalia = gravedad.sintesis_grilla(*modelo, LATS, LONS, h=0.0, funcional='anomalia')
    H = gravedad.sintesis_grilla(*topografia, LATS, LONS, h=0.0, funcional='superficie')
    return anomalia - gravedad.correccion_placa(H), H


def grilla_bouguer_superficie(modelo, topografia, H):
    """Bouguer simple con cada nodo a su altura: la topografía del modelo H más la ondulación del geoide N.

    En una grilla de superficie la altura cambia de nodo a nodo, así que no sirve el producto de matrices por filas
    de `sintesis_grilla`: se evalúa cada fila de la grilla como un conjunto de puntos sueltos.
    """
    N = gravedad.sintesis_grilla(*modelo, LATS, LONS, h=0.0, funcional='potencial') / 9.78
    LON = np.broadcast_to(LONS, (LATS.size, LONS.size))
    filas = [gravedad.sintesis_puntos(*modelo, np.full(LONS.size, lat), LON[i], h=H[i] + N[i], funcional='anomalia')
             for i, lat in enumerate(LATS)]
    return np.vstack(filas) - gravedad.correccion_placa(H)


def guardar_tif(matriz, ruta, funcional='Bouguer simple, rho = 2670 kg/m3, h = 0 sobre GRS80'):
    """GeoTIFF en EPSG:4326 con cada píxel centrado en un nodo de la grilla."""
    perfil = dict(driver='GTiff', dtype='float32', nodata=-99999.0, width=LONS.size, height=LATS.size, count=1,
                  crs='EPSG:4326', transform=from_origin(LONS[0] - PASO / 2, LATS[0] + PASO / 2, PASO, PASO),
                  compress='deflate')
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(ruta, 'w', **perfil) as destino:
        destino.write(matriz.astype('float32'), 1)
        destino.update_tags(UNITS='mGal', MODEL='XGM2019e_2159 (grado 2190)', TOPOGRAPHY='etopo1-2250 (grado 2190)',
                            FUNCTIONAL=funcional)


def valores_en_estaciones(modelo, topografia):
    """Modelo en cada estación: sobre el elipsoide (h = 0) y a la altura de la estación.

    La altura elipsoidal de la estación es la cota del DEM (altura sobre el geoide) más la ondulación del geoide N,
    que se obtiene del propio modelo: N ≈ T/γ, con T el potencial perturbador sobre el elipsoide.
    """
    estaciones = lectura.cargar_gravedad_estaciones()
    geo = estaciones.to_crs('EPSG:4326')
    lat, lon = geo.geometry.y.values, geo.geometry.x.values
    h_dem = espacial.muestrear_raster(ARCHIVOS['dem_90m'], estaciones)
    N = gravedad.sintesis_puntos(*modelo, lat, lon, h=0.0, funcional='potencial') / 9.78
    H = gravedad.sintesis_puntos(*topografia, lat, lon, h=0.0, funcional='superficie')
    dg_h0 = gravedad.sintesis_puntos(*modelo, lat, lon, h=0.0, funcional='anomalia')
    dg_sup = gravedad.sintesis_puntos(*modelo, lat, lon, h=h_dem + N, funcional='anomalia')
    placa = gravedad.correccion_placa(H)
    return pd.DataFrame({
        'OBJECTID': estaciones.OBJECTID.values, 'lon': lon.round(6), 'lat': lat.round(6),
        'h_dem_m': h_dem.round(1), 'N_geoide_m': N.round(2), 'H_modelo_m': H.round(1),
        'bouguer_h0_mgal': (dg_h0 - placa).round(3), 'bouguer_superficie_mgal': (dg_sup - placa).round(3),
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--actualizar', action='store_true',
                        help='escribe la tabla de las estaciones en datos/gravedad/ (luego hay que actualizar el manifiesto)')
    args = parser.parse_args()

    inicio = time.time()
    print('Leyendo los coeficientes de XGM2019e_2159 y etopo1-2250 ...')
    modelo, topografia = leer_modelos()

    print('Síntesis de la grilla ...')
    bouguer, H = grilla_bouguer(modelo, topografia)
    guardar_tif(bouguer, DESCARGAS / 'gravedad_XGM2019e_bouguer.tif')
    with rasterio.open(ARCHIVOS['gravedad_xgm2019e']) as src:
        repositorio = src.read(1)
    diferencia = np.abs(bouguer - repositorio).max()
    print(f'  Bouguer: mín. {bouguer.min():.3f} | máx. {bouguer.max():.3f} mGal '
          f'(ICGEM: {ICGEM_BOUGUER["mín."]} | {ICGEM_BOUGUER["máx."]})')
    print(f'  Topografía: mín. {H.min():.3f} | máx. {H.max():.3f} m '
          f'(ICGEM: {ICGEM_TOPOGRAFIA["mín."]} | {ICGEM_TOPOGRAFIA["máx."]})')
    print(f'  Diferencia máxima con datos/gravedad/gravedad_XGM2019e_bouguer.tif: {diferencia:.5f} mGal')

    print('Grilla en la superficie del modelo ...')
    superficie = grilla_bouguer_superficie(modelo, topografia, H)
    destino_sup = ARCHIVOS['gravedad_xgm2019e_superficie'] if args.actualizar else DESCARGAS / 'gravedad_XGM2019e_bouguer_superficie.tif'
    guardar_tif(superficie, destino_sup, 'Bouguer simple, rho = 2670 kg/m3, en la superficie del modelo (h = H + N)')
    print(f'  mín. {superficie.min():.1f} | máx. {superficie.max():.1f} mGal -> {destino_sup.relative_to(RAIZ)}')

    print('Modelo en las estaciones ...')
    tabla = valores_en_estaciones(modelo, topografia)
    destino = ARCHIVOS['xgm2019e_estaciones'] if args.actualizar else DESCARGAS / 'xgm2019e_estaciones.csv'
    tabla.to_csv(destino, index=False, lineterminator='\n')
    print(f'  {len(tabla)} estaciones -> {destino.relative_to(RAIZ)}')
    if not args.actualizar and ARCHIVOS['xgm2019e_estaciones'].exists():
        guardada = pd.read_csv(ARCHIVOS['xgm2019e_estaciones'])
        columnas = ['bouguer_h0_mgal', 'bouguer_superficie_mgal']
        print(f'  Diferencia máxima con la tabla de datos/: '
              f'{np.abs(guardada[columnas].values - tabla[columnas].values).max():.4f} mGal')

    print(f'Listo en {time.time() - inicio:.0f} s')
    return 0 if diferencia < 0.01 else 1


if __name__ == '__main__':
    sys.exit(main())
