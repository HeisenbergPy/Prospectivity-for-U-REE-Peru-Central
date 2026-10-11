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
El Perú no dispone de radiometría aérea pública, la herramienta habitual en la exploración de uranio. La información
disponible proviene de varias instituciones (INGEMMET, el Instituto Peruano de Energía Nuclear y modelos globales),
que muestrearon en épocas distintas y con laboratorios y métodos distintos. Este trabajo evalúa si esas fuentes
**concuerdan** antes de integrarlas: compara **una misma variable obtenida de fuentes distintas** y analiza
estadísticamente la **relación entre variables**.

Preguntas del trabajo:

1. ¿El modelo global de gravedad XGM2019e reproduce la anomalía de Bouguer medida en las estaciones de INGEMMET?
2. ¿El uranio en roca medido por distintas instituciones es comparable?
3. ¿Con qué variables se relaciona el uranio (Th, SiO₂, Be en sedimentos y gravedad)?

**Área de estudio:** rectángulo de 110 × 140 km (15 400 km²) en la Cordillera Oriental de Junín y Pasco, en
WGS 84 / UTM 18S (EPSG:32718). **Periodo:** los datos se adquirieron entre 1991 y 2024 según la fuente.

# **2. Datos**

---
Los datos crudos del área de estudio se incluyen en la carpeta [`datos/`](datos/) (18 MB), de modo que el
repositorio puede ejecutarse inmediatamente después de clonarlo. La carpeta de
[Google Drive](https://drive.google.com/drive/folders/17-0XKJ0bYfI-5cKTVCm1R5XPFr9zsT3t?usp=drive_link) contiene una
copia idéntica.

El archivo [`datos/manifiesto.csv`](datos/manifiesto.csv) registra la fuente, la forma de acceso y la huella sha256
de cada archivo, lo que permite verificar que los datos no fueron modificados. Los campos, las licencias y el
procedimiento de obtención se describen en [`datos/LEEME.md`](datos/LEEME.md).

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

# **3. Instalación**

---
Se requiere `git` y [uv](https://docs.astral.sh/uv/), el gestor de entornos de Python. uv instala Python 3.12 y las
versiones exactas de las librerías registradas en `uv.lock`, de modo que el entorno es idéntico en cualquier equipo.

Clonar el repositorio:

```bash
git clone https://github.com/HeisenbergPy/Prospectivity-for-U-REE-Peru-Central.git
cd Prospectivity-for-U-REE-Peru-Central
```

Crear el entorno:

```bash
uv sync
```

Ejecutar las pruebas de las funciones y de los datos:

```bash
uv run pytest
```

**Sin uv:** en un entorno de Python 3.12, el paquete se instala con:

```bash
pip install -e . pytest
```

# **4. Estructura y flujo de trabajo**

---
![Flujo de trabajo del repositorio](recursos/flujo.png)

El análisis se organiza en cuadernos de Jupyter, uno por etapa, en la carpeta [`cuadernos/`](cuadernos/). Las
funciones que emplean se encuentran en el paquete [`geocomp/`](geocomp/), y cada una cuenta con pruebas en
[`tests/`](tests/).

| Cuaderno | Contenido | Entrega | Estado |
|---|---|---|:---:|
| [GC01 - Acceso a los datos y exploración](cuadernos/GC01_avance_exploracion.ipynb) | Integridad de los datos, fuentes y forma de acceso, primera comparación de fuentes, cobertura y periodo | Parcial (16/10/2026) | ✔️ |
| GC02 - Validación de fuentes | Gravedad: estaciones frente a modelo según el relieve. Uranio: pares por método analítico y por litología | Final (22/11/2026) | ⏳ |
| GC03 - Relación entre variables | U frente a Th, SiO₂ y Be en sedimentos; gravedad en zonas de U alto y bajo | Final (22/11/2026) | ⏳ |

| Módulo de `geocomp/` | Función |
|---|---|
| `rutas.py` | Rutas de los archivos y sistemas de coordenadas |
| `acceso.py` | Consulta y descarga desde GEOCATMIN; verificación de los archivos con su huella sha256 |
| `lectura.py` | Lectura de cada capa y conversión de la química (texto como `'<2.00'` o `'########'`) a números |
| `espacial.py` | Muestreo de rásteres en puntos, pares de muestras cercanas, reproyección y cobertura en una grilla |
| `estadistica.py` | Métricas de acuerdo entre fuentes (sesgo, RMS, correlación) y resúmenes por grupo |
| `graficos.py` | Estilo de las figuras, mapas en UTM con norte y escala, números con coma decimal |

# **5. Ejecución**

---
Abrir Jupyter en el entorno del proyecto:

```bash
uv run jupyter notebook
```

Ejecutar un cuaderno completo desde la terminal sin modificar el original (el resultado se guarda en `salida/`):

```bash
uv run jupyter nbconvert --to notebook --execute cuadernos/GC01_avance_exploracion.ipynb --output-dir salida
```

En cada cambio, GitHub Actions clona el repositorio desde cero, crea el entorno, ejecuta las pruebas y ejecuta el
cuaderno GC01 completo ([`.github/workflows/pruebas.yml`](.github/workflows/pruebas.yml)). Las imágenes de este
README se generan como se indica en [`recursos/LEEME.md`](recursos/LEEME.md).

# **6. Resultados preliminares**

---
![Resultados preliminares de GC01](recursos/resultados.png)

**Gravedad.** El modelo XGM2019e reproduce el patrón regional de las estaciones (r = 0,80), aunque supera en promedio
en 12 mGal a las mediciones y su error típico (RMS) es de 44,7 mGal; a escala local no reemplaza a las estaciones.
Por encima de 3000 m, dos grupos de estaciones vecinas presentan diferencias de signo opuesto, lo que sugiere un
efecto de la campaña de medición que se evaluará en GC02.

![Comparación entre el modelo XGM2019e y las estaciones de INGEMMET](figuras/GC01_03_bouguer_comparacion.png)

**Uranio.** Las fuentes regionales presentan medianas similares (2,9 a 4,0 ppm), próximas al promedio de la corteza
superior. La mediana del IPEN (15,5 ppm) refleja un sesgo de muestreo hacia zonas con indicios conocidos, no una
diferencia de laboratorio.

![Distribución del U en roca por fuente](figuras/GC01_06_uranio_distribucion_fuentes.png)

# **7. Referencias**

---
- Carpio et al. (2021). [*Prospección del litio en el norte y centro del Perú*](https://hdl.handle.net/20.500.12544/3542) (Boletín B-74). INGEMMET.
- European Space Agency (2021). [*Copernicus Global Digital Elevation Model* (GLO-90)](https://doi.org/10.5069/G9028PQB). Distribuido por OpenTopography.
- Mišković, A., Spikings, R. A., Chew, D. M., Košler, J., Ulianov, A., y Schaltegger, U. (2009). [Tectonomagmatic evolution of Western Amazonia: Geochemical characterization and zircon U-Pb geochronologic constraints from the Peruvian Eastern Cordilleran granitoids](https://doi.org/10.1130/B26488.1). *GSA Bulletin, 121*(9-10), 1298-1324.
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
El código se distribuye bajo la licencia MIT (ver [`LICENSE`](LICENSE)). Los datos conservan la licencia y la cita de
su fuente original (ver [`datos/LEEME.md`](datos/LEEME.md)). Para citar este trabajo puede usarse la opción
*Cite this repository* de GitHub o el archivo [`CITATION.cff`](CITATION.cff).
