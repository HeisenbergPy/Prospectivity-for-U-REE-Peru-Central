# **Prospectivity for "U - REE" - Peru Central**

![Prospectivity for "U - REE" - Peru Central](recursos/portada.png)

[![Pruebas](https://github.com/HeisenbergPy/Prospectivity-for-U-REE-Peru-Central/actions/workflows/pruebas.yml/badge.svg)](https://github.com/HeisenbergPy/Prospectivity-for-U-REE-Peru-Central/actions/workflows/pruebas.yml)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Jupyter](https://img.shields.io/badge/Jupyter-cuadernos-F37626?logo=jupyter&logoColor=white)
![uv](https://img.shields.io/badge/entorno-uv-de5fe9)
![Licencia](https://img.shields.io/badge/licencia-MIT-forestgreen)
[![Datos](https://img.shields.io/badge/datos-Google%20Drive-4285F4?logo=googledrive&logoColor=white)](https://drive.google.com/drive/folders/17-0XKJ0bYfI-5cKTVCm1R5XPFr9zsT3t?usp=drive_link)

**Autores:** Carlos Manuel Gutiérrez Cruzado y Félix Bryan Cordero Escobar<br>
**Curso:** Geocomputación (1GEO20), Pontificia Universidad Católica del Perú, semestre 2026-II

# **1. Introducción**

---
En el Perú no hay radiometría aérea pública, que es la herramienta usual para explorar uranio. Lo que existe son
datos de INGEMMET, del Instituto Peruano de Energía Nuclear (IPEN) y de modelos globales, tomados en distintos años y
analizados con métodos distintos. Antes de usarlos juntos en un estudio de prospectividad, en este trabajo
comparamos una misma variable obtenida de varias fuentes y analizamos cómo se relaciona el uranio con otras
variables.

Preguntas:

1. ¿El modelo global de gravedad XGM2019e reproduce la anomalía de Bouguer de las estaciones de INGEMMET?
2. ¿El uranio en roca medido por distintas instituciones es comparable?
3. ¿Con qué variables se relaciona el uranio (Th, SiO₂, Be en sedimentos y gravedad)?

**Área de estudio:** rectángulo de 110 × 140 km (15 400 km²) en la Cordillera Oriental de Junín y Pasco, en
WGS 84 / UTM 18S (EPSG:32718).<br>
**Periodo:** los datos son de 1991 a 2024, según la fuente.

# **2. Datos**

---
Los datos del área de estudio están en [`datos/`](datos/) (18 MB), así que el repositorio funciona apenas se
clona. La misma carpeta está en
[Google Drive](https://drive.google.com/drive/folders/17-0XKJ0bYfI-5cKTVCm1R5XPFr9zsT3t?usp=drive_link).
En [`datos/manifiesto.csv`](datos/manifiesto.csv) está la fuente, la forma de acceso y la huella sha256 de cada
archivo, y en [`datos/LEEME.md`](datos/LEEME.md) los campos, las licencias y cómo se obtuvo cada fuente.

| Variable | Fuente | Formato | Acceso | En el área |
|---|---|---|---|---:|
| Anomalía de Bouguer | Estaciones gravimétricas de INGEMMET | Shapefile | Servicio REST de GEOCATMIN | 192 estaciones |
| Anomalía de Bouguer | Modelo global XGM2019e + ETOPO1 (Zingerle et al., 2020) | GeoTIFF | Coeficientes armónicos de ICGEM | 100 % |
| U en roca | Litogeoquímica de INGEMMET | Shapefile | GEOCATMIN | 358 rocas (330 con U) |
| U en roca | Base de Datos Geoquímicos 2022 de INGEMMET | Shapefile | GEOCATMIN | 382 rocas (235 con U) |
| U en roca | Proyecto GE27 de INGEMMET | Shapefile | GEOCATMIN | 48 muestras (45 rocas y 3 suelos) |
| U en roca | IPEN (Valencia y Mamani, 2013; Valencia, 2016) | Shapefile | Transcripción de tablas de PDF | 20 muestras (19 rocas) |
| U en roca | Boletín B-74 de INGEMMET (Carpio et al., 2021) | Shapefile | Transcripción de anexos de PDF | 7 rocas |
| Be, La, Y en sedimentos | Sedimentos de quebrada de INGEMMET | Shapefile | GEOCATMIN | 720 muestras |
| Elevación | Copernicus DEM GLO-90 | GeoTIFF | Descarga libre (AWS) | 100 % |

La grilla de XGM2019e la calculamos nosotros a partir de los coeficientes del modelo, porque las descargas de ICGEM
fallaban. El script [`scripts/sintesis_xgm2019e.py`](scripts/sintesis_xgm2019e.py) la vuelve a calcular (la diferencia
con la de ICGEM es menor que 0,0001 mGal) y genera además el modelo en cada estación y una grilla en la superficie,
que se usan en GC02 y GC03.

# **3. Instalación**

---
Se necesita `git` y [uv](https://docs.astral.sh/uv/). uv instala Python 3.12 y las mismas versiones de librerías
que están en `uv.lock`.

```bash
git clone https://github.com/HeisenbergPy/Prospectivity-for-U-REE-Peru-Central.git
cd Prospectivity-for-U-REE-Peru-Central
uv sync
```

Para correr las pruebas:

```bash
uv run pytest
```

Sin uv, en un entorno de Python 3.12: `pip install -e . pytest`.

# **4. Estructura**

---
![Flujo de trabajo del repositorio](recursos/flujo.png)

```
datos/        datos del área y manifiesto con las huellas sha256
geocomp/      funciones que usan los cuadernos
cuadernos/    GC01, GC02 y GC03
scripts/      descarga de las fuentes y síntesis de XGM2019e
tests/        pruebas de las funciones y de los datos
figuras/      figuras que generan los cuadernos (PNG y SVG)
recursos/     imágenes de este README
```

| Cuaderno | Contenido | Entrega |
|---|---|---|
| [GC01 - Acceso a los datos y exploración](cuadernos/GC01_avance_exploracion.ipynb) | Integridad de los datos, fuentes, primera comparación, cobertura y periodo | Parcial (16/10/2026) |
| [GC02 - Validación de las fuentes](cuadernos/GC02_validacion_fuentes.ipynb) | Gravedad: reducción de las estaciones, modelo en la superficie, corrección de terreno. Uranio: pares de muestras, método analítico y tipo de roca | Final (22/11/2026) |
| [GC03 - Relación del uranio con otras variables](cuadernos/GC03_relacion_variables.ipynb) | U frente a Th, SiO₂, Be en sedimentos y gravedad | Final (22/11/2026) |

| Módulo | Qué hace |
|---|---|
| `geocomp/rutas.py` | Rutas de los archivos y sistemas de coordenadas |
| `geocomp/acceso.py` | Descargas de GEOCATMIN, ICGEM y AWS, y verificación de las huellas sha256 |
| `geocomp/lectura.py` | Lectura de las capas, química de texto a número (`'<2.00'`, `'########'`) y depuración de menas, vetas y réplicas |
| `geocomp/espacial.py` | Valores de rásteres en puntos, pares de muestras cercanas, reproyección y cobertura |
| `geocomp/gravedad.py` | Síntesis armónica, anomalía de Bouguer, corrección de terreno y separación regional-residual |
| `geocomp/estadistica.py` | Sesgo, RMS, Bland-Altman, bootstrap, regresión logarítmica y correlación parcial |
| `geocomp/graficos.py` | Estilo de las figuras, mapas y diagramas geoquímicos |

# **5. Ejecución**

---
Abrir los cuadernos:

```bash
uv run jupyter notebook
```

Ejecutar los tres cuadernos desde la terminal (los resultados quedan en `salida/` y los originales no cambian):

```bash
uv run jupyter nbconvert --to notebook --execute cuadernos/*.ipynb --output-dir salida
```

Volver a descargar las fuentes y compararlas con `datos/`, y rehacer la síntesis de XGM2019e (necesitan internet; la
síntesis descarga 420 MB de coeficientes):

```bash
uv run python scripts/descargar_datos.py
uv run python scripts/sintesis_xgm2019e.py
```

Con cada cambio, GitHub Actions instala el entorno desde cero, corre las pruebas y ejecuta los tres cuadernos
([`pruebas.yml`](.github/workflows/pruebas.yml)). La descarga y la síntesis se pueden correr a mano desde la pestaña
Actions ([`fuentes.yml`](.github/workflows/fuentes.yml)).

# **6. Resultados**

---
![Resultados principales de GC02 y GC03](recursos/resultados.png)

**Gravedad.** Las estaciones de INGEMMET tienen anomalía de Bouguer simple (ρ = 2670 kg/m³, sin corrección de
terreno); lo comprobamos recalculándolas con su gravedad observada. En GC01 comparamos con la grilla calculada sobre
el elipsoide y la diferencia tenía una desviación de 44 mGal. Calculando el modelo a la altura de cada estación baja
a 26 mGal, y en las estaciones de más de 3000 m pasa de 66 a 9 mGal. Los dos grupos de signo opuesto que vimos en
GC01 se debían a esto. Todavía queda un sesgo que cambia con la elevación (unos +30 mGal en los valles y −20 mGal en
la puna), por eso el modelo sirve para el patrón regional pero no reemplaza a las estaciones.

![Diferencia entre el modelo y las estaciones](figuras/GC02_03_mapas_diferencia.png)

**Uranio.** En pares de muestras a menos de 1 km, BDG 2022 da una mediana de 1,3 veces el U de la litogeoquímica
(p = 0,03). La diferencia está sobre todo en rocas básicas muestreadas en minas; en las rocas muy ácidas las dos
fuentes dan lo mismo, y GE27 coincide con la litogeoquímica. La digestión parcial de BDG da menos U. Entre muestras
cercanas el U puede variar de 0,2 a 11 veces, mucho más que la diferencia entre fuentes.

![U de BDG 2022 por método analítico y por clase de SiO2](figuras/GC02_07_metodo_y_litologia.png)

**Relación con otras variables.** El U se relaciona con el Th de la misma roca (ρ = 0,80), con el SiO₂ (en la
litogeoquímica el U se multiplica por 1,9 por cada 10 % de SiO₂) y con el Be del sedimento de quebrada más cercano
(ρ = 0,41, también al controlar la elevación). Con la gravedad la correlación es de −0,12, pero desaparece cuando se
controla la posición este-oeste (−0,03), porque las dos variables cambian de oeste a este. La anomalía residual
tampoco da un resultado estable.

![U de la roca y Be del sedimento cercano](figuras/GC03_03_uranio_berilio.png)

# **7. Referencias**

---
- Barthelmes, F. (2013). [*Definition of functionals of the geopotential and their calculation from spherical harmonic models*](https://doi.org/10.2312/GFZ.b103-0902-26) (Scientific Technical Report STR09/02). GFZ Potsdam.
- Bland, J. M., y Altman, D. G. (1986). [Statistical methods for assessing agreement between two methods of clinical measurement](https://doi.org/10.1016/S0140-6736(86)90837-8). *The Lancet, 327*(8476), 307-310.
- Carpio et al. (2021). [*Prospección del litio en el norte y centro del Perú*](https://hdl.handle.net/20.500.12544/3542) (Boletín B-74). INGEMMET.
- Cuney, M. (2014). [Felsic magmatism and uranium deposits](https://doi.org/10.2113/gssgfbull.185.2.75). *Bulletin de la Société Géologique de France, 185*(2), 75-92.
- European Space Agency (2021). [*Copernicus Global Digital Elevation Model* (GLO-90)](https://doi.org/10.5069/G9028PQB). Distribuido por OpenTopography.
- Hammer, S. (1939). [Terrain corrections for gravimeter stations](https://doi.org/10.1190/1.1440495). *Geophysics, 4*(3), 184-194.
- Hofmann-Wellenhof, B., y Moritz, H. (2006). [*Physical geodesy*](https://doi.org/10.1007/978-3-211-33545-1) (2.ª ed.). Springer.
- LaFehr, T. R. (1991). [Standardization in gravity reduction](https://doi.org/10.1190/1.1443137). *Geophysics, 56*(8), 1170-1178.
- Mišković, A., Spikings, R. A., Chew, D. M., Košler, J., Ulianov, A., y Schaltegger, U. (2009). [Tectonomagmatic evolution of Western Amazonia: Geochemical characterization and zircon U-Pb geochronologic constraints from the Peruvian Eastern Cordilleran granitoids](https://doi.org/10.1130/B26488.1). *GSA Bulletin, 121*(9-10), 1298-1324.
- Moritz, H. (2000). [Geodetic Reference System 1980](https://doi.org/10.1007/s001900050278). *Journal of Geodesy, 74*(1), 128-133.
- Rudnick, R. L., y Gao, S. (2003). [Composition of the continental crust](https://doi.org/10.1016/B0-08-043751-6/03016-4). En *Treatise on Geochemistry* (vol. 3, pp. 1-64). Elsevier.
- Valencia y Mamani (2013). En *Informe Científico Tecnológico 2011* (pp. 79-84). Instituto Peruano de Energía Nuclear.
- Valencia (2016). En *Informe Científico Tecnológico*, vol. 14 (p. 131). Instituto Peruano de Energía Nuclear.
- Zingerle, P., Pail, R., Gruber, T., y Oikonomidou, X. (2020). [The combined global gravity field model XGM2019e](https://doi.org/10.1007/s00190-020-01398-0). *Journal of Geodesy, 94*, 66.

# **8. Declaración de uso de inteligencia artificial**

---
Se utilizó una herramienta de inteligencia artificial generativa como apoyo en la edición estética de las gráficas:
formato, paleta de colores, tipografía y composición de las figuras y de las imágenes de este README.

# **9. Licencia y cita**

---
El código tiene licencia MIT ([`LICENSE`](LICENSE)). Los datos mantienen la licencia y la cita de su fuente
([`datos/LEEME.md`](datos/LEEME.md)). Para citar el trabajo se puede usar *Cite this repository* en GitHub o
[`CITATION.cff`](CITATION.cff).
