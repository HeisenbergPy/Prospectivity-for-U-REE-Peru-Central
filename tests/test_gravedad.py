"""Pruebas de la síntesis armónica y de la reducción de las estaciones gravimétricas."""

import geopandas as gpd
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from scipy.special import factorial, lpmv
from shapely.geometry import Point, box

from geocomp import gravedad as gr


def test_legendre_coincide_con_scipy():
    """Las funciones de Legendre totalmente normalizadas de la recursión coinciden con las de SciPy."""
    psi = np.array([-0.2, 0.0, 0.7])
    filas = list(gr._filas_legendre(psi, 8))
    for n in range(9):
        for m in range(n + 1):
            norma = np.sqrt((1 if m == 0 else 2) * (2 * n + 1) * factorial(n - m) / factorial(n + m))
            esperado = norma * (-1) ** m * lpmv(m, n, np.sin(psi))     # SciPy incluye la fase (−1)^m
            np.testing.assert_allclose(filas[n][m], esperado, atol=1e-12)


def test_campo_normal_grs80():
    """El campo normal restado reproduce los zonales publicados del GRS80 (Moritz, 1980): J2 y J4."""
    cabecera = {'earth_gravity_constant': gr.GRS80['GM'], 'radius': gr.GRS80['a']}
    C = np.zeros((21, 21))
    C[0, 0], C[2, 0] = 1.0, -gr.GRS80['J2'] / np.sqrt(5)          # un modelo con solo el término central y J2
    dC = gr.restar_campo_normal(C, cabecera)
    assert dC[0, 0] == pytest.approx(0.0, abs=1e-15)
    assert dC[2, 0] == pytest.approx(0.0, abs=1e-15)
    # ΔC̄40 = 0 − C̄40(normal) = J4/3, con J4 = −0,237091222·10⁻⁵
    assert 3 * dC[4, 0] == pytest.approx(-0.237091222e-5, rel=1e-6)


def test_topografia_de_grado_cero():
    """Una topografía con solo el término de grado cero vale lo mismo en todas partes."""
    cabecera = {'radius': 6378137.0}
    C, S = np.zeros((3, 3)), np.zeros((3, 3))
    C[0, 0] = 1000 / cabecera['radius']                                 # H = R · C̄00 = 1000 m
    H = gr.sintesis_grilla(C, S, cabecera, [-11.0, -10.0], [-75.0, -74.5, -74.0], funcional='superficie')
    np.testing.assert_allclose(H, 1000.0)
    puntos = gr.sintesis_puntos(C, S, cabecera, [-11.0, 5.0], [-75.0, 120.0], funcional='superficie')
    np.testing.assert_allclose(puntos, 1000.0)


def test_grilla_y_puntos_dan_lo_mismo():
    """La síntesis en grilla (producto de matrices) y en puntos sueltos dan el mismo resultado."""
    rng = np.random.default_rng(1)
    N = 30
    C, S = rng.normal(0, 1e-6, (N + 1, N + 1)), rng.normal(0, 1e-6, (N + 1, N + 1))
    C, S = np.tril(C), np.tril(S)
    S[:, 0] = 0
    cabecera = {'earth_gravity_constant': 3.986004415e14, 'radius': 6378136.3}
    lats, lons = np.array([-10.5, -11.0, -11.5]), np.array([-75.5, -75.0])
    grilla = gr.sintesis_grilla(C, S, cabecera, lats, lons, h=1000.0)
    LAT, LON = np.meshgrid(lats, lons, indexing='ij')
    puntos = gr.sintesis_puntos(C, S, cabecera, LAT.ravel(), LON.ravel(), h=1000.0)
    np.testing.assert_allclose(grilla.ravel(), puntos, rtol=1e-10)


