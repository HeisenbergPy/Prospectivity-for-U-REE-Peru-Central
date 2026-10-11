"""Imagen de portada del README: ubicación, relieve, anomalía de Bouguer y muestras de U en roca.

Se ejecuta desde la carpeta del repositorio con:
    uv run python recursos/portada.py
"""

import matplotlib.pyplot as plt

from geocomp import espacial, graficos as graf, lectura
from geocomp.rutas import ARCHIVOS, RAIZ

'''Estilo común y capas'''
graf.aplicar_estilo()
aoi = lectura.cargar_aoi()
departamentos = lectura.cargar_capa('departamentos')
capitales = lectura.cargar_capa('capitales').clip(aoi)
provinciales = capitales[capitales.NOMTIPO.str.contains('PROVINCIAL')].assign(nombre=lambda t: t.NOMPOB.str.title())
estaciones = lectura.cargar_gravedad_estaciones()
uranio = lectura.cargar_uranio()
u_roca = uranio[uranio.U_ppm.notna() & ~uranio.es_mena]

'''Rásteres en UTM'''
elevacion, extension = espacial.raster_a_utm(ARCHIVOS['dem_90m'], aoi, celda=250)
xgm, ext_xgm = espacial.raster_a_utm(ARCHIVOS['gravedad_xgm2019e'], aoi, celda=1000, margen=4000)

fig, ejes = plt.subplots(1, 4, figsize=(16, 6.4), gridspec_kw={'width_ratios': [0.8, 1, 1, 1]})
x0, y0, x1, y1 = aoi.total_bounds

'''(1) Ubicación en el Perú'''
graf.mapa_ubicacion(ejes[0], departamentos, aoi)
ejes[0].set_title('Ubicación')

'''(2) Relieve y capitales de provincia'''
graf.mapa_hipsometrico(ejes[1], elevacion, extension)
graf.rotular_lugares(ejes[1], provinciales, 'nombre', aoi, tamano=8.5, marcador=22)
ejes[1].set_title('Relieve (Copernicus DEM)')

'''(3) Anomalía de Bouguer del modelo global, con las estaciones de INGEMMET'''
ejes[2].imshow(xgm, extent=ext_xgm, cmap=graf.CMAP_CONTINUO, interpolation='bilinear', zorder=0)
graf.relieve(ejes[2], elevacion, extension, opacidad=0.18)
estaciones.plot(ax=ejes[2], color='white', edgecolor='black', linewidth=0.3, markersize=7, zorder=10)
ejes[2].set_title('Anomalía de Bouguer (XGM2019e)')

'''(4) Muestras de roca con U, por fuente'''
graf.relieve(ejes[3], elevacion, extension, opacidad=0.55)
for fuente in lectura.FUENTES_U:
    t = u_roca[u_roca.fuente == fuente]
    t.plot(ax=ejes[3], color=graf.COLORES_FUENTE[fuente], markersize=9 if len(t) > 50 else 22,
           edgecolor='white', linewidth=0.3, zorder=10, label=fuente)
ejes[3].legend(loc='upper center', bbox_to_anchor=(0.5, -0.01), ncol=3, fontsize=8, markerscale=1.5, frameon=False)
ejes[3].set_title('U en roca: cinco fuentes')

'''Mismo encuadre y sin ejes en los tres mapas del área'''
for ax in ejes[1:]:
    aoi.boundary.plot(ax=ax, color='black', lw=1.2, zorder=30)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect('equal')
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel('')
    ax.set_ylabel('')
    ax.grid(False)

fig.suptitle('Prospectivity for "U - REE" - Peru Central', fontsize=20, fontweight='bold', color=graf.AZUL,
             x=0.01, ha='left', y=1.0)
fig.text(0.01, 0.925, '¿Coinciden los datos públicos? Gravimetría y uranio de distintas fuentes en la Cordillera '
         'Oriental de Junín y Pasco', fontsize=11.5, color=graf.GRIS, ha='left')
fig.tight_layout(rect=(0, 0, 1, 0.92), w_pad=0.6)
fig.savefig(RAIZ / 'recursos' / 'portada.png', dpi=150, bbox_inches='tight')
print('Portada guardada en recursos/portada.png')
