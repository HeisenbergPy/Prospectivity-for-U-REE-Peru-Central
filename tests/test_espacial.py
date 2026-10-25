"""Pruebas de las operaciones espaciales con datos sintéticos (resultado conocido de antemano)."""

import geopandas as gpd
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import Point, box

from geocomp.espacial import cobertura, muestrear_raster, pares_cercanos, raster_a_utm, vecino_mas_cercano

CRS = 'EPSG:32718'


@pytest.fixture
def raster_plano(tmp_path):
    """Ráster de 10 × 10 píxeles de 100 m con z = 2·x + 3·y (x, y en km): un plano, que la interpolación bilineal
    debe reproducir exactamente."""
    x0, y0, paso = 500_000.0, 8_700_000.0, 100.0
    cols, filas = np.meshgrid(np.arange(10), np.arange(10))
    x = x0 + (cols + 0.5) * paso
    y = y0 - (filas + 0.5) * paso
    z = (2 * x + 3 * y) / 1000
    ruta = tmp_path / 'plano.tif'
    with rasterio.open(ruta, 'w', driver='GTiff', height=10, width=10, count=1, dtype='float64', crs=CRS,
                       transform=from_origin(x0, y0, paso, paso), nodata=-9999) as dst:
        dst.write(z, 1)
    return ruta


def test_bilineal_reproduce_un_plano(raster_plano):
    puntos = gpd.GeoDataFrame(geometry=[Point(500_237.0, 8_699_412.0), Point(500_801.0, 8_699_150.0)], crs=CRS)
    esperado = (2 * puntos.geometry.x + 3 * puntos.geometry.y) / 1000
    np.testing.assert_allclose(muestrear_raster(raster_plano, puntos), esperado, rtol=0, atol=1e-6)


def test_punto_fuera_del_raster_es_nan(raster_plano):
    puntos = gpd.GeoDataFrame(geometry=[Point(400_000.0, 8_699_500.0)], crs=CRS)
    assert np.isnan(muestrear_raster(raster_plano, puntos)[0])


def test_reproyecta_los_puntos_al_crs_del_raster(raster_plano):
    punto = gpd.GeoDataFrame(geometry=[Point(500_450.0, 8_699_550.0)], crs=CRS)
    en_utm = muestrear_raster(raster_plano, punto)
    en_geograficas = muestrear_raster(raster_plano, punto.to_crs('EPSG:4326'))
    np.testing.assert_allclose(en_utm, en_geograficas, atol=1e-6)


def test_pares_cercanos_usa_cada_muestra_una_vez():
    a = gpd.GeoDataFrame(geometry=[Point(0, 0), Point(1000, 0)], crs=CRS)
    b = gpd.GeoDataFrame(geometry=[Point(10, 0), Point(30, 0), Point(5000, 0)], crs=CRS)
    pares = pares_cercanos(a, b, distancia_max=100)
    # Las dos muestras de b cercanas a a[0] compiten por ella: se queda la más cercana (b[0], a 10 m)
    assert len(pares) == 1
    assert pares.loc[0, ['i_a', 'i_b']].tolist() == [0, 0]
    assert pares.loc[0, 'dist_m'] == pytest.approx(10)


def test_cobertura_cuenta_celdas_con_dato():
    aoi = gpd.GeoDataFrame(geometry=[box(0, 0, 10_000, 10_000)], crs=CRS)    # 4 celdas de 5 km
    puntos = gpd.GeoDataFrame(geometry=[Point(1000, 1000), Point(2000, 2000), Point(7000, 7000)], crs=CRS)
    tabla = cobertura(puntos, aoi, celda=5000)
    assert tabla.loc['todas', 'celdas_con_dato'] == 2
    assert tabla.loc['todas', 'cobertura_pct'] == pytest.approx(50)


def test_raster_a_utm_cubre_el_area(raster_plano):
    aoi = gpd.GeoDataFrame(geometry=[box(500_100, 8_699_100, 500_900, 8_699_900)], crs=CRS)
    matriz, extension = raster_a_utm(raster_plano, aoi, celda=100, margen=0)
    assert matriz.shape == (8, 8)
    assert extension == (500_100, 500_900, 8_699_100, 8_699_900)
    assert np.isfinite(matriz).all()


def test_bilineal_cerca_del_borde_no_es_nan(raster_plano):
    # A 10 m del borde izquierdo (media celda exterior) se usa el valor del píxel del borde
    puntos = gpd.GeoDataFrame(geometry=[Point(500_010.0, 8_699_550.0)], crs=CRS)
    assert np.isfinite(muestrear_raster(raster_plano, puntos)[0])


def test_cercano_toma_el_pixel_que_contiene_al_punto(raster_plano):
    # x = 500 150 m está en la columna 1 (100–200 m); y = 8 699 950 m está en la fila 0
    puntos = gpd.GeoDataFrame(geometry=[Point(500_150.0, 8_699_950.0), Point(500_200.0, 8_699_950.0)], crs=CRS)
    esperado = [(2 * 500_150.0 + 3 * 8_699_950.0) / 1000, (2 * 500_250.0 + 3 * 8_699_950.0) / 1000]
    np.testing.assert_allclose(muestrear_raster(raster_plano, puntos, metodo='cercano'), esperado)


def test_metodo_desconocido_da_error(raster_plano):
    puntos = gpd.GeoDataFrame(geometry=[Point(500_450.0, 8_699_550.0)], crs=CRS)
    with pytest.raises(ValueError):
        muestrear_raster(raster_plano, puntos, metodo='bilinear')


def test_cobertura_cuenta_puntos_en_bordes_y_esquinas():
    aoi = gpd.GeoDataFrame(geometry=[box(0, 0, 10_000, 10_000)], crs=CRS)
    puntos = gpd.GeoDataFrame(geometry=[Point(5000, 2000), Point(0, 0), Point(10_000, 10_000)], crs=CRS)
    tabla = cobertura(puntos, aoi, celda=5000)
    assert tabla.loc['todas', 'puntos'] == 3                    # ninguno se pierde por estar sobre una línea
    assert tabla.loc['todas', 'celdas_con_dato'] == 3


def test_distancias_exigen_coordenadas_en_metros():
    a = gpd.GeoDataFrame(geometry=[Point(-75.0, -11.0)], crs='EPSG:4326')
    with pytest.raises(ValueError):
        pares_cercanos(a, a, distancia_max=100)
    with pytest.raises(ValueError):
        vecino_mas_cercano(a, a, columnas=[])


def test_muestrear_matriz_bilineal():
    """En una matriz que crece 1 por columna, el valor interpolado en x es la posición en celdas."""
    import geopandas as gpd
    from shapely.geometry import Point

    from geocomp.espacial import muestrear_matriz
    matriz = np.tile(np.arange(10.0), (5, 1))                       # 5 filas × 10 columnas, celdas de 100 m
    extension = (0, 1000, 0, 500)
    puntos = gpd.GeoDataFrame(geometry=[Point(50, 250), Point(500, 250), Point(2000, 250)], crs='EPSG:32718')
    valores = muestrear_matriz(matriz, extension, puntos)
    np.testing.assert_allclose(valores[:2], [0.0, 4.5])
    assert np.isnan(valores[2])                                     # fuera de la matriz
