"""Lectura de las capas y conversión de la química a números.

INGEMMET entrega la química como TEXTO: '<2.00' (debajo del límite de detección), '########' (valor perdido en la
fuente), '0' (no determinado) o 'N.R' (no reportado). Antes de comparar fuentes hay que convertir esos textos con
reglas explícitas; `leer_valor` las reúne en un solo lugar.
"""

import re

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio

from .rutas import ARCHIVOS, CRS_UTM

# Nombre corto de cada fuente de U (se usa en tablas, leyendas y colores)
FUENTES_U = ['Litogeoquímica', 'BDG 2022', 'GE27', 'IPEN', 'B-74']

# Proyectos de BDG 2022 con digestión ácida parcial (no disuelve el circón): se marcan para no mezclarlos a ciegas
BDG_DIGESTION_PARCIAL = ('GE33-B6', 'GE33B-5')

# Una muestra con Cu, Pb o Zn por encima de este valor (ppm) es mena, no roca de caja
UMBRAL_MENA_PPM = 1000

_NUMERO = re.compile(r'^-?\d+(?:[.,]\d+)?(?:[eE][+-]?\d+)?$')
_MILES = re.compile(r'^-?\d{1,3}(?:,\d{3})+$')        # '1,000' o '10,000': ¿coma decimal o de miles?
_ANIO = re.compile(r'(19[5-9]\d|20[0-2]\d)')


# ------------------------------------------------------------------------------------------ texto a número
def leer_valor(v):
    """Interpreta un valor químico tal como lo entrega la fuente.

    Devuelve una tupla (valor, estado, limite):
        'numero'   valor medido
        '<LD'      debajo del límite de detección (limite = LD); un número negativo también significa "< |valor|"
        '>LS'      sobre el límite superior de medición
        'perdido'  '########': el valor se perdió en la fuente
        'cero'     0: en una roca no es físico; significa "no determinado"
        'vacio'    sin dato ('', 'N.R', '-', nulo)
        'ambiguo'  texto que no se puede interpretar con seguridad, p. ej. '1,000' (¿1 o 1000?) o '2.5 ppm'
    """
    if v is None or (not isinstance(v, str) and pd.isna(v)):
        return np.nan, 'vacio', np.nan
    if isinstance(v, (int, float, np.integer, np.floating)):
        texto = repr(float(v))
    else:
        texto = str(v).strip().replace(' ', '')
    if texto in ('', 'nan', 'None', '-') or texto.upper().startswith('N.R'):
        return np.nan, 'vacio', np.nan
    if set(texto) == {'#'}:
        return np.nan, 'perdido', np.nan
    if texto[0] in '<>':
        limite = pd.to_numeric(texto[1:].replace(',', '.'), errors='coerce')
        return np.nan, '<LD' if texto[0] == '<' else '>LS', float(limite)
    if _MILES.match(texto):
        return np.nan, 'ambiguo', np.nan
    if _NUMERO.match(texto):
        x = float(texto.replace(',', '.'))
        if x < 0:
            return np.nan, '<LD', -x
        return (np.nan, 'cero', np.nan) if x == 0 else (x, 'numero', np.nan)
    return np.nan, 'ambiguo', np.nan


def a_numero(serie):
    """Convierte una columna de texto químico en números; lo que no es un valor medido queda como NaN."""
    return pd.Series([leer_valor(v)[0] for v in serie], index=serie.index, dtype=float)


def estado(serie):
    """Estado de cada valor de una columna química ('numero', '<LD', 'perdido', 'cero', 'vacio'...)."""
    return pd.Series([leer_valor(v)[1] for v in serie], index=serie.index)


def anio_en_texto(texto):
    """Primer año (1950–2029) que aparece en un texto, p. ej. 'Soler (1991)' da 1991; si no hay, NaN."""
    m = _ANIO.search(str(texto))
    return float(m.group(1)) if m else np.nan


