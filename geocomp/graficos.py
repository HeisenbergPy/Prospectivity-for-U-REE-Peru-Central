"""Estilo de las figuras y elementos de los mapas (norte, escala, grilla en km), con números en formato español."""

from pathlib import Path

import cmcrameri  # noqa: F401  (registra los mapas de color científicos 'cmc.*')
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import shapely
from cycler import cycler
from matplotlib.cm import ScalarMappable
from matplotlib.colors import LightSource, ListedColormap, Normalize
from matplotlib.ticker import FuncFormatter
from matplotlib_scalebar.scalebar import ScaleBar

from .rutas import FIGURAS

# ------------------------------------------------------------------------------------------ colores
AZUL, NARANJA, VINO, GRIS = '#1d3557', '#e8761a', '#a3245e', '#495057'

# Un color por fuente de U (se repite en mapas, tablas y gráficos)
COLORES_FUENTE = {'Litogeoquímica': AZUL, 'BDG 2022': NARANJA, 'GE27': '#1baf7a', 'IPEN': VINO, 'B-74': '#4a3aa7'}

HALO = [pe.withStroke(linewidth=3, foreground='white')]   # contorno blanco para rótulos sobre mapas

CMAP_CONTINUO = 'cmc.batlow'        # variables físicas continuas (gravedad)
CMAP_DIVERGENTE = 'cmc.vik'         # diferencias centradas en 0 (modelo - estación)

# Elevación: mitad superior de cmc.bukavu (la parte de tierra: verdes, ocres y blancos de cumbre)
CMAP_ELEVACION = ListedColormap(plt.get_cmap('cmc.bukavu')(np.linspace(0.5, 1, 256)), name='elevacion')

ESTILO = {
    'font.family': 'DejaVu Sans', 'font.size': 10,
    'axes.titlesize': 12, 'axes.titleweight': 'bold', 'axes.titlelocation': 'left', 'axes.titlepad': 9,
    'axes.titlecolor': AZUL, 'axes.labelsize': 10, 'axes.labelcolor': '#343a40',
    'xtick.labelsize': 9, 'ytick.labelsize': 9, 'xtick.color': GRIS, 'ytick.color': GRIS,
    'xtick.direction': 'in', 'ytick.direction': 'in', 'xtick.top': True, 'ytick.right': True,
    'axes.edgecolor': '#212529', 'axes.linewidth': 1.0,
    'axes.grid': True, 'grid.color': '#e9ecef', 'grid.linewidth': 0.7, 'axes.axisbelow': True,
    'legend.frameon': True, 'legend.framealpha': 0.92, 'legend.edgecolor': '#dee2e6', 'legend.fontsize': 9,
    'axes.formatter.min_exponent': 3,
    'figure.facecolor': 'white', 'savefig.facecolor': 'white', 'axes.facecolor': 'white',
    'svg.fonttype': 'none', 'svg.hashsalt': 'geocomp',        # SVG con texto editable y reproducible
    'axes.prop_cycle': cycler(color=[AZUL, NARANJA, '#1baf7a', VINO, '#4a3aa7', GRIS]),
}


def aplicar_estilo():
    """Aplica el estilo común de las figuras y crea la carpeta `figuras/`."""
    plt.rcParams.update(ESTILO)
    FIGURAS.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------------------------------------ números en español
def numero_es(x, d=1):
    """Número con coma decimal y sin separador de miles: 1740.5 da '1740,5'."""
    return f'{x:.{d}f}'.replace('.', ',')


def valor_p_es(p):
    """Valor p legible: 0.0312 da '0,031'; 4e-17 da '< 0,001'."""
    return '< 0,001' if p < 0.001 else numero_es(p, 3)


def texto_p(p):
    """Texto del valor p para un gráfico: 'p = 0,049' o 'p < 0,001'."""
    valor = valor_p_es(p)
    return f'p {valor}' if valor.startswith('<') else f'p = {valor}'


