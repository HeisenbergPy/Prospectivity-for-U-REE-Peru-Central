"""Pruebas del formato de números en español que usan las figuras."""

import pytest

from geocomp.graficos import numero_es, texto_p, valor_p_es


@pytest.mark.parametrize('valor, decimales, texto', [
    (1740.5, 1, '1740,5'),       # sin separador de miles
    (0.8, 2, '0,80'),
    (-12.04, 1, '-12,0'),
])
def test_numero_es(valor, decimales, texto):
    assert numero_es(valor, decimales) == texto


@pytest.mark.parametrize('p, texto', [(0.0312, '0,031'), (4e-17, '< 0,001'), (0.049, '0,049')])
def test_valor_p_es(p, texto):
    assert valor_p_es(p) == texto


def test_texto_p():
    assert texto_p(0.049) == 'p = 0,049'
    assert texto_p(1e-9) == 'p < 0,001'
