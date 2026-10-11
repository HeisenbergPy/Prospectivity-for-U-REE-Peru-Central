"""Operaciones espaciales: muestrear un ráster en puntos, emparejar muestras cercanas de dos fuentes y medir la
cobertura de cada fuente en una grilla regular.
"""

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject
from scipy.ndimage import map_coordinates
from scipy.spatial import cKDTree
from shapely.geometry import box


# ------------------------------------------------------------------------------------------ ráster a puntos
def muestrear_raster(ruta, puntos, metodo='bilineal'):
    """Valor del ráster en cada punto.

    Los puntos se reproyectan al CRS del ráster.
        'bilineal'  interpola entre los cuatro centros de píxel vecinos (adecuado para campos continuos como la
                    gravedad). En la media celda del borde exterior usa el valor del píxel del borde.
        'cercano'   toma el valor del píxel que contiene al punto.
    Devuelve NaN para los puntos fuera del ráster. En modo bilineal, si alguno de los cuatro vecinos no tiene dato,
    el resultado también es NaN (no se inventa un valor a partir de celdas vacías).
    """
    if metodo not in ('bilineal', 'cercano'):
        raise ValueError(f"metodo debe ser 'bilineal' o 'cercano', no {metodo!r}")
    with rasterio.open(ruta) as src:
        t = src.transform
        if t.b != 0 or t.d != 0:
            raise ValueError('El ráster está rotado; esta función solo admite rásteres alineados con los ejes')
        datos = src.read(1).astype(float)
        if src.nodata is not None:
            datos[datos == src.nodata] = np.nan
        p = puntos.to_crs(src.crs)
    # Posición del punto en unidades de píxel: (0, 0) es la esquina superior izquierda del ráster
    col = (p.geometry.x.values - t.c) / t.a
    fila = (p.geometry.y.values - t.f) / t.e
    filas, cols = datos.shape
    fuera = (fila < 0) | (col < 0) | (fila > filas) | (col > cols)
    if metodo == 'cercano':
        f = np.clip(np.floor(fila), 0, filas - 1).astype(int)
        c = np.clip(np.floor(col), 0, cols - 1).astype(int)
        valores = datos[f, c]
    else:
        # map_coordinates ubica el centro del píxel (0, 0) en (0, 0): por eso se resta medio píxel
        valores = map_coordinates(datos, [fila - 0.5, col - 0.5], order=1, mode='nearest')
    return np.where(fuera, np.nan, valores)


# ------------------------------------------------------------------------------------------ pares entre fuentes
def pares_cercanos(a, b, distancia_max):
    """Pares únicos entre dos capas en metros (UTM): cada muestra de `b` busca la de `a` más cercana, si está a
    menos de `distancia_max` metros.

    Si varias muestras de `b` eligen la misma muestra de `a`, solo se conserva el par más cercano. Las que pierden
    no buscan una segunda opción: se prefiere perder pares antes que repetir una roca, porque una roca atípica
    emparejada varias veces sesgaría la comparación.
    Devuelve una tabla con los índices de ambas capas (`i_a`, `i_b`) y la distancia en metros.
    """
    _exigir_metros(a, b)
    if len(a) == 0 or len(b) == 0:
        return pd.DataFrame(columns=['i_a', 'i_b', 'dist_m'])
    arbol = cKDTree(np.column_stack([a.geometry.x, a.geometry.y]))
    d, j = arbol.query(np.column_stack([b.geometry.x, b.geometry.y]), distance_upper_bound=distancia_max)
    ok = np.isfinite(d)
    pares = pd.DataFrame({'i_a': a.index[j[ok]], 'i_b': b.index[ok], 'dist_m': d[ok]})
    return pares.sort_values('dist_m').drop_duplicates('i_a').reset_index(drop=True)


def vecino_mas_cercano(origen, destino, columnas):
    """Para cada punto de `origen`, los valores de `columnas` del punto de `destino` más cercano y su distancia (m)."""
    _exigir_metros(origen, destino)
    arbol = cKDTree(np.column_stack([destino.geometry.x, destino.geometry.y]))
    d, j = arbol.query(np.column_stack([origen.geometry.x, origen.geometry.y]))
    tabla = destino.iloc[j][columnas].reset_index(drop=True)
    tabla.index = origen.index
    tabla['dist_vecino_m'] = d
    return tabla


