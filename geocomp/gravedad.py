"""Gravedad: síntesis armónica del modelo global XGM2019e y reducción de las estaciones de INGEMMET.

Un modelo global de gravedad se publica como coeficientes de armónicos esféricos (archivo `.gfc` de ICGEM). Para
obtener la anomalía en un lugar se suman todos los términos hasta el grado máximo (2190 en XGM2019e):

    Δg = GM/r² Σn (n − 1) (a/r)^n Σm P̄nm(sen ψ) [ΔC̄nm cos mλ + S̄nm sen mλ]

donde ψ es la latitud geocéntrica, r la distancia al centro de la Tierra, P̄nm las funciones de Legendre
totalmente normalizadas y ΔC̄nm los coeficientes del modelo menos los del campo normal GRS80 (Barthelmes, 2013,
ec. 107). La anomalía de Bouguer simple resta la placa de topografía: Δg_B = Δg − 2πGρH (ec. 126), con H del
modelo de topografía etopo1-2250 truncado al mismo grado.

La suma se hace grado por grado: en cada grado n se calculan a la vez todas las órdenes m con la recursión
estándar de las funciones de Legendre, así que el bucle de Python tiene solo 2191 vueltas.
"""

import numpy as np
import pandas as pd

# ------------------------------------------------------------------------------------------ constantes
G = 6.67428e-11                     # constante de gravitación (m³ kg⁻¹ s⁻²), la que usa ICGEM
RHO_CORTEZA = 2670.0                # densidad de la placa de Bouguer en tierra (kg/m³)
RHO_AGUA_CORTEZA = 1645.0           # densidad equivalente bajo el mar (2670 − 1025)
MGAL = 1e5                          # 1 m/s² = 100 000 mGal

# Elipsoide y campo normal GRS80 (Moritz, 1980)
GRS80 = {'a': 6378137.0, 'GM': 3.986005e14, 'J2': 1.08263e-3, 'e2': 0.00669438002290, 'f': 1 / 298.257222101}

# Gradientes de la reducción de las estaciones (mGal/m)
GRADIENTE_AIRE_LIBRE = 0.3086
GRADIENTE_PLACA = 2 * np.pi * G * RHO_CORTEZA * MGAL        # 0,1120 mGal/m con ρ = 2670 kg/m³


# ------------------------------------------------------------------------------------------ lectura del modelo
def leer_gfc(ruta, grado_max=None):
    """Lee un archivo `.gfc` de ICGEM y devuelve (C, S, cabecera).

    C y S son matrices de (N + 1) × (N + 1) indexadas por [n, m]. La cabecera trae, entre otros, `radius`,
    `earth_gravity_constant` (solo en modelos de gravedad) y `max_degree`. Si se da `grado_max`, el modelo se trunca
    a ese grado al leerlo.
    """
    cabecera, n_cabecera, columnas = {}, 0, 5
    with open(ruta, encoding='latin-1') as f:
        for n_cabecera, linea in enumerate(f, 1):
            if linea.startswith('end_of_head'):
                break
            partes = linea.split()
            if len(partes) >= 2:
                cabecera[partes[0]] = partes[1]
            if partes and partes[0] == 'key':
                columnas = len(partes)                      # 'key L M C S' o 'key L M C S sigma C sigma S'
                columnas = 7 if columnas > 5 else 5
    for clave in ('radius', 'earth_gravity_constant'):
        if clave in cabecera:
            cabecera[clave] = float(cabecera[clave])
    cabecera['max_degree'] = int(cabecera['max_degree'])

    # Columnas: clave, n, m, C, S (y los errores, si el modelo los trae). Los modelos de topografía omiten S cuando
    # m = 0, así que se nombran todas las columnas de la línea 'key': si no, pandas toma el número de columnas de la
    # primera línea de datos y pierde S
    nombres = ['clave', 'n', 'm', 'C', 'S', 'sigma_C', 'sigma_S'][:columnas]
    tabla = pd.read_csv(ruta, skiprows=n_cabecera, sep=r'\s+', header=None, names=nombres,
                        usecols=['n', 'm', 'C', 'S'], dtype={'n': np.int32, 'm': np.int32}, engine='c')
    tabla['S'] = tabla['S'].fillna(0.0)
    N = cabecera['max_degree'] if grado_max is None else min(grado_max, cabecera['max_degree'])
    tabla = tabla[tabla.n <= N]
    C, S = np.zeros((N + 1, N + 1)), np.zeros((N + 1, N + 1))
    C[tabla.n, tabla.m] = tabla.C
    S[tabla.n, tabla.m] = tabla.S
    cabecera['grado'] = N
    return C, S, cabecera


