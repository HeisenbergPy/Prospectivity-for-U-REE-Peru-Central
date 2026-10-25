"""Pruebas de integridad de los datos del repositorio: están completos, no cambiaron y se leen bien."""

import pytest

from geocomp import lectura
from geocomp.acceso import verificar_manifiesto
from geocomp.rutas import ARCHIVOS, CRS_UTM


def test_todos_los_archivos_coinciden_con_su_huella():
    tabla = verificar_manifiesto()
    faltan = tabla.loc[~tabla['existe'], 'archivo'].tolist()
    cambiados = tabla.loc[tabla['existe'] & ~tabla['huella_ok'], 'archivo'].tolist()
    assert not faltan, f'Faltan archivos: {faltan}'
    assert not cambiados, f'Archivos modificados respecto del manifiesto: {cambiados}'


@pytest.mark.parametrize('nombre', list(ARCHIVOS))
def test_cada_archivo_existe(nombre):
    assert ARCHIVOS[nombre].exists()


def test_estaciones_de_gravedad():
    estaciones = lectura.cargar_gravedad_estaciones()
    assert len(estaciones) == 192
    assert estaciones.crs.to_string() == CRS_UTM
    assert estaciones['bouguer_mgal'].between(-500, 0).all()     # rango plausible en los Andes centrales


def test_uranio_une_las_cinco_fuentes_dentro_del_area():
    u = lectura.cargar_uranio()
    assert set(u['fuente']) == set(lectura.FUENTES_U)
    aoi = lectura.cargar_aoi().buffer(500).union_all()            # 500 m de tolerancia en el borde
    assert u.within(aoi).all()


def test_uranio_sin_duplicados_exactos():
    u = lectura.cargar_uranio()
    clave = u[['fuente', 'codigo', 'U_ppm']].astype(str).assign(x=u.geometry.x.round(), y=u.geometry.y.round())
    assert not clave.duplicated().any()


def test_uranio_excluye_lo_que_no_es_roca():
    u = lectura.cargar_uranio()
    assert len(u[u['fuente'] == 'GE27']) == 45                     # 48 muestras menos 3 suelos
    assert len(u[u['fuente'] == 'IPEN']) == 19                     # 20 menos la torbernita
    assert u['U_ppm'].max() < 10_000


def test_teselas_del_dem():
    """El área (−75,6 a −74,5; −11,8 a −10,5) cae en 4 teselas de 1°, nombradas por su esquina suroeste."""
    from geocomp.acceso import teselas_dem
    urls = teselas_dem((-75.55, -11.76, -74.54, -10.49))
    assert len(urls) == 4
    assert any('S12_00_W076_00' in u for u in urls)
