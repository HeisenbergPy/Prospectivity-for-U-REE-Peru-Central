"""Mapas sin ejes que usan las páginas de `recursos/diseno/` (portada, vista previa y resultados del modelo).

Genera en `recursos/imagenes/`, con el relieve sombreado en tonos violeta (los de las presentaciones del proyecto):
    relieve_violeta.png   relieve del área de estudio
    bouguer_violeta.png   anomalía de Bouguer del modelo XGM2019e y estaciones de INGEMMET
    uranio_violeta.png    rocas con U medido, coloreadas por su concentración
    zonas_violeta.png     zonas prioritarias para U y ΣREE (cruce de clases de GC04)

Uso, desde la carpeta del repositorio (después de ejecutar GC04, que escribe `resultados/`):
    uv run python recursos/paneles.py
"""

import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.colors import LightSource, LinearSegmentedColormap, to_rgb

from geocomp import espacial, graficos as graf, lectura
from geocomp.rutas import ARCHIVOS, RAIZ, RESULTADOS

SALIDA = RAIZ / 'recursos' / 'imagenes'
SALIDA.mkdir(parents=True, exist_ok=True)

'''Relieve sombreado en una rampa del morado oscuro al lavanda claro'''
VIOLETA = LinearSegmentedColormap.from_list('violeta', ['#1c1926', '#45405a', '#8a83a3', '#d6d2e3', '#f8f7fb'])
COLOR_CRUCE = {4: '#79326e', 3: '#bd5888', 2: '#f7aa5f', 1: '#a79acd'}

'''Capas'''
graf.aplicar_estilo()
aoi = lectura.cargar_aoi()
x0, y0, x1, y1 = aoi.total_bounds
estaciones = lectura.cargar_gravedad_estaciones()
uranio = lectura.cargar_uranio()
u_roca = uranio[uranio.U_ppm.notna() & ~uranio.es_mena]
elevacion, extension = espacial.raster_a_utm(ARCHIVOS['dem_90m'], aoi, celda=250, margen=0)
xgm, ext_xgm = espacial.raster_a_utm(ARCHIVOS['gravedad_xgm2019e'], aoi, celda=1000, margen=0)


def mapa_vacio(alto=7.0):
    '''Figura del tamaño exacto del área de estudio, sin ejes ni márgenes'''
    fig = plt.figure(figsize=(alto * (x1 - x0) / (y1 - y0), alto))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    return fig, ax


def guardar(fig, ax, nombre):
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    fig.savefig(SALIDA / nombre, dpi=150)
    plt.close(fig)


def sombra_violeta(ax, opacidad=1.0):
    z = np.where(np.isfinite(elevacion), elevacion, np.nanmin(elevacion))
    paso = (extension[1] - extension[0]) / elevacion.shape[1]
    s_ = LightSource(azdeg=315, altdeg=40).hillshade(z, vert_exag=2.2, dx=paso, dy=paso)
    ax.imshow(s_, extent=extension, cmap=VIOLETA, vmin=0.05, vmax=1, alpha=opacidad, zorder=0,
              interpolation='bilinear')


'''Relieve'''
fig, ax = mapa_vacio()
sombra_violeta(ax)
guardar(fig, ax, 'relieve_violeta.png')

'''Anomalía de Bouguer del modelo y estaciones'''
fig, ax = mapa_vacio()
ax.imshow(xgm, extent=ext_xgm, cmap='cmc.acton', interpolation='bilinear', zorder=0)
sombra_violeta(ax, opacidad=0.35)
estaciones.plot(ax=ax, color='white', edgecolor='#26262f', linewidth=0.4, markersize=12, zorder=10)
guardar(fig, ax, 'bouguer_violeta.png')

'''Rocas con U medido (las de más U, encima)'''
fig, ax = mapa_vacio()
sombra_violeta(ax, opacidad=0.85)
orden = u_roca.sort_values('U_ppm')
ax.scatter(orden.geometry.x, orden.geometry.y, c=np.log10(orden.U_ppm.clip(0.3, 60)), cmap='cmc.lajolla', s=14,
           edgecolor='#1d1830', linewidth=0.3, zorder=10)
guardar(fig, ax, 'uranio_violeta.png')

'''Zonas prioritarias de GC04'''
with rasterio.open(RESULTADOS / 'cruce_U_SREE.tif') as src:
    cruce, b = src.read(1), src.bounds
rgba = np.zeros(cruce.shape + (4,))
for k, c in COLOR_CRUCE.items():
    rgba[cruce == k] = [*to_rgb(c), 0.88]
fig, ax = mapa_vacio(alto=9)
sombra_violeta(ax, opacidad=0.9)
ax.imshow(rgba, extent=(b.left, b.right, b.bottom, b.top), interpolation='nearest', zorder=2)
guardar(fig, ax, 'zonas_violeta.png')

print('Imágenes guardadas en recursos/imagenes/')