def ejes_coma_decimal(ax, x=True, y=True, d=None):
    """Rótulos de los ejes con coma decimal (también en ejes logarítmicos: 0,1 - 1 - 10 - 100 - 1000)."""
    def formato(v, _):
        dec = d if d is not None else (0 if float(v).is_integer() else 1)
        return numero_es(v, dec)
    if x:
        ax.xaxis.set_major_formatter(FuncFormatter(formato))
    if y:
        ax.yaxis.set_major_formatter(FuncFormatter(formato))


def cuadro_texto(ax, texto, x=0.97, y=0.04, ha='right', va='bottom'):
    """Recuadro blanco con estadísticos dentro de los ejes (x, y en fracción de los ejes)."""
    ax.text(x, y, texto, transform=ax.transAxes, ha=ha, va=va, fontsize=9, zorder=40,
            bbox=dict(boxstyle='round,pad=0.4', fc='white', ec='#ced4da', alpha=0.95))


# ------------------------------------------------------------------------------------------ mapas
def flecha_norte(ax, x=0.07, y=0.92):
    """Flecha del norte con halo blanco (se lee sobre cualquier fondo)."""
    ax.annotate('N', xy=(x, y), xytext=(x, y - 0.10), xycoords='axes fraction', ha='center', va='center',
                fontsize=13, fontweight='bold', zorder=40,
                path_effects=HALO,
                arrowprops=dict(facecolor='black', edgecolor='white', linewidth=1.2, width=3, headwidth=11,
                                headlength=11))


def escala(ax, lugar='lower right'):
    """Barra de escala gráfica (el mapa debe estar en metros: UTM)."""
    barra = ScaleBar(1, 'm', location=lugar, border_pad=1.2, pad=0.45, box_alpha=0.85, length_fraction=0.22,
                     font_properties={'size': 8}, scale_loc='top')
    barra.set_zorder(40)
    ax.add_artist(barra)


def marco_mapa(ax, aoi, titulo='', margen=4000, accesorios=True):
    """Mapa en UTM 18S: límite del área de estudio, grilla en km, norte y escala."""
    x0, y0, x1, y1 = aoi.total_bounds
    aoi.boundary.plot(ax=ax, color='black', lw=1.8, zorder=30)
    ax.set_xlim(x0 - margen, x1 + margen)
    ax.set_ylim(y0 - margen, y1 + margen)
    ax.set_aspect('equal')
    ax.grid(color='#adb5bd', lw=0.4, ls=':')
    km = FuncFormatter(lambda v, _: f'{v / 1000:.0f}')
    ax.xaxis.set_major_formatter(km)
    ax.yaxis.set_major_formatter(km)
    ax.tick_params(labelsize=8)
    ax.set_xlabel('Este (km, UTM 18S)')
    ax.set_ylabel('Norte (km, UTM 18S)')
    if titulo:
        ax.set_title(titulo)
    if accesorios:
        flecha_norte(ax)
        escala(ax)


def fuente_al_pie(ax, texto, y=-0.075):
    """Línea de fuente de los datos debajo de los ejes `ax` (y en fracción de la altura de los ejes)."""
    ax.text(0, y, texto, transform=ax.transAxes, fontsize=7.5, color=GRIS, ha='left', va='top')


def fuente_figura(fig, texto):
    """Línea de fuente de los datos al pie de una figura de varios paneles (debajo de todo, alineada a la izquierda)."""
    fig.text(0.01, -0.015, texto, fontsize=7.5, color=GRIS, ha='left', va='top')


def relieve(ax, elevacion, extension, opacidad=0.45):
    """Relieve sombreado en grises (luz del noroeste) como fondo de un mapa."""
    con_dato = np.isfinite(elevacion)
    z = np.where(con_dato, elevacion, np.nanmin(elevacion))
    paso = (extension[1] - extension[0]) / elevacion.shape[1]        # tamaño de celda en metros
    sombra = LightSource(azdeg=315, altdeg=45).hillshade(z, vert_exag=2, dx=paso, dy=paso)
    sombra = np.where(con_dato, sombra, np.nan)                  # fuera del DEM queda transparente
    ax.imshow(sombra, extent=extension, cmap='gray', vmin=0, vmax=1, alpha=opacidad, zorder=0,
              interpolation='bilinear')


