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


def mediana_por_tramo(tabla, x, y, tramos, minimo=3):
    """Mediana y rango intercuartil (Q1-Q3) de `y` en tramos de `x` (p. ej., U en tramos de 5 % de SiO2).

    Solo se conservan los tramos con al menos `minimo` valores. Devuelve una tabla con la mediana (`med`), los
    cuartiles (`q1`, `q3`), el número de valores (`n`) y el centro del tramo (`x`), lista para dibujar la tendencia.
    """
    datos = tabla[[x, y]].dropna()
    resumen = datos.groupby(pd.cut(datos[x], tramos), observed=True)[y].agg(
        med='median', q1=lambda v: v.quantile(0.25), q3=lambda v: v.quantile(0.75), n='size')
    resumen = resumen[resumen.n >= minimo].copy()
    resumen['x'] = [tramo.mid for tramo in resumen.index]
    return resumen


def bland_altman(referencia, estimado, log=False):
    """Diagrama de Bland y Altman (1986): diferencia entre dos fuentes frente a su promedio.

    Muestra si el desacuerdo depende del nivel de la variable. Devuelve un diccionario con `media` y `diferencia`
    (arreglos para graficar), el `sesgo` (media de la diferencia) y los límites de acuerdo al 95 % (`lim_inf`,
    `lim_sup` = sesgo ± 1,96 desviaciones). Con `log=True` (variables positivas como el U) la diferencia es
    log10(estimado/referencia) y la media es la media geométrica: el error se lee como un factor.
    """
    x, y = np.asarray(referencia, float), np.asarray(estimado, float)
    ok = np.isfinite(x) & np.isfinite(y) & ((x > 0) & (y > 0) if log else True)
    x, y = x[ok], y[ok]
    if log:
        media, diferencia = np.sqrt(x * y), np.log10(y / x)
    else:
        media, diferencia = (x + y) / 2, y - x
    sesgo, desv = diferencia.mean(), diferencia.std(ddof=1)
    return {'media': media, 'diferencia': diferencia, 'n': int(ok.sum()), 'sesgo': sesgo,
            'lim_inf': sesgo - 1.96 * desv, 'lim_sup': sesgo + 1.96 * desv}


def intervalo_razon_mediana(a, b, nivel=0.90, n_remuestreos=2000, semilla=0):
    """Intervalo de confianza de la razón mediana b/a por remuestreo de los pares (bootstrap de percentiles).

    Con pocos pares la mediana es inestable; el intervalo dice qué tan lejos de 1 está con esa incertidumbre.
    `semilla` fija el remuestreo para que el resultado sea reproducible.
    """
    a, b = np.asarray(a, float), np.asarray(b, float)
    ok = np.isfinite(a) & np.isfinite(b) & (a > 0) & (b > 0)
    razon = b[ok] / a[ok]
    if len(razon) < 3:
        return np.nan, np.nan
    rng = np.random.default_rng(semilla)
    medianas = np.median(rng.choice(razon, size=(n_remuestreos, len(razon)), replace=True), axis=1)
    cola = (1 - nivel) / 2
    return tuple(np.quantile(medianas, [cola, 1 - cola]))


def regresion_log(x, y, log_x=False):
    """Recta de mínimos cuadrados de log10(y) frente a x (o frente a log10(x) si `log_x`).

    En geoquímica las concentraciones varían en órdenes de magnitud, así que la relación se ajusta en escala
    logarítmica. Devuelve n, pendiente, su intervalo de confianza del 95 % (t de Student), intercepto y r². Con
    `log_x=False`, 10^(pendiente·Δx) es el factor por el que se multiplica y cuando x aumenta Δx.
    """
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y) & (y > 0) & ((x > 0) if log_x else True)
    xx = np.log10(x[ok]) if log_x else x[ok]
    ajuste = stats.linregress(xx, np.log10(y[ok]))
    t = stats.t.ppf(0.975, ok.sum() - 2)
    return {'n': int(ok.sum()), 'pendiente': ajuste.slope, 'pend_inf': ajuste.slope - t * ajuste.stderr,
            'pend_sup': ajuste.slope + t * ajuste.stderr, 'intercepto': ajuste.intercept, 'r2': ajuste.rvalue ** 2}


def correlacion_parcial(x, y, z):
    """Correlación de Spearman entre x e y descontando el efecto de z (p. ej., la posición este-oeste).

    Se pasan las tres variables a rangos, se quita a x y a y la parte que explica z con una recta y se correlacionan
    los residuos. Si x e y solo se parecen porque ambas cambian con z, la correlación parcial se acerca a 0.
    Devuelve (rho, p), con el valor p de una t de Student con n − 3 grados de libertad.
    """
    tabla = pd.DataFrame({'x': x, 'y': y, 'z': z}).dropna()
    rangos = tabla.rank()

    def residuo(v):
        return rangos[v] - np.polyval(np.polyfit(rangos['z'], rangos[v], 1), rangos['z'])

    rho = np.corrcoef(residuo('x'), residuo('y'))[0, 1]
    n = len(tabla)
    t = rho * np.sqrt((n - 3) / (1 - rho ** 2))
    return rho, 2 * stats.t.sf(abs(t), n - 3)
