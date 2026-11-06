"""Fondos de las imágenes del README con la estética de las presentaciones del proyecto: panel oscuro con curvas de
nivel reales del área (DEM Copernicus GLO-90 alrededor de San Ramón) en morado luminoso, línea gris biselada que lo
separa del área clara y esquina con degradado morado.

Genera en `recursos/imagenes/`:
    marco_portada.png      1600 × 640 (guardada al doble), para diseno/portada.html
    marco_vista_previa.png 1280 × 640 (guardada al doble), para diseno/vista_previa.html
    marco_perfil.png       1600 × 400 (guardada al doble), para el encabezado del perfil de GitHub

Uso, desde la carpeta del repositorio:
    uv run python recursos/marco.py
"""

import numpy as np
from contourpy import contour_generator
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage
from shapely.geometry import LineString, Polygon, box

from geocomp import espacial, lectura
from geocomp.rutas import ARCHIVOS, RAIZ

SALIDA = RAIZ / 'recursos' / 'imagenes'
SS = 2                                                   # sobremuestreo: curvas suaves
OSCURO, GRIS = (32, 31, 42), (190, 190, 200)
INTERVALO, INDICE = 50, 250


def curvas(ancho, alto, ancho_km=40.0, centro=(495_000, 8_775_000)):
    """Curvas de nivel en píxeles de la imagen: lista de (nivel, [(x, y), ...]). La ventana del DEM tiene la misma
    proporción que la imagen y queda dentro del área de estudio, al este de San Ramón (fuera del área el DEM del
    repositorio no tiene datos)."""
    aoi = lectura.cargar_aoi()
    dem, ext = espacial.raster_a_utm(ARCHIVOS['dem_90m'], aoi, celda=90, margen=0, metodo='bilineal')
    w, h = ancho_km * 1000, ancho_km * 1000 * alto / ancho
    c0 = int((centro[0] - w / 2 - ext[0]) / 90)
    f0 = int((ext[3] - centro[1] - h / 2) / 90)
    z = ndimage.gaussian_filter(np.nan_to_num(dem[f0:f0 + int(h / 90), c0:c0 + int(w / 90)], nan=1000.0), 2.0)
    ny, nx = z.shape
    gen = contour_generator(z=z)
    lineas = []
    for nivel in range(int(z.min() // INTERVALO + 1) * INTERVALO, int(z.max()), INTERVALO):
        for seg in gen.lines(nivel):
            if len(seg) >= 8:
                lineas.append((nivel, [(c / (nx - 1) * ancho, f / (ny - 1) * alto) for c, f in seg]))
    return lineas


def mascara(geom, ancho, alto):
    m = Image.new('L', (ancho * SS, alto * SS), 0)
    d = ImageDraw.Draw(m)
    for g in ([geom] if geom.geom_type == 'Polygon' else list(geom.geoms)):
        d.polygon([(x * SS, y * SS) for x, y in g.exterior.coords], fill=255)
    return m.resize((ancho, alto), Image.LANCZOS)


def dibujar(lineas, ancho, alto, menor, indice, ancho_m, ancho_i):
    capa = Image.new('RGBA', (ancho * SS, alto * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    for nivel, pts in lineas:
        es_indice = nivel % INDICE == 0
        d.line([(x * SS, y * SS) for x, y in pts], fill=indice if es_indice else menor,
               width=max(1, round((ancho_i if es_indice else ancho_m) * SS)), joint='curve')
    return capa.resize((ancho, alto), Image.LANCZOS)


def con_alfa(capa, mascara_l, factor=1.0):
    a = np.asarray(capa)[..., 3].astype(float) * (np.asarray(mascara_l) / 255) * factor
    capa.putalpha(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)))
    return capa


def marco(ancho, alto, borde, esquina, nombre, claro=(236, 237, 242), ancho_gris=9, e=2):
    """`borde`: línea (x, y) de arriba hacia la derecha que separa el panel oscuro (a su izquierda y debajo) del área
    clara; `esquina`: polígono que recorta del panel oscuro la esquina morada. Coordenadas en píxeles del diseño; la
    imagen se guarda `e` veces más grande, para las exportaciones de resolución 2x."""
    ancho, alto, ancho_gris = ancho * e, alto * e, ancho_gris * e
    borde = [(x * e, y * e) for x, y in borde]
    esquina = [(x * e, y * e) for x, y in esquina]
    lienzo = box(-20, -20, ancho + 20, alto + 20)
    linea = LineString(borde)
    oscuro = Polygon(borde + [(ancho + 20, alto + 20), (-20, alto + 20), (-20, -20)]).intersection(lienzo)
    a = linea.buffer(ancho_gris, single_sided=True, join_style=2, mitre_limit=10)
    b = linea.buffer(-ancho_gris, single_sided=True, join_style=2, mitre_limit=10)
    gris = (a if a.intersection(oscuro).area < b.intersection(oscuro).area else b).difference(oscuro)
    morado = oscuro.intersection(Polygon(esquina))
    oscuro = oscuro.difference(morado)
    m_osc, m_mor, m_gris = (mascara(g, ancho, alto) for g in (oscuro, morado, gris))
    lineas = curvas(ancho, alto)

    img = Image.new('RGBA', (ancho, alto), (*claro, 255))
    '''Panel oscuro con un degradado suave (más claro junto al borde)'''
    dist = ndimage.distance_transform_edt(np.asarray(m_osc) > 0)
    t = np.clip(dist / (160 * e), 0, 1)[..., None]
    rgb = np.array([46, 44, 60]) * (1 - t) + np.array(OSCURO) * t
    img.paste(Image.fromarray(np.dstack([rgb, np.full((alto, ancho), 255)]).astype(np.uint8), 'RGBA'), (0, 0), m_osc)
    '''Curvas luminosas: resplandor violeta debajo y la línea encima; las índice, casi blancas'''
    peso = Image.fromarray((np.clip(0.28 + dist / (340 * e), 0.28, 0.62) * np.asarray(m_osc)).astype(np.uint8))
    brillo = dibujar(lineas, ancho, alto, (130, 60, 230, 255), (165, 100, 245, 255), 2.2 * e, 3.4 * e)
    img = Image.alpha_composite(img, con_alfa(brillo.filter(ImageFilter.GaussianBlur(5 * e)), peso, 0.3))
    img = Image.alpha_composite(img, con_alfa(dibujar(lineas, ancho, alto, (150, 85, 250, 255),
                                                      (195, 150, 255, 255), 0.8 * e, 1.5 * e), peso))
    '''Esquina morada con degradado y curvas en lavanda'''
    yy, xx = np.mgrid[0:alto, 0:ancho].astype(np.float32)
    x0, y0 = min(p[0] for p in esquina), min(p[1] for p in esquina)
    t = np.clip(((xx - x0) / max(ancho - x0, 1)) * 0.7 + (1 - (yy - y0) / max(alto - y0, 1)) * 0.3, 0, 1)[..., None]
    rgb = np.array([62, 0, 140]) * (1 - t) + np.array([156, 82, 255]) * t
    img.paste(Image.fromarray(np.dstack([rgb, np.full((alto, ancho), 255)]).astype(np.uint8), 'RGBA'), (0, 0), m_mor)
    img = Image.alpha_composite(img, con_alfa(dibujar(lineas, ancho, alto, (228, 205, 255, 150),
                                                      (240, 228, 255, 200), 0.8 * e, 1.4 * e), m_mor))
    '''Línea gris de grosor constante y sombra suave sobre el área clara'''
    sombra = mascara(oscuro.union(morado).union(gris), ancho, alto).filter(ImageFilter.GaussianBlur(10 * e))
    capa_s = Image.new('RGBA', (ancho, alto), (20, 10, 40, 0))
    capa_s.putalpha(Image.fromarray((np.asarray(sombra) * 0.3).astype(np.uint8)))
    base = Image.new('RGBA', (ancho, alto), (*claro, 255))
    base = Image.alpha_composite(base, capa_s)
    base.paste(img, (0, 0), Image.fromarray(np.maximum(np.asarray(m_osc), np.asarray(m_mor))))
    base.paste(Image.new('RGBA', (ancho, alto), (*GRIS, 255)), (0, 0), m_gris)
    base.convert('RGB').save(SALIDA / nombre, optimize=True)
    print(nombre, base.size)


if __name__ == '__main__':
    SALIDA.mkdir(parents=True, exist_ok=True)
    marco(1600, 640, [(640, -10), (690, 370), (655, 450), (740, 560), (1330, 626), (1610, 520)],
          [(1330, -20), (1620, -20), (1620, 660), (1330, 660)], 'marco_portada.png')
    marco(1280, 640, [(560, -10), (610, 370), (575, 450), (650, 560), (1060, 626), (1290, 530)],
          [(1060, -20), (1300, -20), (1300, 660), (1060, 660)], 'marco_vista_previa.png')
    marco(1600, 400, [(720, -10), (760, 230), (735, 290), (800, 350), (1380, 390), (1610, 318)],
          [(1380, -20), (1620, -20), (1620, 420), (1380, 420)], 'marco_perfil.png')
