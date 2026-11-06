"""Modelos de prospectividad: datos integrados, bloques espaciales, línea base geológica, cinco algoritmos con
validación anidada, mapas en percentiles, consenso y prueba contra el azar espacial.

Reglas que siguen todas las funciones:
- la validación es por bloques espaciales (32 km) y los duplicados de un afloramiento quedan en el mismo bloque;
- los hiperparámetros se eligen dentro de cada pliegue (validación anidada), nunca con las rocas de evaluación;
- cada afloramiento pesa 1 (columna `peso` = 1/n de su grupo de duplicados) y las clases se equilibran con pesos;
- las probabilidades no están calibradas, por eso los mapas se expresan en percentiles del área de estudio.
"""

import numpy as np
import pandas as pd
import rasterio
from scipy import stats
from scipy.spatial import cKDTree
from sklearn.base import clone
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from .rutas import ARCHIVOS, RAIZ

SEMILLA = 42
LADO_BLOQUE = 32_000                    # m; mayor que el alcance de la autocorrelación del U en roca
CELDA_KM2 = 0.0625                      # área de una celda de 250 m

# Etiquetas: U ≥ 6,7 ppm (≈ 2 veces un granito promedio) y ΣREE ≥ 478 ppm (percentil 85 de las rocas aptas)
ETIQUETAS = {'U_pos': 'U', 'SREE_pos': 'ΣREE'}
UMBRALES = {'U_pos': 6.7, 'SREE_pos': 478.0}

# Variables que nunca entran a un modelo: describen el muestreo, no la geología
CONTROL = ['sed_densidad', 'grav_dist_estacion_km', 'grav_residual']

LINEA_BASE = 'Línea base geológica'
CORTO = {'Regresión logística': 'RL', 'SVM': 'SVM', 'Random Forest': 'RF', 'Gradient Boosting': 'GB',
         'Red neuronal': 'MLP'}

# Clases de favorabilidad por área: A = 5 % más favorable del área, B = 5-15 %, C = 15-30 %
CLASES = {3: 'A', 2: 'B', 1: 'C'}
CORTES_CLASE = (95, 85, 70)


# ------------------------------------------------------------------------------------------ datos
def cargar_rocas():
    """Tabla de rocas con sus etiquetas y el valor de las 40 variables en su ubicación (UTM 18S)."""
    return pd.read_csv(ARCHIVOS['rocas_variables'])


def cargar_catalogo():
    """Catálogo de variables: familia, descripción, porcentaje del área con dato y archivo."""
    return pd.read_csv(ARCHIVOS['catalogo_variables'])


def conjunto(tabla, etiqueta, cual='entrenamiento'):
    """Rocas con la etiqueta definida en el conjunto pedido ('entrenamiento' o 'prueba') y su vector 0/1."""
    d = tabla[tabla[etiqueta].notna() & tabla.conjunto.eq(cual)].reset_index(drop=True)
    return d, d[etiqueta].astype(int).values


def leer_variable(nombre):
    """Matriz de una variable y su perfil de rasterio."""
    with rasterio.open(RAIZ / 'datos' / 'modelo' / 'variables' / f'{nombre}.tif') as src:
        return src.read(1), src.profile


def pila(variables):
    """Matriz (celdas × variables) de la grilla de 250 m, en el orden de `variables`."""
    return np.stack([leer_variable(v)[0].ravel() for v in variables], axis=1)


def extension(perfil):
    """Extensión (x0, x1, y0, y1) de un ráster para `imshow`."""
    t = perfil['transform']
    return t.c, t.c + perfil['width'] * t.a, t.f + perfil['height'] * t.e, t.f


