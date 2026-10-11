"""Pruebas de las métricas de comparación entre fuentes."""

import numpy as np
import pandas as pd
import pytest

from geocomp.estadistica import comparar_pares_log, metricas_acuerdo, resumen_por_grupo


def test_metricas_con_un_sesgo_constante():
    referencia = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    m = metricas_acuerdo(referencia, referencia + 2)       # misma forma, desplazada 2 unidades
    assert m['n'] == 5
    assert m['sesgo'] == pytest.approx(2)
    assert m['desv'] == pytest.approx(0)
    assert m['rms'] == pytest.approx(2)
    assert m['r'] == pytest.approx(1)
    assert m['pendiente'] == pytest.approx(1)
    assert m['intercepto'] == pytest.approx(2)


def test_metricas_ignoran_pares_incompletos():
    m = metricas_acuerdo([1, 2, np.nan, 4, 5], [1, 2, 3, np.nan, 5])
    assert m['n'] == 3


def test_razon_mediana_entre_pares():
    a = np.array([1.0, 2.0, 4.0, 8.0, 16.0, 32.0])
    r = comparar_pares_log(a, 2 * a)                        # la segunda fuente mide siempre el doble
    assert r['n'] == 6
    assert r['razon_mediana'] == pytest.approx(2)


def test_resumen_por_grupo_respeta_el_orden():
    tabla = pd.DataFrame({'fuente': ['B', 'A', 'A', 'B'], 'U': [1.0, 2.0, 4.0, np.nan]})
    r = resumen_por_grupo(tabla, 'U', 'fuente', orden=['A', 'B'])
    assert list(r.index) == ['A', 'B']
    assert r.loc['A', 'mediana'] == pytest.approx(3)
    assert r.loc['B', 'n_total'] == 2 and r.loc['B', 'n_medido'] == 1
