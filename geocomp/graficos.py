"""Estilo de las figuras y elementos de los mapas (norte, escala, grilla en km), con números en formato español."""

from pathlib import Path

import cmcrameri  # noqa: F401  (registra los mapas de color científicos 'cmc.*')
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shapely
from cycler import cycler
from matplotlib.cm import ScalarMappable
from matplotlib.colors import LightSource, ListedColormap, Normalize, to_rgb
from matplotlib.ticker import FuncFormatter, NullFormatter
from matplotlib.transforms import ScaledTranslation
from matplotlib_scalebar.scalebar import ScaleBar
from scipy.stats import gaussian_kde

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


# ------------------------------------------------------------------------------------------ diagramas geoquímicos
# Lenguaje común de los diagramas: referencias publicadas rotuladas sobre el gráfico (en cursiva y con su cita),
# campos interpretativos en gris claro, cada fuente como una región que encierra el 50 % de sus rocas y su mediana
# como símbolo grande con la cruz Q1-Q3.
TINTA = '#212529'              # marco, marcas y textos fuertes
COLOR_REF = '#5c677d'          # líneas de referencia (no compite con los colores de las fuentes)
COLOR_CAMPO = '#adb5bd'        # nombres de los campos interpretativos
COLOR_BANDA = '#f4a261'        # bandas de referencia (ámbar suave)
MARCADOR_FUENTE = {'Litogeoquímica': 'o', 'BDG 2022': 'D', 'GE27': 's', 'IPEN': '^', 'B-74': 'v'}

# Composición de referencia (ppm): corteza continental superior (Rudnick y Gao, 2003)
CCS = {'U': 2.7, 'Th': 10.5}


def oscurecer(color, f=0.35):
    """El mismo color, más oscuro (f = 0 no cambia; f = 1 es negro)."""
    r, g, b = to_rgb(color)
    return (r * (1 - f), g * (1 - f), b * (1 - f))


def letra(ax, texto):
    """Letra de panel en una pastilla oscura, a la izquierda del título."""
    ax.text(-0.02, 1.02, texto, transform=ax.transAxes, ha='right', va='bottom', fontsize=11, fontweight='bold',
            color='white', bbox=dict(boxstyle='round,pad=0.28', fc=TINTA, ec='none'), zorder=20)


def marco(ax):
    """Marco completo y nítido, marcas hacia dentro y rejilla muy suave."""
    for lado in ('top', 'right', 'bottom', 'left'):
        ax.spines[lado].set_visible(True)
        ax.spines[lado].set_color(TINTA)
        ax.spines[lado].set_linewidth(1.1)
    ax.tick_params(which='both', direction='in', top=True, right=True, colors=TINTA, labelcolor='#343a40')
    ax.tick_params(which='major', length=5, width=0.9)
    ax.tick_params(which='minor', length=2.5, width=0.6)
    ax.grid(True, which='major', color='#e9ecef', lw=0.6, zorder=0)
    ax.set_axisbelow(True)


def ejes_log_planos(ax, eje='both'):
    """Números planos con coma decimal en ejes logarítmicos (0,1 - 1 - 10 - 100), como es costumbre en geoquímica."""
    formato = FuncFormatter(lambda v, _: f'{v:g}'.replace('.', ','))
    for nombre in (('x', 'y') if eje == 'both' else (eje,)):
        eje_mpl = ax.xaxis if nombre == 'x' else ax.yaxis
        eje_mpl.set_major_formatter(formato)
        eje_mpl.set_minor_formatter(NullFormatter())


def linea_ref(ax, y, texto='', pos=0.985, lado='arriba', ls=(0, (5, 3)), color=COLOR_REF, lw=1.1):
    """Línea horizontal de referencia con su rótulo en cursiva sobre la propia línea."""
    ax.axhline(y, color=color, ls=ls, lw=lw, zorder=1.5)
    if texto:
        ax.annotate(texto, xy=(pos, y), xycoords=('axes fraction', 'data'), ha='right' if pos > 0.5 else 'left',
                    va='bottom' if lado == 'arriba' else 'top', fontsize=8, style='italic', color=color,
                    xytext=(0, 2 if lado == 'arriba' else -2), textcoords='offset points', zorder=12,
                    bbox=dict(boxstyle='round,pad=0.15', fc='white', ec='none', alpha=0.8))


def banda_ref(ax, y0, y1, texto, pos=0.015):
    """Banda horizontal de referencia (un rango publicado) con su rótulo dentro."""
    ax.axhspan(y0, y1, color=COLOR_BANDA, alpha=0.16, lw=0, zorder=0.5)
    y_medio = np.sqrt(y0 * y1) if ax.get_yscale() == 'log' else (y0 + y1) / 2
    ax.annotate(texto, xy=(pos, y_medio), xycoords=('axes fraction', 'data'), ha='left' if pos < 0.5 else 'right',
                va='center', fontsize=8, style='italic', color='#9c4a00', path_effects=HALO, zorder=6)


def campo(ax, x, y, texto, ha='center', color=COLOR_CAMPO, tamano=9.5):
    """Nombre de un campo interpretativo escrito sobre el gráfico (x, y en fracción de los ejes)."""
    ax.text(x, y, texto, transform=ax.transAxes, ha=ha, va='center', fontsize=tamano, style='italic',
            fontweight='bold', color=color, path_effects=HALO, zorder=1.2)


