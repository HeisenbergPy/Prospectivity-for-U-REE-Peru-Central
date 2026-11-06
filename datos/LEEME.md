# Datos del área de estudio

Datos crudos tal como se obtuvieron de cada fuente, recortados al área de estudio (salvo los departamentos, ver la tabla). **No se editan**: toda la limpieza
y la conversión se hacen en el código (`geocomp/lectura.py`). Cada archivo tiene registrada su huella sha256 en
`manifiesto.csv`; la prueba `tests/test_datos.py` y la sección 2 del cuaderno GC01 comprueban que no hayan
cambiado.

Copia idéntica en Google Drive: https://drive.google.com/drive/folders/17-0XKJ0bYfI-5cKTVCm1R5XPFr9zsT3t?usp=drive_link

| Carpeta | Archivo | Contenido |
|---|---|---|
| `area_estudio/` | `AOI.shp` | Rectángulo de 110 × 140 km en UTM 18S (440–550 km E, 8700–8840 km N) |
| `contexto/` | `departamentos.shp` | Departamentos del Perú (INGEMMET), solo para el mapa de ubicación. Es el único archivo modificado: se quitaron los lagos y se simplificó el contorno a 0,005° (~500 m), para que pese 0,2 MB en lugar de 6 MB |
| | `provincias.shp`, `capitales.shp` | Límites provinciales y capitales de distrito y provincia (INGEMMET) |
| `gravedad/` | `gravimetria_estaciones.shp` | 192 estaciones: `GRAV_MGAL` (gravedad observada) y `BOUG_MGAL` (anomalía de Bouguer, mGal) |
| | `gravedad_XGM2019e_bouguer.tif` | Anomalía de Bouguer simple del modelo XGM2019e (mGal), grilla de 0,025° sobre el elipsoide (h = 0) |
| | `gravedad_XGM2019e_bouguer_superficie.tif` | La misma grilla evaluada en la superficie del modelo (h = H + N en cada nodo); la usa GC03 |
| | `xgm2019e_estaciones.csv` | Modelo en cada estación: ondulación del geoide, topografía del modelo y Bouguer a h = 0 y en la superficie; la usa GC02 |
| `geoquimica/` | `litogeoquimica_roca.shp` | Química de rocas de INGEMMET (texto original); `QUIMICA_RE` es la referencia de cada dato |
| | `rocas_BDG_2022.shp` | Base de Datos Geoquímicos 2022 (proyectos GE33 y GE36); `F_MTRA` es la fecha (ms desde 1970) |
| | `materia_critica_U.shp` | Proyecto GE27 de INGEMMET (U en ppm); `GEOLOG_A` describe la muestra |
| | `ipen_san_ramon.shp` | 19 rocas y 1 mineral (torbernita) del IPEN, transcritos de dos informes |
| | `carpio2021_B74.shp` | 17 muestras del Boletín B-74; `EN_AOI` indica si están dentro del área |
| | `sedimentos_quebrada.shp` | 720 sedimentos de quebrada (Be, La, Y en ppm; sin U en esta área) |
| `elevacion/` | `dem_copernicus_90m.tif` | Copernicus DEM GLO-90 (m), celda de 3 segundos de arco (~90 m) |
| `modelo/` | `variables/*.tif` | 40 variables del modelo de prospectividad en la grilla de 250 m (440 × 560 celdas, UTM 18S); son datos **integrados**, no crudos (ver abajo) |
| | `rocas_variables.csv` | 794 rocas con su fuente, conjunto (entrenamiento o franja de prueba), peso por afloramiento, grupo geológico, U, ΣREE, etiquetas y el valor de las 40 variables en su ubicación |
| | `catalogo_variables.csv` | Familia, descripción y porcentaje del área con dato de cada variable |
| | `franja_prueba.shp` | Franja sur de 20 km reservada para la evaluación final (440–550 km E, 8700–8720 km N) |

## Cómo se obtuvo cada fuente

- **GEOCATMIN (INGEMMET):** servicio ArcGIS REST, https://geocatmin.ingemmet.gob.pe/arcgis/rest/services/. El servicio
  no admite paginación, así que se piden los identificadores dentro de la caja del área y luego se descargan por
  bloques (`geocomp/acceso.py`, función `descargar_capa`). El servicio y la capa de cada archivo están en
  `manifiesto.csv`.
- **IPEN y Boletín B-74:** tablas transcritas de los informes en PDF. La página de cada valor está en el campo
  `FUENTE` (IPEN) y en la referencia del boletín.
- **XGM2019e:** el servicio de grillas de ICGEM (GFZ Potsdam) calculó la grilla, pero sus descargas fallaban (error
  HTTP 502). Por eso se descargaron los coeficientes oficiales del modelo (`XGM2019e_2159.gfc`) y de la topografía
  (`etopo1-2250.gfc`) y se hizo la síntesis armónica en Python con el mismo funcional de ICGEM
  (`gravity_anomaly_bg`):
  - grado máximo 2190, sobre el elipsoide GRS80 (h = 0);
  - Δg_B = Δg − 2πGρH, con ρ = 2670 kg/m³.

  El resultado coincide con las estadísticas que publica ICGEM para la misma grilla: mínimo y máximo con una
  diferencia de 0,01 mGal o menos. Resolución real: ~9 km. La síntesis se rehace con
  `uv run python scripts/sintesis_xgm2019e.py` (descarga los 420 MB de coeficientes a `descargas/`, reproduce la
  grilla con una diferencia máxima de 0,00002 mGal y calcula la grilla de superficie y la tabla de las estaciones).