def restar_campo_normal(C, cabecera, normal=GRS80):
    """Coeficientes perturbadores ΔC̄ = C̄ − C̄(normal): se restan el término central y los zonales pares J2…J20 del
    elipsoide, expresados con la GM y el radio del modelo (así lo hace ICGEM)."""
    dC = C.copy()
    escala_gm = normal['GM'] / cabecera['earth_gravity_constant']
    dC[0, 0] -= escala_gm                                          # término de grado cero
    e2, J2 = normal['e2'], normal['J2']
    for k in range(1, 11):                                         # n = 2k = 2, 4, …, 20
        n = 2 * k
        if n >= C.shape[0]:
            break
        J2n = (-1) ** (k + 1) * 3 * e2 ** k / ((2 * k + 1) * (2 * k + 3)) * (1 - k + 5 * k * J2 / e2)
        dC[n, 0] += J2n / np.sqrt(4 * k + 1) * escala_gm * (normal['a'] / cabecera['radius']) ** n
    return dC


# ------------------------------------------------------------------------------------------ coordenadas
def geocentricas(lat, lon, h=0.0, elipsoide=GRS80):
    """Latitud geodésica (grados), longitud y altura sobre el elipsoide (m) → latitud geocéntrica ψ (rad),
    longitud λ (rad) y radio r (m)."""
    lat, h = np.radians(np.asarray(lat, float)), np.asarray(h, float)
    a, e2 = elipsoide['a'], elipsoide['e2']
    N = a / np.sqrt(1 - e2 * np.sin(lat) ** 2)                     # radio de curvatura en el primer vertical
    p = (N + h) * np.cos(lat)                                      # distancia al eje de rotación
    z = (N * (1 - e2) + h) * np.sin(lat)
    return np.arctan2(z, p), np.radians(np.asarray(lon, float)), np.hypot(p, z)


# ------------------------------------------------------------------------------------------ síntesis
def _filas_legendre(psi, N):
    """Genera, para n = 0…N, la fila P̄n,m(sen ψ) de m = 0…n (matriz de (n + 1) × puntos).

    Recursión por grado: P̄n,m = a·t·P̄n−1,m − b·P̄n−2,m para m < n, y la sectorial P̄n,n = u·√((2n+1)/2n)·P̄n−1,n−1.
    En la latitud del Perú (u = cos ψ ≈ 0,98) no hay subdesbordamiento hasta el grado 2190.
    """
    t, u = np.sin(psi), np.cos(psi)
    anterior2 = None
    anterior = np.ones((1, t.size))
    yield anterior
    if N == 0:
        return
    anterior2, anterior = anterior, np.vstack([np.sqrt(3) * t, np.sqrt(3) * u])
    yield anterior
    for n in range(2, N + 1):
        m = np.arange(n)[:, None]
        a = np.sqrt((2 * n - 1) * (2 * n + 1) / ((n - m) * (n + m)))
        b = np.sqrt((2 * n + 1) * (n + m - 1) * (n - m - 1) / ((n - m) * (n + m) * (2 * n - 3)))
        previa2 = np.vstack([anterior2, np.zeros((1, t.size))])        # P̄n−2,n−1 = 0
        fila = np.empty((n + 1, t.size))
        fila[:n] = a * t * anterior - b * previa2
        fila[n] = u * np.sqrt((2 * n + 1) / (2 * n)) * anterior[n - 1]
        anterior2, anterior = anterior, fila
        yield fila