def test_geocentricas_en_el_ecuador_y_el_polo():
    psi, _, r = gr.geocentricas([0.0, 90.0], [0.0, 0.0], 0.0)
    np.testing.assert_allclose(psi, [0.0, np.pi / 2])
    np.testing.assert_allclose(r, [gr.GRS80['a'], gr.GRS80['a'] * np.sqrt(1 - gr.GRS80['e2'])])


def test_placa_de_bouguer():
    assert gr.correccion_placa(1000.0) == pytest.approx(111.97, abs=0.01)      # 0,112 mGal/m con 2670 kg/m³
    assert gr.correccion_placa(-1000.0) == pytest.approx(-68.98, abs=0.01)     # bajo el mar: 1645 kg/m³


def test_bouguer_simple_de_una_estacion():
    """Con g = γ en el elipsoide (h = 0) la anomalía es 0; a 1000 m suma 308,6 − 112,0 mGal."""
    gamma = gr.gravedad_normal_1967(-11.0)
    assert gr.bouguer_simple(gamma, -11.0, 0.0) == pytest.approx(0.0)
    assert gr.bouguer_simple(gamma, -11.0, 1000.0) == pytest.approx(308.6 - 111.97, abs=0.01)


def _dem_y_area(tmp_path, z):
    """GeoTIFF en UTM 18S con la matriz z (celdas de 250 m) y el área de estudio en su centro."""
    ruta = tmp_path / 'dem.tif'
    x0, y1 = 400_000, 8_800_000
    perfil = dict(driver='GTiff', dtype='float32', width=z.shape[1], height=z.shape[0], count=1,
                  crs='EPSG:32718', transform=from_origin(x0, y1, 250, 250), nodata=-9999)
    with rasterio.open(ruta, 'w', **perfil) as f:
        f.write(z.astype('float32'), 1)
    centro = (x0 + z.shape[1] * 125, y1 - z.shape[0] * 125)
    aoi = gpd.GeoDataFrame(geometry=[box(centro[0] - 1000, centro[1] - 1000, centro[0] + 1000, centro[1] + 1000)],
                           crs='EPSG:32718')
    estacion = gpd.GeoDataFrame(geometry=[Point(*centro)], crs='EPSG:32718')
    return ruta, aoi, estacion


def test_correccion_de_terreno_plano_es_cero(tmp_path):
    ruta, aoi, estacion = _dem_y_area(tmp_path, np.full((120, 120), 1500.0))
    tc = gr.correccion_terreno(estacion, [1500.0], ruta, aoi, celda=250, radio=5000)
    assert tc[0] == pytest.approx(0.0, abs=1e-9)


def test_correccion_de_terreno_en_un_valle_suma(tmp_path):
    """Una estación en el fondo de un valle tiene corrección positiva, mayor cuanto más profundo es el valle."""
    x = np.arange(120) - 59.5
    valle = 1000 + 2 * np.abs(x)[None, :].repeat(120, axis=0) * 250 * 0.3      # laderas de 30 % de pendiente
    (tmp_path / 'a').mkdir()
    (tmp_path / 'b').mkdir()
    ruta, aoi, estacion = _dem_y_area(tmp_path / 'a', valle)
    tc = gr.correccion_terreno(estacion, [1000.0], ruta, aoi, celda=250, radio=5000)
    ruta, aoi, estacion = _dem_y_area(tmp_path / 'b', 1000 + (valle - 1000) * 2)
    tc_profundo = gr.correccion_terreno(estacion, [1000.0], ruta, aoi, celda=250, radio=5000)
    assert tc[0] > 0
    assert tc_profundo[0] > tc[0]


def test_separar_regional_conserva_la_suma():
    rng = np.random.default_rng(2)
    z = np.add.outer(np.zeros(40), np.linspace(-300, -150, 50)) + rng.normal(0, 5, (40, 50))
    regional, residual = gr.separar_regional(z, celda=1000, sigma_m=10_000)
    np.testing.assert_allclose(regional + residual, z)
    assert abs(residual.mean()) < 1 and residual.std() < z.std()
