# Recursos gráficos del README

| Archivo | Contenido |
|---|---|
| `paneles.py` | Genera en `imagenes/` los mapas sin ejes de los diseños (`*_violeta.png`: relieve, anomalía de Bouguer, U en roca y zonas prioritarias, en tonos violeta); el de zonas lee `resultados/`, así que se ejecuta después de GC04 |
| `marco.py` | Genera en `imagenes/` los fondos de la portada y de la vista previa: panel oscuro con curvas de nivel reales del área en morado, línea gris biselada y esquina con degradado (la estética de las presentaciones del proyecto) |
| `diseno/portada.html` | Portada del README |
| `animar_portada.py` | Genera `portada.svg`, la portada del README: `portada.png` con pulsos de luz animados que recorren las curvas de nivel del panel oscuro (sin pasar sobre los textos) y un brillo lento en la esquina morada |
| `imagenes/logo_andeanx.png`, `imagenes/logo_pucp.png` | Logos de AndeanX y de la PUCP de la portada (fondo blanco convertido en transparente) |
| `diseno/flujo.html` | Diagrama del flujo de trabajo del repositorio |
| `diseno/resultados.html` | Resultados principales de GC02 y GC03 |
| `diseno/modelo.html` | Resultados de los modelos de prospectividad (GC04) |
| `diseno/vista_previa.html` | Imagen para compartir el repositorio (vista previa de GitHub, 1280 × 640) |
| `portada.png`, `flujo.png`, `resultados.png`, `modelo.png` | Exportación de las páginas anteriores (resolución 2x) |
| `vista_previa.jpg` | Exportación de `vista_previa.html` a 1280 × 640 (menos de 1 MB, como pide GitHub) |

Los diseños son páginas HTML con CSS y usan las familias tipográficas Open Sans e IBM Plex (Google Fonts, licencia
SIL Open Font License). Las cifras de `resultados.html` provienen de los cuadernos `cuadernos/GC02_validacion_fuentes.ipynb` y
`cuadernos/GC03_relacion_variables.ipynb`; las de `modelo.html`, de `cuadernos/GC04_modelo_prospectividad.ipynb`.

## Cómo regenerar las imágenes

1. Mapas y fondos de los diseños:

   ```bash
   uv run python recursos/paneles.py
   uv run python recursos/marco.py
   ```

2. Exportación de cada página a PNG con Microsoft Edge o Google Chrome en modo sin interfaz (ejemplo para la
   portada, desde la carpeta `recursos/`; `--virtual-time-budget` da tiempo a que carguen las fuentes):

   ```bash
   msedge --headless=new --hide-scrollbars --force-device-scale-factor=2 --virtual-time-budget=8000 --window-size=1600,640 --screenshot=portada.png diseno/portada.html
   ```

3. Portada animada (después de exportar `portada.png`):

   ```bash
   uv run python recursos/animar_portada.py
   ```

   | Página | Tamaño (px) |
   |---|---|
   | `portada.html` | 1600 × 640 |
   | `flujo.html` | 1600 × 560 |
   | `resultados.html` | 1600 × 400 |
   | `modelo.html` | 1600 × 620 |
   | `vista_previa.html` | 1280 × 640 (exportada con factor 2 y reducida a 1280 × 640 en JPG) |