def _factor_grado(n, r, radio, funcional):
    """Factor radial del grado n según el funcional: anomalía de gravedad, potencial perturbador o superficie."""
    if funcional == 'anomalia':                       # Δg en aproximación esférica: (n − 1) (a/r)^n
        return (n - 1) * (radio / r) ** n
    if funcional == 'potencial':                      # T: (a/r)^n
        return (radio / r) ** n
    return 1.0                                        # función de superficie (topografía): sin factor radial


def _escala_funcional(r, cabecera, funcional):
    if funcional == 'anomalia':
        return cabecera['earth_gravity_constant'] / r ** 2 * MGAL           # en mGal
    if funcional == 'potencial':
        return cabecera['earth_gravity_constant'] / r                       # en m²/s²
    return cabecera['radius']                                               # topografía en m


def sintesis_puntos(C, S, cabecera, lat, lon, h=0.0, funcional='anomalia'):
    """Evalúa el modelo en puntos sueltos (p. ej., en cada estación, a su propia altura).

    funcional: 'anomalia' (Δg en mGal; usar coeficientes perturbadores), 'potencial' (T en m²/s²) o 'superficie'
    (modelos de topografía: H en m, evaluada con la latitud geocéntrica del punto).
    """
    psi, lam, r = geocentricas(lat, lon, h)
    psi, lam, r = np.atleast_1d(psi), np.atleast_1d(lam), np.atleast_1d(r)
    N = C.shape[0] - 1
    m = np.arange(N + 1)[:, None]
    cos_m, sen_m = np.cos(m * lam), np.sin(m * lam)                   # (N + 1) × puntos
    total = np.zeros(psi.size)
    for n, fila in enumerate(_filas_legendre(psi, N)):
        suma_m = np.einsum('mp,mp->p', fila, C[n, :n + 1, None] * cos_m[:n + 1] + S[n, :n + 1, None] * sen_m[:n + 1])
        total += _factor_grado(n, r, cabecera['radius'], funcional) * suma_m
    return total * _escala_funcional(r, cabecera, funcional)


def sintesis_grilla(C, S, cabecera, lats, lons, h=0.0, funcional='anomalia'):
    """Evalúa el modelo en una grilla regular (filas = `lats`, columnas = `lons`, en grados) a la altura `h`.

    Como en una grilla la latitud se repite por fila y la longitud por columna, la suma en m se hace con un producto
    de matrices por grado: mucho más rápido que tratar cada nodo como un punto suelto.
    """
    lats, lons = np.asarray(lats, float), np.asarray(lons, float)
    psi, _, r = geocentricas(lats, np.zeros_like(lats), h)
    lam = np.radians(lons)
    N = C.shape[0] - 1
    m = np.arange(N + 1)[:, None]
    cos_m, sen_m = np.cos(m * lam), np.sin(m * lam)                   # (N + 1) × columnas
    total = np.zeros((lats.size, lons.size))
    for n, fila in enumerate(_filas_legendre(psi, N)):
        parcial = (fila * C[n, :n + 1, None]).T @ cos_m[:n + 1] + (fila * S[n, :n + 1, None]).T @ sen_m[:n + 1]
        total += np.asarray(_factor_grado(n, r, cabecera['radius'], funcional))[..., None] * parcial
    return total * np.asarray(_escala_funcional(r, cabecera, funcional))[..., None]


def correccion_placa(H):
    """Atracción de la placa de Bouguer 2πGρH en mGal (ρ = 2670 kg/m³ en tierra y 1645 kg/m³ bajo el mar)."""
    H = np.asarray(H, float)
    return 2 * np.pi * G * np.where(H >= 0, RHO_CORTEZA, RHO_AGUA_CORTEZA) * H * MGAL


