# resultados/ — Resultados del P1 (Grupo 6)

Carpeta única de resultados del análisis estructural del Edificio de
Ingeniería. Cada subcarpeta corresponde a un tipo de resultado.

## Índice

| Carpeta | Contenido | Se genera con |
|---------|-----------|---------------|
| `01_casos_base/` | `edificio_full_results{,_Q,_EX,_EY,_COMBO}.json` (G, Q, EX, EY) | `python opensees/opensees_edificio_v2.py` |
| `02_reacciones/` | `reacciones.csv` (apoyos, kN y kN·m) | `python opensees/exportar_resultados_csv.py` |
| `03_desplazamientos/` | `desplazamientos.csv` (nodos, mm y rad) | `python opensees/exportar_resultados_csv.py` |
| `04_fuerzas_elementos/` | `fuerzas_elementos.csv` (extremo i, global) | `python opensees/exportar_resultados_csv.py` |
| `05_sismo/` | `sismo_por_piso.csv` (EX/EY por piso) | `python opensees/exportar_analysis_map.py` |
| `06_superposicion/` | `verificacion.csv` (checks directa vs explícita) | `python opensees/superposicion.py` |
| `07_capacidad/` | `mom_curv/` (M-φ columna), `pm_columnas/`, `pm_muros/`, `sensibilidad/` | `scripts/parte_d_fiber.py`, `scripts/parte_d_muros.py`, `scripts/sensibilidad_secciones.py` |
| `08_verificacion/` | `benchmark_3d.json`, `verification.md`, `verificacion_rc.json` | `benchmark_3d.py`, `scripts/comparacion_rc.py` |
| `09_demanda_capacidad/` | `demanda_capacidad_*.png`, `demanda_capacidad_critica.json` | `scripts/demanda_capacidad.py` |
| `10_figuras/` | Diagramas 2D/3D, `marco_3d_interactivo.html`, `marco_3d_resultados.png` | `opensees/benchmark_3d.py` + visualizadores |
| `11_mapa_visor/` | `analysis_map.js`, `tributary_map.js`, `deformada_elements.js` | `python opensees/exportar_analysis_map.py` |

## Semántica de sobrescritura

- Cada script escribe SIEMPRE en la misma ruta fija de su carpeta: re-ejecutarlo
  **reemplaza** el archivo anterior (nunca se acumulan versiones `_v2`, `_bak`).
- Los scripts con salida múltiple limpian su carpeta destino antes de regenerar
  (p. ej. `parte_d_muros.py` borra `pm_*` en `07_capacidad/pm_muros/`).
- Solo queda la versión de la **última corrida** de cada generador.

## Notas

- Los Cascos JSON de `01_casos_base/` son la fuente del mapa del visor y de los
  CSVs; todo lo demás se deriva de ellos.
- Los avances y planes (semana01/02/03, empalmes, PDF) viven en `reports/`.