# ------------------------------------------------------------------------------------------ capas
def describir(ruta):
    """Ficha de un archivo geoespacial: tipo, formato, sistema de coordenadas, tamaño y resolución (si es ráster)."""
    if str(ruta).lower().endswith('.tif'):
        with rasterio.open(ruta) as src:
            unidad = '°' if src.crs.is_geographic else ' m'
            return {'tipo': 'ráster', 'formato': 'GeoTIFF', 'crs': src.crs.to_string(),
                    'tamaño': f'{src.width} × {src.height} celdas', 'resolución': f'{src.res[0]:g}{unidad}'}
    capa = gpd.read_file(ruta)
    return {'tipo': 'vector', 'formato': 'Shapefile', 'crs': capa.crs.to_string(),
            'tamaño': f'{len(capa)} {"puntos" if capa.geom_type.iloc[0] == "Point" else "polígonos"}',
            'resolución': '—'}


def cargar_capa(nombre, crs=CRS_UTM):
    """Lee una capa de `datos/` por su nombre en `rutas.ARCHIVOS` y la lleva al sistema de trabajo (UTM 18S)."""
    return gpd.read_file(ARCHIVOS[nombre]).to_crs(crs)


def cargar_aoi(crs=CRS_UTM):
    """Área de estudio: rectángulo de 110 × 140 km en la Cordillera Oriental de Junín y Pasco."""
    return cargar_capa('aoi', crs)


def cargar_gravedad_estaciones(crs=CRS_UTM):
    """Estaciones gravimétricas de INGEMMET con la anomalía de Bouguer (mGal) y la gravedad observada."""
    capa = cargar_capa('gravedad_estaciones', crs)
    return capa.rename(columns={'BOUG_MGAL': 'bouguer_mgal', 'GRAV_MGAL': 'gravedad_mgal'})[
        ['OBJECTID', 'bouguer_mgal', 'gravedad_mgal', 'geometry']]


def cargar_sedimentos(crs=CRS_UTM):
    """Sedimentos de quebrada de INGEMMET con Be, La e Y en ppm (en el área de estudio no traen U ni Th)."""
    capa = cargar_capa('sedimentos', crs)
    tabla = pd.DataFrame({f'{e}_ppm': a_numero(capa[f'{e.upper()}_PPM']) for e in ('Be', 'La', 'Y')})
    return gpd.GeoDataFrame(tabla, geometry=capa.geometry, crs=capa.crs)


def _es_mena(capa, columnas):
    """True si alguna de las columnas de metales base supera el umbral de mena."""
    metales = pd.concat([a_numero(capa[c]) for c in columnas if c in capa], axis=1)
    return metales.gt(UMBRAL_MENA_PPM).any(axis=1)