def mapa_hipsometrico(ax, elevacion, extension, cmap=CMAP_ELEVACION, vmin=None, vmax=None):
    """Elevación en color con el sombreado fundido en el mismo píxel (no una capa gris semitransparente encima,
    que apaga los colores). Devuelve el objeto para dibujar la barra de color."""
    con_dato = np.isfinite(elevacion)
    vmin = np.nanmin(elevacion) if vmin is None else vmin
    vmax = np.nanmax(elevacion) if vmax is None else vmax
    z = np.where(con_dato, elevacion, vmin)
    paso = (extension[1] - extension[0]) / elevacion.shape[1]
    norma = Normalize(vmin, vmax)
    color = LightSource(azdeg=315, altdeg=45).shade(z, cmap=plt.get_cmap(cmap), norm=norma, blend_mode='soft',
                                                    vert_exag=1.5, dx=paso, dy=paso)
    color[~con_dato, 3] = 0                                         # fuera del DEM queda transparente
    ax.imshow(color, extent=extension, zorder=0, interpolation='bilinear')
    return ScalarMappable(norma, plt.get_cmap(cmap))


def mapa_ubicacion(ax, departamentos, aoi, resaltar=('JUNIN', 'PASCO')):
    """Mapa de ubicación: el Perú por departamentos, los de `resaltar` en gris oscuro y el área de estudio en rojo."""
    departamentos.plot(ax=ax, color='#e9ecef', edgecolor='white', linewidth=0.4)
    departamentos[departamentos.NM_DEPA.isin(resaltar)].plot(ax=ax, color='#adb5bd', edgecolor='white', linewidth=0.4)
    aoi.plot(ax=ax, color='#d62828', edgecolor='#d62828', linewidth=1.2, zorder=5)
    ax.set_aspect('equal')
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel('')
    ax.set_ylabel('')
    ax.grid(False)
    ax.set_facecolor('white')
    ax.text(0.95, 0.95, 'PERÚ', transform=ax.transAxes, ha='right', va='top', fontsize=8, fontweight='bold',
            color=GRIS)


def limites(ax, poligonos, **estilo):
    """Dibuja los límites de unos polígonos una sola vez: el borde compartido por dos polígonos vecinos no se
    duplica (dos líneas discontinuas superpuestas se ven como una línea continua)."""
    lineas = shapely.line_merge(poligonos.geometry.boundary.union_all())
    for parte in getattr(lineas, 'geoms', [lineas]):
        x, y = parte.xy
        ax.plot(x, y, **estilo)


def rotular_lugares(ax, puntos, campo, aoi, tamano=8.5, negrita=True, color='black', marcador=18, distancia=15_000):
    """Punto y nombre de cada lugar. Cerca del borde este del área el rótulo se escribe a la izquierda del punto
    para que no se corte."""
    puntos.plot(ax=ax, color=color, markersize=marcador, edgecolor='white', linewidth=0.6, zorder=10)
    borde_este = aoi.total_bounds[2] - distancia
    for x, y, nombre in zip(puntos.geometry.x, puntos.geometry.y, puntos[campo]):
        izquierda = x > borde_este
        ax.annotate(nombre, (x, y), xytext=(-5 if izquierda else 5, 4), textcoords='offset points',
                    ha='right' if izquierda else 'left', fontsize=tamano,
                    fontweight='bold' if negrita else 'normal', color=color, path_effects=HALO, zorder=11)


# ------------------------------------------------------------------------------------------ guardado
def guardar(fig, nombre, svg=False):
    """Guarda la figura en `figuras/` (PNG de 300 dpi y, si es un gráfico, también SVG editable) y la muestra."""
    fig.savefig(FIGURAS / nombre, dpi=300, bbox_inches='tight')
    if svg:
        fig.savefig(FIGURAS / Path(nombre).with_suffix('.svg'), bbox_inches='tight', metadata={'Date': None})
    plt.show()
