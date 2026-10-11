"""Estadística para comparar fuentes de una misma variable y resumir distribuciones por grupo."""

import numpy as np
import pandas as pd
from scipy import stats


def metricas_acuerdo(referencia, estimado):
    """Acuerdo entre dos fuentes de la misma variable, medidas en los mismos lugares.

    Diferencia = estimado − referencia. Devuelve:
        n         pares válidos
        sesgo     media de la diferencia (error sistemático)
        desv      desviación estándar de la diferencia (error aleatorio)
        rms       raíz del error cuadrático medio (sesgo y dispersión juntos)
        r         correlación de Pearson (¿se mueven juntas?)
        rho       correlación de Spearman (igual, pero por rangos: robusta a valores extremos)
        pendiente e intercepto de la recta de mínimos cuadrados estimado ~ referencia
    """
    x, y = np.asarray(referencia, float), np.asarray(estimado, float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    if len(x) < 3 or np.ptp(x) == 0:
        raise ValueError('Se necesitan al menos 3 pares válidos y una referencia que no sea constante')
    dif = y - x
    ajuste = stats.linregress(x, y)
    return {'n': int(ok.sum()), 'sesgo': dif.mean(), 'desv': dif.std(ddof=1), 'rms': np.sqrt(np.mean(dif ** 2)),
            'r': stats.pearsonr(x, y)[0], 'rho': stats.spearmanr(x, y)[0],
            'pendiente': ajuste.slope, 'intercepto': ajuste.intercept}


def comparar_pares_log(a, b):
    """Compara dos fuentes con muestras emparejadas de una variable positiva (p. ej. U en ppm).

    Usa la razón b/a: en geoquímica los errores son proporcionales, así que una razón de 2 pesa lo mismo con 1 ppm
    que con 100 ppm. La prueba de Wilcoxon de rangos con signo sobre log(b/a) dice si la mediana de la razón
    difiere de 1 (sesgo entre fuentes).
    """
    a, b = np.asarray(a, float), np.asarray(b, float)
    ok = np.isfinite(a) & np.isfinite(b) & (a > 0) & (b > 0)
    razon = b[ok] / a[ok]
    p = stats.wilcoxon(np.log(razon)).pvalue if ok.sum() >= 5 else np.nan
    return {'n': int(ok.sum()), 'razon_mediana': np.median(razon) if ok.any() else np.nan, 'p_wilcoxon': p}


def resumen_por_grupo(tabla, valor, grupo, orden=None):
    """Tabla descriptiva de `valor` por `grupo`: filas totales (`n_total`), filas con valor (`n_medido`), mediana,
    cuartiles, mínimo y máximo. `orden` fija el orden de los grupos en la tabla."""
    filas = []
    for g, t in tabla.groupby(grupo, sort=False):
        v = t[valor].dropna()
        filas.append({grupo: g, 'n_total': len(t), 'n_medido': len(v), 'mediana': v.median(),
                      'P25': v.quantile(0.25), 'P75': v.quantile(0.75), 'min': v.min(), 'max': v.max()})
    resumen = pd.DataFrame(filas).set_index(grupo)
    return resumen.reindex(orden) if orden is not None else resumen