# ------------------------------------------------------------------------------------------ validación espacial
def bloques(d, lado=LADO_BLOQUE):
    """Código del bloque cuadrado de `lado` m de cada roca; un grupo de duplicados va al bloque de su primer miembro."""
    bx = ((d.x - d.x.min()) // lado).astype(int)
    by = ((d.y - d.y.min()) // lado).astype(int)
    b = bx.astype(str) + '_' + by.astype(str)
    con_grupo = d.grupo_dup.fillna('').ne('')
    if con_grupo.any():
        primero = d[con_grupo].groupby('grupo_dup').apply(lambda g: b[g.index[0]], include_groups=False)
        b[con_grupo] = d.loc[con_grupo, 'grupo_dup'].map(primero)
    return b.values


def pliegues(d, y, n=5, semilla=SEMILLA):
    """Pliegues estratificados por bloques (lista de pares entrenamiento, evaluación) y los bloques de cada roca."""
    grupos = bloques(d)
    n = min(n, len(np.unique(grupos[y == 1])))
    cv = StratifiedGroupKFold(n_splits=n, shuffle=True, random_state=semilla)
    return list(cv.split(d, y, grupos)), grupos


def linea_base(d_ent, y_ent, d_eval):
    """Lo que ya sabe el mapa geológico: tasa ponderada de positivos de cada grupo geológico (con corrección de
    Laplace), aprendida en el entrenamiento y asignada a las rocas de evaluación."""
    t = pd.DataFrame({'g': d_ent.grupo.values, 'y': y_ent * d_ent.peso.values, 'w': d_ent.peso.values})
    t = t.groupby('g').sum()
    tasa = (t.y + 1) / (t.w + 2)
    return d_eval.grupo.map(tasa).fillna(tasa.mean()).values


# ------------------------------------------------------------------------------------------ modelos
def _imputar_escalar():
    """Faltantes por la mediana (con columna indicadora) y estandarización, ajustadas dentro de cada pliegue."""
    return [SimpleImputer(strategy='median', add_indicator=True), StandardScaler()]


def modelos(nucleos=-1):
    """Los cinco algoritmos y sus rejillas de hiperparámetros, de lo más simple a lo más flexible."""
    return {
        'Regresión logística': (
            make_pipeline(*_imputar_escalar(), LogisticRegression(class_weight='balanced', max_iter=5000)),
            {'logisticregression__C': [0.01, 0.1, 1]}),
        'SVM': (
            make_pipeline(*_imputar_escalar(), SVC(kernel='rbf', class_weight='balanced', probability=True,
                                                   random_state=SEMILLA)),
            {'svc__C': [0.3, 1, 3], 'svc__gamma': ['scale', 0.03]}),
        'Random Forest': (
            RandomForestClassifier(n_estimators=300, class_weight='balanced_subsample', n_jobs=nucleos,
                                   random_state=SEMILLA),
            {'min_samples_leaf': [3, 10], 'max_features': ['sqrt', 0.5]}),
        'Gradient Boosting': (
            HistGradientBoostingClassifier(max_iter=200, class_weight='balanced', l2_regularization=1.0,
                                           random_state=SEMILLA),
            {'learning_rate': [0.03, 0.1], 'max_depth': [2, 4]}),
        'Red neuronal': (
            make_pipeline(*_imputar_escalar(), MLPClassifier(max_iter=3000, random_state=SEMILLA)),
            {'mlpclassifier__hidden_layer_sizes': [(16,), (32, 16)], 'mlpclassifier__alpha': [0.01, 0.1]}),
    }


_PARAMETRO_PESO = {'Regresión logística': 'logisticregression__sample_weight', 'SVM': 'svc__sample_weight',
                   'Random Forest': 'sample_weight', 'Gradient Boosting': 'sample_weight',
                   'Red neuronal': 'mlpclassifier__sample_weight'}


def pesos(nombre, d, y):
    """Peso de ajuste: 1 por afloramiento; la red neuronal no tiene `class_weight` y recibe aquí el equilibrio de
    clases."""
    w = d.peso.values.copy()
    if nombre == 'Red neuronal':
        w = w * np.where(y == 1, (y == 0).sum() / max(y.sum(), 1), 1.0)
    return w


def ajustar(nombre, d, y, variables, grupos, catalogo_modelos=None):
    """Búsqueda en rejilla con validación interna por bloques (máximo 3 pliegues, criterio PR-AUC) y ajuste final con
    los mejores hiperparámetros. Devuelve el modelo ajustado y los hiperparámetros elegidos."""
    base, rejilla = (catalogo_modelos or modelos())[nombre]
    n_int = min(3, len(np.unique(grupos[y == 1])))
    busqueda = GridSearchCV(clone(base), rejilla, scoring='average_precision', refit=True,
                            cv=StratifiedGroupKFold(n_splits=n_int, shuffle=True, random_state=SEMILLA))
    busqueda.fit(d[variables].values, y, groups=grupos, **{_PARAMETRO_PESO[nombre]: pesos(nombre, d, y)})
    return busqueda.best_estimator_, busqueda.best_params_


def validacion_anidada(d, y, variables, pl, grupos, nombres=None):
    """Predicciones fuera de pliegue de la línea base y de cada modelo.

    Devuelve (pred, ajustados, parametros): `pred[nombre]` es el vector de predicciones de todas las rocas,
    `ajustados[(nombre, k)]` el modelo del pliegue externo k y `parametros[(nombre, k)]` sus hiperparámetros.
    """
    catalogo_modelos = modelos()
    nombres = list(nombres or catalogo_modelos)
    pred = {m: np.zeros(len(d)) for m in [LINEA_BASE, *nombres]}
    ajustados, parametros = {}, {}
    for k, (tr, te) in enumerate(pl):
        d_tr, d_te = d.iloc[tr].reset_index(drop=True), d.iloc[te]
        pred[LINEA_BASE][te] = linea_base(d_tr, y[tr], d_te)
        for nombre in nombres:
            modelo, params = ajustar(nombre, d_tr, y[tr], variables, grupos[tr], catalogo_modelos)
            pred[nombre][te] = modelo.predict_proba(d_te[variables].values)[:, 1]
            ajustados[(nombre, k)], parametros[(nombre, k)] = modelo, params
    return pred, ajustados, parametros


def metricas(d, y, pl, pred):
    """ROC-AUC, PR-AUC y Brier de cada modelo (sobre todas las predicciones fuera de pliegue, ponderadas por
    afloramiento) y la desviación típica de las dos primeras entre pliegues."""
    w = d.peso.values
    filas = []
    for nombre, p in pred.items():
        validos = [te for _, te in pl if 0 < y[te].sum() < len(te)]
        filas.append({
            'modelo': nombre,
            'ROC-AUC': roc_auc_score(y, p, sample_weight=w),
            'ROC-AUC desv.': np.std([roc_auc_score(y[te], p[te], sample_weight=w[te]) for te in validos]),
            'PR-AUC': average_precision_score(y, p, sample_weight=w),
            'PR-AUC desv.': np.std([average_precision_score(y[te], p[te], sample_weight=w[te]) for te in validos]),
            'Brier': brier_score_loss(y, p, sample_weight=w),
            'prevalencia': np.average(y, weights=w),
        })
    return pd.DataFrame(filas).set_index('modelo')


def habiles(tabla_metricas):
    """Modelos con habilidad demostrada: PR-AUC mayor que la de la línea base geológica."""
    base = tabla_metricas.loc[LINEA_BASE, 'PR-AUC']
    return [m for m in tabla_metricas.index if m != LINEA_BASE and tabla_metricas.loc[m, 'PR-AUC'] > base]


def importancia(ajustados, d, y, pl, variables, nombre, repeticiones=5):
    """Importancia por permutación (caída de la PR-AUC) en las rocas de evaluación de cada pliegue, promediada."""
    acumulado = []
    for k, (_, te) in enumerate(pl):
        if not 0 < y[te].sum() < len(te):
            continue
        imp = permutation_importance(ajustados[(nombre, k)], d.loc[te, variables].values, y[te],
                                     scoring='average_precision', n_repeats=repeticiones, random_state=SEMILLA,
                                     sample_weight=d.peso.values[te])
        acumulado.append(imp.importances_mean)
    return pd.Series(np.mean(acumulado, axis=0), index=variables)


# ------------------------------------------------------------------------------------------ mapas
def predecir(modelo, matriz, tamano=40_000):
    """Probabilidad en cada celda con dato (por tandas, para no llenar la memoria); NaN fuera del área."""
    p = np.full(matriz.shape[0], np.nan)
    dentro = np.flatnonzero(np.isfinite(matriz).any(axis=1))
    for i0 in range(0, len(dentro), tamano):
        i = dentro[i0:i0 + tamano]
        p[i] = modelo.predict_proba(matriz[i])[:, 1]
    return p


def a_percentil(p):
    """Percentil de cada celda dentro del área (0 = menos favorable, 100 = más favorable). Solo depende del orden de
    las celdas, así que permite comparar algoritmos cuyas probabilidades tienen escalas distintas."""
    r = np.full(np.shape(p), np.nan)
    ok = np.isfinite(p)
    r[ok] = 100 * stats.rankdata(p[ok]) / ok.sum()
    return r


def consenso(percentiles, corte=95):
    """Número de modelos que ubican cada celda en la clase A (percentil ≥ `corte`)."""
    pcs = np.stack(percentiles)
    return np.where(np.isfinite(pcs[0]), (pcs >= corte).sum(axis=0), np.nan)


def clase(mediana):
    """Clase de favorabilidad de la mediana de los percentiles: 3 = A, 2 = B, 1 = C y 0 = baja."""
    c = np.select([mediana >= CORTES_CLASE[0], mediana >= CORTES_CLASE[1], mediana >= CORTES_CLASE[2]], [3, 2, 1], 0)
    return np.where(np.isfinite(mediana), c, np.nan)


def guardar_tif(ruta, matriz, perfil):
    """GeoTIFF float32 comprimido con NaN como sin dato, en la grilla de las variables."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(ruta, 'w', **{**perfil, 'dtype': 'float32', 'nodata': np.nan, 'compress': 'deflate'}) as dst:
        dst.write(np.asarray(matriz, dtype='float32'), 1)


# ------------------------------------------------------------------------------------------ azar espacial
def trasladar_etiquetas(d, y, rng):
    """Desplaza el campo de etiquetas un vector al azar, con retorno por los bordes (traslación toroidal), y da a cada
    roca la etiqueta de la roca más cercana a su posición desplazada. Conserva cuán agrupados están los positivos,
    pero rompe su relación con las variables."""
    x0, x1, y0, y1 = d.x.min(), d.x.max(), d.y.min(), d.y.max()
    ancho, alto = x1 - x0 + 1, y1 - y0 + 1
    dx, dy = rng.uniform(0, ancho), rng.uniform(0, alto)
    xs = (d.x.values - x0 + dx) % ancho + x0
    ys = (d.y.values - y0 + dy) % alto + y0
    return y[cKDTree(d[['x', 'y']].values).query(np.c_[xs, ys])[1]]


def mejora_sobre_base(d, y, pl, variables, params_rf):
    """ROC-AUC y PR-AUC del Random Forest (hiperparámetros fijos) y su mejora sobre la línea base, con los mismos
    pliegues. NaN si algún pliegue se queda sin positivos."""
    p_rf, p_b = np.zeros(len(d)), np.zeros(len(d))
    base = modelos()['Random Forest'][0]
    for tr, te in pl:
        if y[tr].sum() == 0:
            return dict.fromkeys(['ROC-AUC', 'PR-AUC', 'mejora ROC-AUC', 'mejora PR-AUC'], np.nan)
        rf = clone(base).set_params(**params_rf)
        rf.fit(d[variables].values[tr], y[tr], sample_weight=d.peso.values[tr])
        p_rf[te] = rf.predict_proba(d[variables].values[te])[:, 1]
        p_b[te] = linea_base(d.iloc[tr].reset_index(drop=True), y[tr], d.iloc[te])
    w = d.peso.values
    roc, pr = roc_auc_score(y, p_rf, sample_weight=w), average_precision_score(y, p_rf, sample_weight=w)
    return {'ROC-AUC': roc, 'PR-AUC': pr,
            'mejora ROC-AUC': roc - roc_auc_score(y, p_b, sample_weight=w),
            'mejora PR-AUC': pr - average_precision_score(y, p_b, sample_weight=w)}


def valor_p(observado, nulos):
    """Valor p de una cola con la corrección (1 + k) / (1 + n) de las pruebas de permutación."""
    nulos = np.asarray(nulos)
    nulos = nulos[np.isfinite(nulos)]
    return (1 + (nulos >= observado).sum()) / (1 + len(nulos))
