"""Pruebas de las métricas de comparación entre fuentes."""

import numpy as np
import pandas as pd
import pytest

from geocomp.estadistica import comparar_pares_log, mediana_por_tramo, metricas_acuerdo, resumen_por_grupo


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


def test_mediana_por_tramo():
    tabla = pd.DataFrame({'SiO2': [46, 47, 48, 52, 53, 54, 71], 'U': [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 9.0]})
    r = mediana_por_tramo(tabla, 'SiO2', 'U', tramos=[45, 50, 55, 75])
    assert list(r['med']) == [2.0, 5.0]               # el tramo 55-75 tiene una sola roca y se descarta
    assert list(r['x']) == [47.5, 52.5]
    assert list(r['n']) == [3, 3]


def test_bland_altman_lineal_y_logaritmico():
    from geocomp.estadistica import bland_altman
    a = np.array([1.0, 2.0, 4.0, 8.0])
    lineal = bland_altman(a, a + 1)
    assert lineal['sesgo'] == pytest.approx(1)
    assert lineal['lim_inf'] == pytest.approx(1) and lineal['lim_sup'] == pytest.approx(1)
    log = bland_altman(a, 10 * a, log=True)                 # la segunda fuente mide siempre 10 veces más
    assert log['sesgo'] == pytest.approx(1)                 # log10(10) = 1
    np.testing.assert_allclose(log['media'], np.sqrt(10) * a)


def test_intervalo_de_la_razon_mediana():
    from geocomp.estadistica import intervalo_razon_mediana
    rng = np.random.default_rng(3)
    a = rng.lognormal(1, 0.5, 200)
    inferior, superior = intervalo_razon_mediana(a, 2 * a * rng.lognormal(0, 0.1, 200))
    assert inferior < 2 < superior
    assert np.isnan(intervalo_razon_mediana([1.0, 2.0], [2.0, 4.0])[0])     # con menos de 3 pares no se calcula


def test_regresion_log_recupera_el_factor():
    from geocomp.estadistica import regresion_log
    x = np.linspace(45, 75, 40)
    y = 2 * 10 ** (0.03 * (x - 45))                  # el valor se multiplica por 10^0,3 ≈ 2 cada 10 unidades
    r = regresion_log(x, y)
    assert r['pendiente'] == pytest.approx(0.03)
    assert r['r2'] == pytest.approx(1)
    assert r['pend_inf'] <= r['pendiente'] <= r['pend_sup']


def test_correlacion_parcial_quita_la_variable_comun():
    """x e y dependen las dos de z, pero no entre sí: la correlación simple es alta y la parcial, cercana a 0."""
    from scipy import stats

    from geocomp.estadistica import correlacion_parcial
    rng = np.random.default_rng(5)
    z = rng.normal(size=500)
    x, y = z + rng.normal(0, 0.3, 500), z + rng.normal(0, 0.3, 500)
    assert stats.spearmanr(x, y)[0] > 0.8
    rho, p = correlacion_parcial(x, y, z)
    assert abs(rho) < 0.15 and p > 0.01