# ------------------------------------------------------------------------------------------ estaciones
def gravedad_normal_1967(lat):
    """Gravedad normal sobre el elipsoide (mGal) con la Fórmula Internacional de 1967."""
    lat = np.radians(np.asarray(lat, float))
    return 978031.846 * (1 + 0.0053024 * np.sin(lat) ** 2 - 0.0000058 * np.sin(2 * lat) ** 2)


def bouguer_simple(gravedad_observada, lat, h, densidad=RHO_CORTEZA):
    """Anomalía de Bouguer simple de una estación (mGal): g − γ + 0,3086·h − 2πGρ·h, sin corrección de terreno."""
    placa = 2 * np.pi * G * densidad * MGAL
    return (np.asarray(gravedad_observada, float) - gravedad_normal_1967(lat)
            + (GRADIENTE_AIRE_LIBRE - placa) * np.asarray(h, float))


def correccion_terreno(puntos, alturas, ruta_dem, aoi, celda=250, radio=20_000, densidad=RHO_CORTEZA):
    """Corrección de terreno aproximada (mGal) en cada punto, a partir de un DEM.

    La placa de Bouguer supone un terreno plano a la altura de la estación. Los cerros de alrededor (masa de más,
    encima) y los valles (masa de menos, debajo) atraen o dejan de atraer, y en ambos casos la gravedad medida queda
    más baja que la de una placa: la corrección siempre suma. Cada celda del DEM se aproxima como una columna
    vertical de sección `celda`² a distancia r y con desnivel Δh respecto de la estación:

        δg = Gρ·A·(1/r − 1/√(r² + Δh²))

    Se suman las celdas hasta `radio` metros (la zona M de Hammer llega a 21,9 km) y se omite la celda de la
    estación, cuyo efecto depende de detalles que un DEM de 250 m no resuelve. `puntos` debe estar en UTM.
    """
    from .espacial import raster_a_utm

    z, (x0, _, _, y1) = raster_a_utm(ruta_dem, aoi, celda=celda, margen=radio + 2 * celda)
    k = int(np.ceil(radio / celda))
    dx = celda * np.arange(-k, k + 1)
    DX, DY = np.meshgrid(dx, -dx)
    correcciones = []
    for x, y, h in zip(puntos.geometry.x, puntos.geometry.y, np.asarray(alturas, float)):
        i, j = int((y1 - y) // celda), int((x - x0) // celda)
        ventana = z[i - k:i + k + 1, j - k:j + k + 1]
        # Distancia desde la estación al centro de cada celda de la ventana
        r = np.hypot(DX + (x0 + (j + 0.5) * celda - x), DY + (y1 - (i + 0.5) * celda - y))
        usar = (r > 0.75 * celda) & (r <= radio) & np.isfinite(ventana)
        dh = ventana[usar] - h
        correcciones.append(G * densidad * celda ** 2 * np.sum(1 / r[usar] - 1 / np.sqrt(r[usar] ** 2 + dh ** 2)))
    return np.array(correcciones) * MGAL


# ------------------------------------------------------------------------------------------ separación regional
def separar_regional(matriz, celda, sigma_m):
    """Separa una grilla de anomalía de Bouguer en una parte regional y una residual.

    La regional es la grilla suavizada con un filtro gaussiano de desviación `sigma_m` metros: retiene las longitudes
    de onda largas (en los Andes, el engrosamiento de la corteza). La residual = grilla − regional conserva las
    fuentes más someras y pequeñas, como un plutón. El resultado depende de `sigma_m`, por lo que conviene probar
    varios valores. Devuelve (regional, residual).
    """
    from scipy.ndimage import gaussian_filter

    regional = gaussian_filter(matriz, sigma_m / celda, mode='nearest')
    return regional, matriz - regional
