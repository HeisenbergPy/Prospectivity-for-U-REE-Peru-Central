"""Imágenes de los diseños del README (portada, flujo de trabajo y resultados).

Genera en `recursos/imagenes/` los mapas sin ejes que usan las páginas de `recursos/diseno/`:
    ubicacion.png      el Perú por departamentos y el área de estudio
    relieve.png        elevación con sombreado
    bouguer.png        anomalía de Bouguer del modelo XGM2019e y estaciones de INGEMMET
    uranio.png         muestras de roca con U, por fuente
    curvas_nivel.png   curvas de nivel cada 200 m (fondo de la portada, transparente)
    favorabilidad_U.png  percentil de favorabilidad del U (mediana de los modelos hábiles de GC04)
    zonas.png          zonas prioritarias para U y ΣREE (cruce de clases de GC04)
    *_violeta.png      relieve, gravedad, U en roca y zonas en tonos violeta, para la portada

Uso, desde la carpeta del repositorio (después de ejecutar GC04, que escribe `resultados/`):
    uv run python recursos/paneles.py
"""

import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.colors import to_rgb

from geocomp import espacial, graficos as graf, lectura
from geocomp.rutas import ARCHIVOS, RAIZ, RESULTADOS

SALIDA = RAIZ / 'recursos' / 'imagenes'
SALIDA.mkdir(parents=True, exist_ok=True)

'''Capas'''
graf.aplicar_estilo()
aoi = lectura.cargar_aoi()
x0, y0, x1, y1 = aoi.total_bounds
departamentos = lectura.cargar_capa('departamentos')
estaciones = lectura.cargar_gravedad_estaciones()
uranio = lectura.cargar_uranio()
u_roca = uranio[uranio.U_ppm.notna() & ~uranio.es_mena]
elevacion, extension = espacial.raster_a_utm(ARCHIVOS['dem_90m'], aoi, celda=250, margen=0)
xgm, ext_xgm = espacial.raster_a_utm(ARCHIVOS['gravedad_xgm2019e'], aoi, celda=1000, margen=0)


def mapa_vacio(alto=7.0):
    '''Figura del tamaño exacto del área de estudio, sin ejes ni márgenes'''
    fig = plt.figure(figsize=(alto * (x1 - x0) / (y1 - y0), alto))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_axis_off()
    return fig, ax


def guardar(fig, nombre, transparente=False):
    fig.savefig(SALIDA / nombre, dpi=150, transparent=transparente)
    plt.close(fig)


'''Ubicación en el Perú'''
fig, ax = plt.subplots(figsize=(4, 5.4))
graf.mapa_ubicacion(ax, departamentos, aoi)
ax.texts[-1].remove()                                   # sin el rótulo «PERÚ»: lo pone el diseño
ax.set_axis_off()
fig.subplots_adjust(0, 0, 1, 1)
guardar(fig, 'ubicacion.png', transparente=True)

'''Relieve'''
fig, ax = mapa_vacio()
graf.mapa_hipsometrico(ax, elevacion, extension)
guardar(fig, 'relieve.png')

'''Anomalía de Bouguer del modelo y estaciones'''
fig, ax = mapa_vacio()
ax.imshow(xgm, extent=ext_xgm, cmap=graf.CMAP_CONTINUO, interpolation='bilinear', zorder=0)
graf.relieve(ax, elevacion, extension, opacidad=0.2)
estaciones.plot(ax=ax, color='white', edgecolor='black', linewidth=0.4, markersize=14, zorder=10)
ax.set_xlim(x0, x1)
ax.set_ylim(y0, y1)
guardar(fig, 'bouguer.png')

'''Muestras de U por fuente'''
fig, ax = mapa_vacio()
graf.relieve(ax, elevacion, extension, opacidad=0.6)
for fuente in lectura.FUENTES_U:
    t = u_roca[u_roca.fuente == fuente]
    t.plot(ax=ax, color=graf.COLORES_FUENTE[fuente], markersize=16 if len(t) > 50 else 40,
           edgecolor='white', linewidth=0.4, zorder=10)
ax.set_xlim(x0, x1)
ax.set_ylim(y0, y1)
guardar(fig, 'uranio.png')