def cargar_uranio(crs=CRS_UTM):
    """Une las cinco fuentes de U en roca en una sola tabla con columnas comunes.

    Columnas: fuente, codigo, U_ppm, estado_U, Th_ppm, SiO2_pct, anio, metodo, es_mena y geometry.
    Se conservan todas las filas (también las que no tienen U medido) para poder contar la cobertura de cada fuente.
    Se excluye lo que no es roca: los suelos del GE27 (uno llega a 10 000 ppm, con posible pechblenda) y el mineral
    de torbernita del IPEN. Del B-74 solo se toman las rocas que están dentro del área de estudio.
    `es_mena` marca las muestras con Cu, Pb o Zn > 1000 ppm en las fuentes que miden esos metales (litogeoquímica y
    BDG 2022); GE27, IPEN y B-74 no los miden, así que allí queda en False.
    Se eliminan los duplicados exactos: misma fuente, mismo código, mismo U y mismo lugar (a 1 m).
    """
    partes = []

    # Litogeoquímica de INGEMMET (incluye datos publicados; el año sale de la referencia, si la tiene)
    c = cargar_capa('litogeoquimica', crs)
    partes.append(pd.DataFrame({
        'fuente': 'Litogeoquímica', 'codigo': c['CODIGO'].astype(str), 'U_txt': c['U'], 'Th_ppm': a_numero(c['TH']),
        'SiO2_pct': a_numero(c['SIO2']), 'anio': c['QUIMICA_RE'].map(anio_en_texto),
        'metodo': 'fusión (mayoritaria)', 'es_mena': _es_mena(c, ['CU', 'PB', 'ZN']), 'geometry': c.geometry}))

    # BDG 2022: el U por fusión ("_ROCA") tiene prioridad sobre el multielemento por digestión
    c = cargar_capa('bdg_2022', crs)
    u_txt = c['U_PPM_ROCA'].where(c['U_PPM_ROCA'].notna(), c['U_PPM'])
    th_txt = c['TH_PPM_ROC'].where(c['TH_PPM_ROC'].notna(), c['TH_PPM'])
    metodo = np.where(c['U_PPM_ROCA'].notna(), 'fusión',
                      np.where(c['PROY'].isin(BDG_DIGESTION_PARCIAL), 'digestión parcial', 'digestión total'))
    partes.append(pd.DataFrame({
        'fuente': 'BDG 2022', 'codigo': c['CD_MTRA'].astype(str), 'U_txt': u_txt, 'Th_ppm': a_numero(th_txt),
        'SiO2_pct': a_numero(c['SIO2_PCT']),
        'anio': pd.to_datetime(c['F_MTRA'], unit='ms', errors='coerce').dt.year.astype(float),
        'metodo': metodo, 'es_mena': _es_mena(c, ['CU_PPM', 'PB_PPM', 'ZN_PPM', 'ZN_PPM_ROC', 'CU_PPM_MEN',
                                                  'PB_PPM_MEN', 'ZN_PPM_MEN']),
        'geometry': c.geometry}))

    # GE27: proyecto de materias primas críticas de INGEMMET (solo U); se excluyen los suelos
    c = cargar_capa('ge27', crs)
    c = c[~c['GEOLOG_A'].str.startswith('Suelo')]
    partes.append(pd.DataFrame({
        'fuente': 'GE27', 'codigo': c['C_DIGO'].astype(str), 'U_txt': c['U_PPM'], 'Th_ppm': np.nan,
        'SiO2_pct': np.nan, 'anio': c['A_O'].astype(float), 'metodo': 'fusión (peróxido de sodio)',
        'es_mena': False, 'geometry': c.geometry}))

    # IPEN: rocas de San Ramón (se excluye la torbernita, que es un mineral de U)
    c = cargar_capa('ipen', crs)
    c = c[c['MATERIAL'].eq('roca')]
    partes.append(pd.DataFrame({
        'fuente': 'IPEN', 'codigo': c['CODIGO'].astype(str), 'U_txt': c['U_PPM'], 'Th_ppm': a_numero(c['TH_PPM']),
        'SiO2_pct': np.nan, 'anio': c['FUENTE'].map(anio_en_texto), 'metodo': c['METODO'],
        'es_mena': False, 'geometry': c.geometry}))

    # Boletín B-74 (Carpio et al., 2021): solo las rocas dentro del área de estudio
    c = cargar_capa('b74', crs)
    c = c[c['EN_AOI'].eq('SI')]
    partes.append(pd.DataFrame({
        'fuente': 'B-74', 'codigo': c['CODIGO'].astype(str), 'U_txt': c['U_PPM'], 'Th_ppm': a_numero(c['TH_PPM']),
        'SiO2_pct': np.nan, 'anio': 2021.0, 'metodo': 'digestión sin HF', 'es_mena': False, 'geometry': c.geometry}))

    tabla = pd.concat(partes, ignore_index=True)

    # Duplicados exactos (la misma muestra cargada dos veces en la fuente)
    puntos = gpd.GeoSeries(tabla['geometry'])
    lugar = pd.DataFrame({'x': puntos.x.round(), 'y': puntos.y.round()})
    repetida = pd.concat([tabla[['fuente', 'codigo', 'U_txt']].astype(str), lugar], axis=1).duplicated()
    tabla = tabla[~repetida].reset_index(drop=True)

    tabla['U_ppm'] = a_numero(tabla['U_txt'])
    tabla['estado_U'] = estado(tabla['U_txt'])
    columnas = ['fuente', 'codigo', 'U_ppm', 'estado_U', 'Th_ppm', 'SiO2_pct', 'anio', 'metodo', 'es_mena',
                'geometry']
    return gpd.GeoDataFrame(tabla[columnas], geometry='geometry', crs=crs)
