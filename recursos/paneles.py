"""Imágenes de los diseños del README (portada, flujo de trabajo y resultados).

Genera en `recursos/imagenes/` los mapas sin ejes que usan las páginas de `recursos/diseno/`:
    ubicacion.png      el Perú por departamentos y el área de estudio
    relieve.png        elevación con sombreado
    bouguer.png        anomalía de Bouguer del modelo XGM2019e y estaciones de INGEMMET
    uranio.png         muestras de roca con U, por fuente
    curvas_nivel.png   curvas de nivel cada 200 m (fondo de la portada, transparente)

Uso, desde la carpeta del repositorio:
    uv run python recursos/paneles.py
"""

import matplotlib.pyplot as plt
import numpy as np

from geocomp import espacial, graficos as graf, lectura
from geocomp.rutas import ARCHIVOS, RAIZ

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

print('Imágenes guardadas en recursos/imagenes/')
