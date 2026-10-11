"""Pruebas de la conversión de la química (texto a número) y de la extracción del año."""

import numpy as np
import pandas as pd
import pytest

from geocomp.lectura import a_numero, anio_en_texto, leer_valor


@pytest.mark.parametrize('texto, valor, estado, limite', [
    ('3.5', 3.5, 'numero', np.nan),
    ('3,5', 3.5, 'numero', np.nan),            # coma decimal
    (12.0, 12.0, 'numero', np.nan),            # ya es número
    ('<2.00', np.nan, '<LD', 2.0),             # debajo del límite de detección
    (-0.5, np.nan, '<LD', 0.5),                # convención de INGEMMET: −LD significa "< LD"
    ('>1000', np.nan, '>LS', 1000.0),          # sobre el límite superior
    ('########', np.nan, 'perdido', np.nan),   # valor perdido en la fuente
    ('0', np.nan, 'cero', np.nan),             # en roca, 0 significa "no determinado"
    ('N.R', np.nan, 'vacio', np.nan),          # no reportado
    (None, np.nan, 'vacio', np.nan),
    ('', np.nan, 'vacio', np.nan),
    (pd.NA, np.nan, 'vacio', np.nan),         # nulo de pandas (no es '<NA>' debajo del límite)
    ('1E+3', 1000.0, 'numero', np.nan),       # notación científica con signo
    ('1,000', np.nan, 'ambiguo', np.nan),     # ¿coma decimal (1) o de miles (1000)? No se adivina
    ('2.5 ppm', np.nan, 'ambiguo', np.nan),   # texto no reconocido: no se descarta en silencio como vacío
])
def test_leer_valor(texto, valor, estado, limite):
    v, e, lim = leer_valor(texto)
    assert e == estado
    np.testing.assert_equal(v, valor)
    np.testing.assert_equal(lim, limite)


def test_a_numero_conserva_el_indice():
    serie = pd.Series(['1.2', '<0.5', '########', '4'], index=[10, 11, 12, 13])
    resultado = a_numero(serie)
    assert list(resultado.index) == [10, 11, 12, 13]
    np.testing.assert_array_equal(resultado.values, [1.2, np.nan, np.nan, 4.0])


@pytest.mark.parametrize('texto, anio', [
    ('Miscovic & Schalteger (2009)', 2009.0),
    ('Valencia y Mamani 2013 (ICT 2011, IPEN), tabla 2', 2013.0),
    ('C50-3', np.nan),
    (np.nan, np.nan),
])
def test_anio_en_texto(texto, anio):
    np.testing.assert_equal(anio_en_texto(texto), anio)