def razon_constante(ax, r, texto, x_texto, ls='-', color=COLOR_REF, lw=0.9):
    """Recta y = r·x en ejes log-log (Th/U constante) con el rótulo girado según su pendiente en pantalla.
    Se llama después de fijar las escalas y los límites."""
    x0, x1 = ax.get_xlim()
    xs = np.logspace(np.log10(x0), np.log10(x1), 50)
    ax.plot(xs, r * xs, color=color, ls=ls, lw=lw, zorder=1.5)
    p1, p2 = ax.transData.transform([(x_texto, r * x_texto), (x_texto * 2, r * x_texto * 2)])
    angulo = np.degrees(np.arctan2(p2[1] - p1[1], p2[0] - p1[0]))
    ax.text(x_texto, r * x_texto, texto, rotation=angulo, rotation_mode='anchor', ha='left', va='bottom',
            fontsize=8, style='italic', color=color, path_effects=HALO, zorder=6, transform_rotates_text=False)


def punto_ref(ax, x, y, texto, dx=6, dy=4, tamano=230):
    """Composición de referencia (p. ej., la corteza continental superior) como estrella con su nombre."""
    ax.scatter([x], [y], marker='*', s=tamano, color='#ffd166', edgecolor='k', lw=0.9, zorder=8)
    ax.annotate(texto, xy=(x, y), xytext=(dx, dy), textcoords='offset points', fontsize=8, fontweight='bold',
                color='#343a40', path_effects=HALO, zorder=9)


def densidad(ax, x, y, color, rango, logx=False, logy=False, nivel=0.5, n=180, alpha=0.28):
    """Región que encierra el 50 % de las rocas de una fuente: la zona de mayor densidad de una estimación de núcleo
    gaussiana, calculada en el espacio del eje (logarítmico si el eje lo es). `rango` = (x0, x1, y0, y1).
    Con menos de 8 rocas no se dibuja, porque la estimación no sería estable."""
    d = pd.DataFrame({'x': np.asarray(x, float), 'y': np.asarray(y, float)}).dropna()
    if logx:
        d = d[d.x > 0]
    if logy:
        d = d[d.y > 0]
    if len(d) < 8:
        return
    tx = np.log10(d.x.values) if logx else d.x.values
    ty = np.log10(d.y.values) if logy else d.y.values
    nucleo = gaussian_kde(np.vstack([tx, ty]))
    x0, x1, y0, y1 = rango
    gx = np.linspace(np.log10(x0) if logx else x0, np.log10(x1) if logx else x1, n)
    gy = np.linspace(np.log10(y0) if logy else y0, np.log10(y1) if logy else y1, n)
    XX, YY = np.meshgrid(gx, gy)
    Z = nucleo(np.vstack([XX.ravel(), YY.ravel()])).reshape(XX.shape)
    umbral = np.quantile(nucleo(np.vstack([tx, ty])), 1 - nivel)      # densidad que deja dentro el 50 % de las rocas
    PX = 10 ** XX if logx else XX
    PY = 10 ** YY if logy else YY
    ax.contourf(PX, PY, Z, levels=[umbral, Z.max() * 1.01], colors=[color], alpha=alpha, zorder=1.1)
    ax.contour(PX, PY, Z, levels=[umbral], colors=[oscurecer(color, 0.12)], linewidths=1.6, zorder=1.3)


def mediana(ax, x, y, color, marcador='o', tamano=11, desplazamiento=0):
    """Mediana de una fuente: símbolo grande con borde negro y cruz Q1-Q3 (resumen robusto de la nube).

    `desplazamiento` (en puntos) corre el símbolo en horizontal solo para que no tape a otra mediana casi igual; el
    valor representado no cambia.
    """
    x, y = pd.Series(x).dropna(), pd.Series(y).dropna()
    if len(x) < 3 or len(y) < 3:
        return
    antes = set(ax.lines) | set(ax.collections)
    mx, my = x.median(), y.median()
    error_x = [[mx - x.quantile(0.25)], [x.quantile(0.75) - mx]]
    error_y = [[my - y.quantile(0.25)], [y.quantile(0.75) - my]]
    ax.errorbar(mx, my, xerr=error_x, yerr=error_y, fmt='none', ecolor='white', elinewidth=4.2, capsize=0, zorder=8.5)
    ax.errorbar(mx, my, xerr=error_x, yerr=error_y, fmt='none', ecolor=oscurecer(color, 0.15), elinewidth=2,
                capsize=4, capthick=1.6, zorder=8.6)
    ax.plot(mx, my, marker=marcador, ms=tamano, mfc=color, mec=TINTA, mew=1.4, ls='', zorder=9,
            path_effects=[pe.withStroke(linewidth=3.5, foreground='white')])
    if desplazamiento:
        corrimiento = ScaledTranslation(desplazamiento / 72, 0, ax.figure.dpi_scale_trans)
        for artista in [a for a in list(ax.lines) + list(ax.collections) if a not in antes]:
            artista.set_transform(artista.get_transform() + corrimiento)


# ------------------------------------------------------------------------------------------ guardado
def guardar(fig, nombre, svg=False):
    """Guarda la figura en `figuras/` (PNG de 300 dpi y, si es un gráfico, también SVG editable) y la muestra."""
    fig.savefig(FIGURAS / nombre, dpi=300, bbox_inches='tight')
    if svg:
        fig.savefig(FIGURAS / Path(nombre).with_suffix('.svg'), bbox_inches='tight', metadata={'Date': None})
    plt.show()