# ------------------------------------------------------------------------------------------ cobertura
def grilla(aoi, celda):
    """Grilla regular de celdas cuadradas de `celda` metros que cubre el área de estudio."""
    x0, y0, x1, y1 = aoi.total_bounds
    xs, ys = np.arange(x0, x1, celda), np.arange(y0, y1, celda)
    celdas = [box(x, y, min(x + celda, x1), min(y + celda, y1)) for y in ys for x in xs]
    return gpd.GeoDataFrame({'id_celda': range(len(celdas))}, geometry=celdas, crs=aoi.crs)


def celda_de(puntos, aoi, celda):
    """Número de celda de la grilla (mismo orden que `grilla`) en que cae cada punto; −1 si cae fuera de la caja.

    Se calcula con división entera: un punto sobre la línea entre dos celdas pertenece siempre a una sola (la de la
    derecha o la de arriba), y un punto sobre el borde exterior de la caja se asigna a la celda del borde.
    """
    _exigir_metros(puntos, aoi)
    x0, y0, x1, y1 = aoi.total_bounds
    n_x, n_y = int(np.ceil((x1 - x0) / celda)), int(np.ceil((y1 - y0) / celda))
    x, y = puntos.geometry.x.values, puntos.geometry.y.values
    i = np.minimum(np.floor((x - x0) / celda), n_x - 1)
    j = np.minimum(np.floor((y - y0) / celda), n_y - 1)
    dentro = (x >= x0) & (x <= x1) & (y >= y0) & (y <= y1)
    return np.where(dentro, j * n_x + i, -1).astype(int)


def cobertura(puntos, aoi, celda=5000, grupo=None):
    """Porcentaje de celdas de la grilla con al menos un punto (por grupo, si se indica una columna).

    Es una medida simple de qué tan repartida está una fuente: 100 puntos juntos en una quebrada cubren poco.
    """
    n_celdas = len(grilla(aoi, celda))
    tabla = pd.DataFrame({'id_celda': celda_de(puntos, aoi, celda)}, index=puntos.index)
    tabla['grupo'] = puntos[grupo].values if grupo else 'todas'
    tabla = tabla[tabla['id_celda'] >= 0]
    filas = [{'grupo': g, 'puntos': len(t), 'celdas_con_dato': t['id_celda'].nunique(),
              'cobertura_pct': 100 * t['id_celda'].nunique() / n_celdas}
             for g, t in tabla.groupby('grupo', sort=False)]
    return pd.DataFrame(filas).set_index('grupo')


def _exigir_metros(*capas):
    """Las distancias y las grillas se calculan en metros: todas las capas deben estar en el mismo CRS proyectado."""
    crs = {str(c.crs) for c in capas}
    if len(crs) != 1 or capas[0].crs is None or capas[0].crs.is_geographic:
        raise ValueError(f'Las capas deben compartir un CRS proyectado en metros (UTM); se recibió: {crs}')


# ------------------------------------------------------------------------------------------ ráster a UTM
def raster_a_utm(ruta, aoi, celda=250, margen=5000, metodo='bilineal'):
    """Reproyecta un ráster a la grilla UTM del área de estudio (más un margen), con celdas de `celda` metros.

    Devuelve (matriz, extension), donde extension = (x_min, x_max, y_min, y_max) sirve para `imshow`.
    Las celdas sin dato quedan como NaN.
    """
    x0, y0, x1, y1 = aoi.total_bounds
    x0, y0, x1, y1 = x0 - margen, y0 - margen, x1 + margen, y1 + margen
    ancho, alto = int(np.ceil((x1 - x0) / celda)), int(np.ceil((y1 - y0) / celda))
    destino = np.full((alto, ancho), np.nan)
    remuestreo = Resampling.bilinear if metodo == 'bilineal' else Resampling.nearest
    with rasterio.open(ruta) as src:
        reproject(source=rasterio.band(src, 1), destination=destino, src_nodata=src.nodata, dst_nodata=np.nan,
                  dst_transform=from_origin(x0, y1, celda, celda), dst_crs=aoi.crs, resampling=remuestreo)
    return destino, (x0, x0 + ancho * celda, y1 - alto * celda, y1)
