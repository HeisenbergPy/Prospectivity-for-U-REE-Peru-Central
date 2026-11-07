"""Portada animada del README (portada.svg).

Toma la portada fija (portada.png, exportada de diseno/portada.html) y le superpone, en SVG, pulsos de luz que recorren
las curvas de nivel del panel oscuro (las mismas que dibuja marco.py) y un brillo lento en la esquina morada. Los
pulsos no pasan sobre el título ni sobre los autores. GitHub muestra el SVG animado en el README; con «reducir
movimiento» activado en el sistema, queda fijo.

Uso, desde la carpeta del repositorio (después de exportar portada.png):
    uv run python recursos/animar_portada.py
"""

import base64
import importlib.util
import io
import random

from PIL import Image
from shapely.geometry import LineString, Polygon, box

from geocomp.rutas import RAIZ

RECURSOS = RAIZ / 'recursos'
E = 2                                                     # portada.png está a resolución 2x
ANCHO, ALTO = 1600 * E, 640 * E
BORDE = [(640, -10), (690, 370), (655, 450), (740, 560), (1330, 626), (1610, 520)]   # el de marco_portada.png
ESQUINA_X = 1330
TEXTOS = [box(110, 110, 1310, 960), box(110, 1010, 1470, 1140)]   # título y autores (px 2x): sin pulsos encima


def main():
    spec = importlib.util.spec_from_file_location('marco', RECURSOS / 'marco.py')
    marco = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(marco)
    lineas = marco.curvas(ANCHO, ALTO)

    random.seed(7)
    oscuro = Polygon([(x * E, y * E) for x, y in BORDE] + [(ANCHO + 40, ALTO + 40), (-40, ALTO + 40), (-40, -40)])
    zona = oscuro
    for t in TEXTOS:
        zona = zona.difference(t.buffer(24))
    '''Curvas con un recorrido largo fuera de los textos (las índice primero), simplificadas para que el SVG pese poco'''
    elegidas = []
    for nivel, pts in lineas:
        if len(pts) < 2:
            continue
        linea = LineString(pts)
        if linea.intersection(zona).length < 300:
            continue
        elegidas.append((nivel % marco.INDICE == 0, linea.simplify(1.2)))
    elegidas.sort(key=lambda t: (not t[0], -t[1].length))
    elegidas = [l for _, l in elegidas[:42]]

    rutas, usos = [], []
    for i, l in enumerate(elegidas):
        d = 'M' + ' L'.join(f'{x:.1f} {y:.1f}' for x, y in l.coords)
        rutas.append(f'<path id="c{i}" d="{d}" pathLength="1000"/>')
        dur = random.uniform(8, 14)
        retraso = -random.uniform(0, dur)
        tramo = random.choice([30, 40, 55])
        estilo = f'stroke-dasharray:{tramo} {1000 - tramo};animation-duration:{dur:.1f}s;animation-delay:{retraso:.1f}s'
        usos.append(f'<use href="#c{i}" class="brillo" style="{estilo}"/><use href="#c{i}" class="pulso" style="{estilo}"/>')

    '''Imagen fija incrustada (JPEG) para que el SVG sea un solo archivo'''
    buf = io.BytesIO()
    Image.open(RECURSOS / 'portada.png').convert('RGB').save(buf, 'JPEG', quality=86, optimize=True, progressive=True)
    fondo = base64.b64encode(buf.getvalue()).decode()

    anillos = []
    for g in getattr(zona, 'geoms', [zona]):
        anillos += [g.exterior, *g.interiors]
    contorno = ' '.join('M' + ' L'.join(f'{x:.0f} {y:.0f}' for x, y in a.coords) + ' Z' for a in anillos)
    x0 = ESQUINA_X * E
    esquina = f'{x0},{ALTO} {x0},{626 * E} {1610 * E},{520 * E} {ANCHO},{ALTO}'

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ANCHO} {ALTO}" width="1600" height="640" role="img" aria-label="Prospectivity for U - REE - Peru Central">
<style>
.brillo, .pulso {{ fill: none; stroke-linecap: round; animation-name: fluir; animation-timing-function: linear;
  animation-iteration-count: infinite; }}
.brillo {{ stroke: #b46cff; stroke-width: 9; opacity: 0.55; filter: url(#difuso); }}
.pulso {{ stroke: #f1e6ff; stroke-width: 2.6; opacity: 0.9; }}
@keyframes fluir {{ from {{ stroke-dashoffset: 1000; }} to {{ stroke-dashoffset: 0; }} }}
.esquina {{ fill: #e2c8ff; animation: respirar 6s ease-in-out infinite; }}
@keyframes respirar {{ 0%, 100% {{ opacity: 0; }} 50% {{ opacity: 0.22; }} }}
@media (prefers-reduced-motion: reduce) {{ .brillo, .pulso, .esquina {{ animation: none; opacity: 0; }} }}
</style>
<defs>
<filter id="difuso" x="-5%" y="-5%" width="110%" height="110%"><feGaussianBlur stdDeviation="6"/></filter>
<clipPath id="panel"><path clip-rule="evenodd" d="{contorno}"/></clipPath>
{''.join(rutas)}
</defs>
<image width="{ANCHO}" height="{ALTO}" href="data:image/jpeg;base64,{fondo}"/>
<g clip-path="url(#panel)">
{''.join(usos)}
</g>
<polygon class="esquina" points="{esquina}"/>
</svg>
'''
    salida = RECURSOS / 'portada.svg'
    salida.write_text(svg, encoding='utf-8')
    print(f'{len(elegidas)} curvas animadas; {salida.stat().st_size / 1e6:.2f} MB')


if __name__ == '__main__':
    main()
