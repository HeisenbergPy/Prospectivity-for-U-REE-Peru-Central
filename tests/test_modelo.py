"""Pruebas del módulo de modelos (datos sintéticos con resultado conocido) y de los datos integrados de GC04."""

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from geocomp import modelo


@pytest.fixture
def rocas_sinteticas():
    """60 rocas en una grilla de 6 × 10 km con dos grupos geológicos; el grupo 'granito' tiene más positivos y las
    rocas 0-2 son duplicados de un mismo afloramiento (en bloques distintos a propósito)."""
    rng = np.random.default_rng(0)
    x = np.repeat(np.arange(6), 10) * 10_000.0 + 400_000
    y = np.tile(np.arange(10), 6) * 10_000.0 + 8_700_000
    d = pd.DataFrame({'x': x, 'y': y, 'peso': 1.0, 'grupo_dup': pd.Series([None] * 60, dtype=object),
                      'grupo': np.where(x < 430_000, 'granito', 'otras')})
    d.loc[[0, 1, 2], 'grupo_dup'] = 'G1'
    d.loc[[0, 1, 2], 'x'] = [400_000.0, 450_000.0, 500_000.0]
    d.loc[[0, 1, 2], 'peso'] = 1 / 3
    y_ = np.where(d.grupo.eq('granito'), rng.random(60) < 0.6, rng.random(60) < 0.1).astype(int)
    return d, y_


def test_duplicados_quedan_en_el_mismo_bloque(rocas_sinteticas):
    d, _ = rocas_sinteticas
    b = modelo.bloques(d, lado=32_000)
    assert len(set(b[[0, 1, 2]])) == 1


def test_un_bloque_nunca_se_reparte_entre_pliegues(rocas_sinteticas):
    d, y = rocas_sinteticas
    pl, grupos = modelo.pliegues(d, y, n=3)
    for tr, te in pl:
        assert not set(grupos[tr]) & set(grupos[te])
    evaluadas = np.concatenate([te for _, te in pl])
    assert sorted(evaluadas) == list(range(len(d)))               # cada roca se evalúa una sola vez


def test_linea_base_es_la_tasa_por_grupo_con_laplace():
    d = pd.DataFrame({'grupo': ['a', 'a', 'a', 'b'], 'peso': [1.0, 1.0, 1.0, 1.0]})
    y = np.array([1, 1, 0, 0])
    evaluar = pd.DataFrame({'grupo': ['a', 'b', 'c']})
    tasa = modelo.linea_base(d, y, evaluar)
    np.testing.assert_allclose(tasa[:2], [(2 + 1) / (3 + 2), (0 + 1) / (1 + 2)])
    assert tasa[2] == pytest.approx(np.mean(tasa[:2]))             # grupo nuevo: tasa media


def test_percentil_conserva_el_orden_y_va_de_0_a_100():
    p = np.array([0.2, np.nan, 0.9, 0.1, 0.5])
    r = modelo.a_percentil(p)
    assert np.isnan(r[1])
    assert stats.spearmanr(p[[0, 2, 3, 4]], r[[0, 2, 3, 4]])[0] == pytest.approx(1)
    assert np.nanmax(r) == 100 and np.nanmin(r) > 0


def test_consenso_cuenta_modelos_en_clase_a():
    a = np.array([96.0, 50.0, np.nan])
    b = np.array([99.0, 97.0, np.nan])
    c = modelo.consenso([a, b])
    assert c[0] == 2 and c[1] == 1 and np.isnan(c[2])


def test_clases_por_cortes_de_area():
    c = modelo.clase(np.array([99.0, 90.0, 75.0, 10.0, np.nan]))
    np.testing.assert_array_equal(c[:4], [3, 2, 1, 0])
    assert np.isnan(c[4])


