# Recursos gráficos del README

| Archivo | Contenido |
|---|---|
| `paneles.py` | Genera en `imagenes/` los mapas sin ejes que usan los diseños (ubicación, relieve, anomalía de Bouguer, U en roca y curvas de nivel) |
| `diseno/portada.html` | Portada del README |
| `diseno/flujo.html` | Diagrama del flujo de trabajo del repositorio |
| `diseno/resultados.html` | Resultados principales de GC02 y GC03 |
| `portada.png`, `flujo.png`, `resultados.png` | Exportación de las tres páginas anteriores (resolución 2x) |

Los diseños son páginas HTML con CSS y usan las familias tipográficas IBM Plex (Google Fonts, licencia SIL Open Font
License). Las cifras de `resultados.html` provienen de los cuadernos `cuadernos/GC02_validacion_fuentes.ipynb` y
`cuadernos/GC03_relacion_variables.ipynb`.

## Cómo regenerar las imágenes

1. Mapas de los diseños:

   ```bash
   uv run python recursos/paneles.py
   ```

2. Exportación de cada página a PNG con Microsoft Edge o Google Chrome en modo sin interfaz (ejemplo para la
   portada, desde la carpeta `recursos/`; `--virtual-time-budget` da tiempo a que carguen las fuentes):

   ```bash
   msedge --headless=new --hide-scrollbars --force-device-scale-factor=2 --virtual-time-budget=8000 --window-size=1600,640 --screenshot=portada.png diseno/portada.html
   ```

   | Página | Tamaño (px) |
   |---|---|
   | `portada.html` | 1600 × 640 |
   | `flujo.html` | 1600 × 560 |
   | `resultados.html` | 1600 × 400 |