- **Copernicus DEM:** teselas GLO-90 de libre acceso en https://copernicus-dem-90m.s3.amazonaws.com.

## Datos integrados del modelo (`modelo/`)

A diferencia del resto de la carpeta, `modelo/` contiene variables ya calculadas: cada fuente se llevó a la grilla de
250 m del área. GC04 (sección 2) comprueba que tres de ellas se rehacen exactamente con los datos de este repositorio
(`sed_Be`, `grav_XGM2019e` y `elevacion`). El resto se calculó con capas de INGEMMET que no se copian aquí por su
tamaño:

| Familia | Variables | Fuente y cálculo |
|---|---|---|
| Geología | `clase_*`, `pulso_*`, `litologia_felsica`, `dist_PT_km`, `dist_contacto_km`, `dist_san_ramon_km` | Geología 1:50 000 de INGEMMET (GEOCATMIN), rasterizada; pulsos según edades U-Pb (Mišković et al., 2009); distancias euclidianas en km |
| Estructural | `dist_falla_km`, `dens_falla`, `dist_falla_regional_km`, `dens_pliegue` | Fallas y ejes de pliegue 1:50 000 y sistemas de fallas regionales de INGEMMET; densidad = km de línea por km² en un radio de 5 km |
| Sedimentos | `sed_La`, `sed_Y`, `sed_Be`, `sed_K`, `sed_La_Y`, `sed_densidad` | Sedimentos de quebrada de INGEMMET: promedio gaussiano del log10 (banda 2,5 km, radio máximo 7,5 km) |
| Sedimentos (cuenca) | `cue_*` | log10 del sedimento cuya cuenca de drenaje contiene la celda (D8 sobre el DEM de 90 m; donde se superponen cuencas, prevalece la más pequeña) |
| Geofísica | `gravedad_bouguer`, `grav_dist_estacion_km`, `grav_XGM2019e`, `grav_residual`, `mag_EMAG2`, `mag_gradiente` | Estaciones de INGEMMET interpoladas (vacío a más de 15 km), XGM2019e (este repositorio), EMAG2v3 (Meyer et al., 2017) y su gradiente horizontal |
| Relieve | `elevacion`, `pendiente`, `rugosidad` | Copernicus DEM GLO-90 promediado a 250 m |
| Landsat | `ls_oxidos_fe`, `ls_arcillas`, `ls_ferroso`, `ls_ndvi` | Mediana de 32 escenas Landsat 8/9 Colección 2 nivel 2 de la estación seca 2023-2025 (USGS) |

Las etiquetas: `U_pos` = 1 si U ≥ 6,7 ppm (rocas ígneas y metamórficas) y `SREE_pos` = 1 si la suma de las 14 REE es
≥ 478 ppm (percentil 85); vacías donde la roca no es apta. `peso` = 1/n en cada grupo de duplicados (`grupo_dup`), de
modo que cada afloramiento cuenta una vez.

## Comprobar la copia con las fuentes

`uv run python scripts/descargar_datos.py` vuelve a descargar las cinco capas de GEOCATMIN, las teselas del DEM y los
coeficientes de ICGEM en `descargas/` (carpeta que no se sube) y las compara con esta copia, sin modificarla. El
25/10/2026, las cinco capas coincidieron registro por registro (a menos de 1 m) y el DEM celda por celda.

Servicios de GEOCATMIN: litogeoquímica `SERV_GEOLOGIA_REGIONAL/MapServer/2`, GE27 `SERV_MATERIA_PRIMA_CRITICA/MapServer/31`,
BDG 2022 `SERV_GEOQUIMICA_2022/MapServer/10`, sedimentos `SERV_GEOQUIMICA/MapServer/1` y estaciones
`SERV_GEOFISICA/MapServer/4`.

## Licencias y citas

| Fuente | Condición de uso |
|---|---|
| INGEMMET (GEOCATMIN, boletines) | Información pública del Estado peruano; citar a INGEMMET como fuente |
| IPEN | Informes científicos públicos; citar los informes |
| XGM2019e | CC BY 4.0. Zingerle, P., Pail, R., Gruber, T., Oikonomidou, X. (2019). GFZ Data Services. https://doi.org/10.5880/ICGEM.2019.007 |
| ETOPO1 | Amante, C., y Eakins, B. W. (2009). NOAA. https://doi.org/10.7289/V5C8276M |
| EMAG2v3 | Meyer, B., Saltus, R., y Chulliat, A. (2017). NOAA NCEI. https://doi.org/10.7289/V5H70CVX |
| Landsat 8/9 Colección 2 | Dominio público, cortesía del U.S. Geological Survey |
| Copernicus DEM GLO-90 | Licencia Copernicus de uso libre con atribución: © DLR e.V. 2010–2014 y © Airbus Defence and Space GmbH 2014–2018, provisto bajo COPERNICUS por la Unión Europea y la ESA |