def test_traslacion_conserva_la_proporcion_de_positivos():
    """Rocas repartidas al azar con los positivos agrupados en una esquina: en promedio, el campo desplazado tiene la
    misma proporción de positivos, pero cada traslación los lleva a otro lugar."""
    rng = np.random.default_rng(1)
    d = pd.DataFrame({'x': rng.uniform(0, 100_000, 400), 'y': rng.uniform(0, 100_000, 400)})
    y = ((d.x < 40_000) & (d.y < 40_000)).astype(int).values
    trasladadas = [modelo.trasladar_etiquetas(d, y, rng) for _ in range(300)]
    assert set(np.unique(trasladadas[0])) <= {0, 1}
    assert np.mean([t.mean() for t in trasladadas]) == pytest.approx(y.mean(), abs=0.02)
    assert np.mean([(t == y).mean() for t in trasladadas]) < 0.9


def test_valor_p_de_permutacion():
    assert modelo.valor_p(10, [1, 2, 3]) == pytest.approx(1 / 4)
    assert modelo.valor_p(0, [1, 2, 3]) == pytest.approx(1)


def test_un_modelo_aprende_una_senal_clara():
    """Con una variable que separa las clases, el Random Forest debe superar con holgura a la línea base."""
    rng = np.random.default_rng(2)
    n = 200
    d = pd.DataFrame({'x': rng.uniform(400_000, 560_000, n), 'y': rng.uniform(8_700_000, 8_840_000, n),
                      'peso': 1.0, 'grupo_dup': np.nan, 'grupo': 'unico', 'senal': rng.normal(size=n),
                      'ruido': rng.normal(size=n)})
    y = (d.senal + 0.3 * rng.normal(size=n) > 0.8).astype(int).values
    pl, grupos = modelo.pliegues(d, y, n=3)
    pred, _, _ = modelo.validacion_anidada(d, y, ['senal', 'ruido'], pl, grupos, nombres=['Random Forest'])
    m = modelo.metricas(d, y, pl, pred)
    assert m.loc['Random Forest', 'ROC-AUC'] > 0.9
    assert modelo.habiles(m) == ['Random Forest']


# ------------------------------------------------------------------------------------------ datos de GC04
def test_tabla_de_rocas_y_etiquetas():
    t = modelo.cargar_rocas()
    assert len(t) == 794 and set(t.conjunto) == {'entrenamiento', 'prueba'}
    con_u = t[t.U_pos.notna()]
    assert (con_u.U_pos == (con_u.U_ppm >= modelo.UMBRALES['U_pos'])).all()
    con_ree = t[t.SREE_pos.notna()]
    assert (con_ree.SREE_pos == (con_ree.SREE_ppm >= modelo.UMBRALES['SREE_pos'])).all()


def test_las_variables_de_la_tabla_salen_de_los_rasteres():
    """El valor de cada roca en la tabla coincide con la celda del ráster donde cae (ρ > 0,9 en las variables
    continuas; > 90 % de acuerdo en las indicadoras, que pueden cambiar en un contacto)."""
    t, cat = modelo.cargar_rocas(), modelo.cargar_catalogo()
    for v in cat.variable:
        m, perfil = modelo.leer_variable(v)
        tr = perfil['transform']
        col, fil = ((t.x - tr.c) / tr.a).astype(int), ((t.y - tr.f) / tr.e).astype(int)
        celda, tabla = m[fil, col], t[v].values
        assert (np.isfinite(celda) == np.isfinite(tabla)).mean() > 0.99, v
        ok = np.isfinite(celda) & np.isfinite(tabla)
        if set(np.unique(tabla[ok])) <= {0, 1}:
            assert (celda[ok] == tabla[ok]).mean() > 0.9, v
        else:
            assert stats.spearmanr(celda[ok], tabla[ok])[0] > 0.9, v


def test_todas_las_variables_comparten_la_grilla():
    perfiles = [modelo.leer_variable(v)[1] for v in modelo.cargar_catalogo().variable]
    assert all(p['transform'] == perfiles[0]['transform'] and p['width'] == 440 and p['height'] == 560
               for p in perfiles)