'''Curvas de nivel cada 200 m, en blanco sobre fondo transparente'''
fig, ax = mapa_vacio(alto=9)
x = np.linspace(extension[0], extension[1], elevacion.shape[1])
y = np.linspace(extension[3], extension[2], elevacion.shape[0])
ax.contour(x, y, elevacion, levels=np.arange(400, 5000, 200), colors='white', linewidths=0.5)
guardar(fig, 'curvas_nivel.png', transparente=True)

'''Resultados de GC04: favorabilidad del U y zonas prioritarias sobre el relieve'''
def leer_resultado(nombre):
    with rasterio.open(RESULTADOS / nombre) as src:
        b = src.bounds
        return src.read(1), (b.left, b.right, b.bottom, b.top)


fig, ax = mapa_vacio()
graf.relieve(ax, elevacion, extension, opacidad=0.9)
mediana, ext_res = leer_resultado('U_mediana.tif')
ax.imshow(mediana, extent=ext_res, cmap='cmc.batlow', vmin=0, vmax=100, alpha=0.78, interpolation='nearest', zorder=2)
ax.set_xlim(x0, x1)
ax.set_ylim(y0, y1)
guardar(fig, 'favorabilidad_U.png')

COLOR_CRUCE = {4: '#79326e', 3: '#bd5888', 2: '#f7aa5f', 1: '#a79acd'}
cruce, ext_res = leer_resultado('cruce_U_SREE.tif')
rgba = np.zeros(cruce.shape + (4,))
for k, c in COLOR_CRUCE.items():
    rgba[cruce == k] = [*to_rgb(c), 0.88]
fig, ax = mapa_vacio()
graf.relieve(ax, elevacion, extension, opacidad=0.9)
ax.imshow(rgba, extent=ext_res, interpolation='nearest', zorder=2)
ax.set_xlim(x0, x1)
ax.set_ylim(y0, y1)
guardar(fig, 'zonas.png')

'''Versiones en tonos violeta para la portada: relieve sombreado en una rampa del morado oscuro al lavanda claro, la
misma de las presentaciones del proyecto'''
from matplotlib.colors import LightSource, LinearSegmentedColormap
VIOLETA = LinearSegmentedColormap.from_list('violeta', ['#1c1926', '#45405a', '#8a83a3', '#d6d2e3', '#f8f7fb'])


def sombra_violeta(ax, opacidad=1.0):
    z = np.where(np.isfinite(elevacion), elevacion, np.nanmin(elevacion))
    paso = (extension[1] - extension[0]) / elevacion.shape[1]
    s_ = LightSource(azdeg=315, altdeg=40).hillshade(z, vert_exag=2.2, dx=paso, dy=paso)
    ax.imshow(s_, extent=extension, cmap=VIOLETA, vmin=0.05, vmax=1, alpha=opacidad, zorder=0,
              interpolation='bilinear')


fig, ax = mapa_vacio()
sombra_violeta(ax)
guardar(fig, 'relieve_violeta.png')

fig, ax = mapa_vacio()
ax.imshow(xgm, extent=ext_xgm, cmap='cmc.acton', interpolation='bilinear', zorder=0)
sombra_violeta(ax, opacidad=0.35)
estaciones.plot(ax=ax, color='white', edgecolor='#26262f', linewidth=0.4, markersize=12, zorder=10)
ax.set_xlim(x0, x1)
ax.set_ylim(y0, y1)
guardar(fig, 'bouguer_violeta.png')

fig, ax = mapa_vacio()
sombra_violeta(ax, opacidad=0.85)
alto_u = u_roca.sort_values('U_ppm')
ax.scatter(alto_u.geometry.x, alto_u.geometry.y, c=np.log10(alto_u.U_ppm.clip(0.3, 60)), cmap='cmc.lajolla',
           s=14, edgecolor='#1d1830', linewidth=0.3, zorder=10)
ax.set_xlim(x0, x1)
ax.set_ylim(y0, y1)
guardar(fig, 'uranio_violeta.png')

fig, ax = mapa_vacio(alto=9)
sombra_violeta(ax, opacidad=0.9)
ax.imshow(rgba, extent=ext_res, interpolation='nearest', zorder=2)
ax.set_xlim(x0, x1)
ax.set_ylim(y0, y1)
guardar(fig, 'zonas_violeta.png')

print('Imágenes guardadas en recursos/imagenes/')
