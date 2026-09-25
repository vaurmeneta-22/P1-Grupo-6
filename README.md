# P1 — Laboratorio Estructural Digital

**Edificio de Ingeniería — Grupo 6**

## Descripción

Laboratorio estructural digital que combina:
- Análisis estructural 3D con OpenSeesPy
- Visualización e interacción en Unity
- Realidad aumentada con AR Foundation

## Tecnologías

| Componente | Tecnología |
|-----------|-----------|
| Análisis | Python + OpenSeesPy |
| Visualización | Unity + C# (Unity 6, 6000.x) |
| AR | AR Foundation + Image Tracking |
| Datos | JSON (contrato OpenSees↔Unity) |

## Funcionalidades del visor Unity

El visor oficial del proyecto es Unity. La interfaz principal se organiza en cuatro pestañas: **Visualización / Modificaciones / Análisis / Datos**.

- **6 diafragmas rígidos** (niveles 0.00, 3.56, 7.12, 10.68, 14.24 y 17.8 m) por la huella real de piso: plano casi transparente con borde cian y triangulación de polígono cóncavo (tecla `D`).
- **HUD del visor** (`ViewerHud.cs`): barra superior con `Visualización`, `Modificaciones`, `Análisis` y `Datos`; información arriba-izquierda; leyenda de colores y casillas para alternar capas.
- **Capas alternables por familia** a través de teclas o de las casillas de la leyenda.
- **Buscador de elementos** en Visualización: permite elegir tipo e ID, enfoca automáticamente el elemento, lo resalta en amarillo y restaura vista/materiales con `Limpiar`.
- **Inspector por clic / doble clic**: al hacer clic sobre una viga, columna, muro o losa se muestra un panel con sus propiedades y, en vigas, el área tributaria y las **cargas** G (permanente) y Q (sobrecarga) calculadas en el análisis. En el modo análisis el **hover** resalta en magenta el elemento bajo el puntero y el **doble clic** sobre una columna/muro de hormigón dibuja la **curva P-M** con su punto de demanda, mientras que sobre una viga o un **metálico** reporta N/V/M/DEF de ambos extremos (`PickHighlight.cs`).
- **Modo modificaciones** (`ModificationMode.cs`): ejecuta desde Unity las variantes Base, Mod A y Mod B, muestra log, guarda historial y recarga la escena al terminar.
- **Modo análisis**: superpone al modelo los resultados del análisis lineal con OpenSees — deformada y diagramas de momento (M), axial (N) y corte (V).
- **SQ4 carga móvil**: en Análisis, doble clic sobre una losa activa martillo/carga móvil arrastrable, vigas receptoras, reparto de `P_user`, conservación de carga y flechas de transferencia.
- **Panel DATOS** (tecla `B` o botón `DATOS`, `DataPanel.cs`): ventana derecha con **6 pestañas** — Sismo (12 columnas con ux/uy/Rz por piso), Mom-Curv, P-M (fibra vs H.A.), Reacciones (con *Pintar en 3D*), Tributarias y **Diagramas 2D N/V/M** apilados — alimentadas por la API real de `AnalysisMap`.
- **Modo hormigón** (`H`): pinta todo el edificio en tonos de concreto (fundaciones más oscuras).

### Modo análisis del visor

Accesible desde la pestaña **Análisis**:

- **Vistas**: deformada (con amplificación ajustable), Momento M, Axial N y Corte V.
- **Casos de carga**: G (permanente), Q (sobrecarga), EX, EY y COMBO. En Unity los sliders `λG`, `λQ`, `λEX`, `λEY` actualizan COMBO en memoria sin reanálisis cuando se combinan casos ya calculados.
- **Color por valor**: cada elemento se pinta con un colormap azul→verde→rojo normalizado por el **percentil 90** de los valores (evita que uno o dos muros en la base dominen la escala y dejen el resto en azul). La leyenda inferior derecha muestra los rangos reales en las unidades de cada vista (mm en deformada, kN·m en momento, kN en axial/corte).
- **Doble clic en análisis**: sobre una **columna o muro de hormigón** dibuja en el inspector la **curva de capacidad** P-M (de las secciones de fibra RC, como **diamante completo simétrico**: rama +M a la derecha y su espejo −M a la izquierda) y marca el punto de demanda del caso activo (P axial y M resultante del extremo i del elemento), reportando el % de la **capacidad interpolada a esa misma carga axial** y si la demanda cae dentro de la curva (una demanda fuera de la curva se marca en rojo). Sobre una **viga** —y también sobre los **refuerzos metálicos** (columnas y vigas de acero, que no usan P-M)— muestra una tabla con los valores **numéricos** de N (axial), V (corte), M (momento resultante) y DEF (desplazamiento nodal) para los **dos extremos** i y j del elemento del caso activo. El inspector se cierra con la **X** de su esquina superior.
- **Refuerzos metálicos**: 20 elementos de acero A240ES (10 columnas `300x300x20` y 10 vigas diagonales `300x300x50`, en color amarillo) insertados entre los niveles 2–3 y 4–Techo. Su capacidad P-M está exportada en `analysis_map.json`, pero por diseño el visor solo les muestra el reporte N/V/M/DEF.
- Deformada amplificable con el deslizador `x` (escala x120 por defecto, rango 10–600). M/N/V en respuesta lineal del modelo global.

Los datos se cargan desde `Unity/Assets/StreamingAssets/analysis_map.json`, generado por `exportar_analysis_map.py` a partir de los resultados `edificio_full_results*.json`. La navegación funciona con mouse (arrastrar-rota, rueda-zoom, clic derecho-pan) y con **touch** en móvil/simulador (1 dedo-rota, 2 dedos-pinch zoom y pan, tap-seleccionar y doble tap-reporte, `CameraController.cs` + `activeInputHandler: Both`).

### Atajos de teclado

En Unity las capas se alternan con las casillas del panel izquierdo o con las teclas siguientes:

| Tecla | Acción |
|-------|--------|
| `C` | Alternar columnas |
| `X` | Alternar vigas X |
| `Y` | Alternar vigas Y |
| `W` | Alternar muros |
| `L` | Alternar lozas |
| `G` | Alternar refuerzos metálicos (columnas y vigas de acero) |
| `P` | Alternar apoyos (fundaciones) |
| `N` | Alternar nodos |
| `E` | Alternar solo los ejes |
| `D` | Alternar diafragmas rígidos |
| `TAB` | Alternar modo análisis (deformada / M / N / V) |
| `1`–`5` | Seleccionar caso G / Q / EX / EY / COMBO (modo análisis) |
| `M` / `N` / `V` / `D` | Vista Momento / Axial / Corte / Deformada (modo análisis) |
| `R` | Pintar/ocultar las reacciones en 3D (modo análisis) |
| `+` / `-` | Amplificar / reducir la escala de la deformada (10–600) |
| `B` | Abrir/cerrar el panel DATOS (Sismo, Mom-Curv, P-M, Reacciones, Tributarias, Diagramas) |
| `H` | Modo hormigón (concreto claro / fundaciones oscuras) |
| Clic izquierdo | Inspector de propiedades y cargas del elemento; en modo análisis, el **hover** resalta el elemento en magenta y el **doble clic** sobre columna/muro de hormigón dibuja la curva P-M, o sobre viga/**metálico** los valores M/V/N/DEF numéricos (cierre con **X**) |
| Arr. rotar (mouse) / 1 dedo | Orbitar la cámara |
| Zoom 2 dedos (móvil) / rueda | Zoom de la cámara |
| Pan 2 dedos (móvil) / clic derecho | Desplazar la vista (pan) |
| Tap (móvil) | Equivale al clic izquierdo (seleccionar/inspeccionar); doble tap = doble clic (P-M / N-V-M-DEF en análisis) |

## Estructura

```
├── Edificio.json         # Contrato OpenSees↔Unity (regenerado desde el visor)
├── opensees/             # Scripts de análisis estructural
│   ├── loads/            # Definición de cargas
│   ├── fiber_sections/   # Secciones de fibras RC
│   ├── analysis/         # Análisis lineal y no lineal
│   ├── opensees_edificio_v1.py  # Análisis del edificio completo (versión v1)
│   ├── opensees_edificio_v2.py  # FE principal: casos G/Q/EX/EY/COMBO, diafragmas, auditorías
│   ├── conexiones.py     # Reglas de conexión/rigidLinks y apoyos huérfanos (reglas A-E)
│   ├── superposicion.py  # Auditoría de superposición del COMBO
│   ├── verificador_camino_carga.py  # Verificación del camino de carga losa→viga→columna→fundación
│   ├── areas_tributarias.py        # Áreas y cargas tributarias de vigas
│   ├── exportar_analysis_map.py   # Resultados → analysis_map.json (modo análisis del visor)
│   ├── exportar_resultados_csv.py # Resultados → CSV
├── resultados/                    # Resultados del análisis (carpeta tipo)
│   ├── 00_readme.md               # Índice y semántica de sobrescritura
│   ├── 01_casos_base/             # edificio_full_results*.json (G/Q/EX/EY/COMBO)
│   ├── 02_reacciones/             # reacciones.csv
│   ├── 03_desplazamientos/        # desplazamientos.csv
│   ├── 04_fuerzas_elementos/      # fuerzas_elementos.csv
│   ├── 05_sismo/                  # sismo_por_piso.csv (EX/EY)
│   ├── 06_superposicion/          # verificacion.csv de la superposición COMBO
│   ├── 07_capacidad/              # M-φ y P-M: mom_curv/, pm_columnas/, pm_muros/, sensibilidad/
│   ├── 08_verificacion/           # benchmark_3d.json, verification.md, verificacion_rc.json
│   ├── 09_demanda_capacidad/      # demanda_capacidad_*.png + critica.json
│   ├── 10_figuras/                # Diagramas 2D/3D y marco_3d interactivo
│   ├── 11_mapa_visor/             # analysis_map.json, tributary_map.js, mapas del visor
├── reports/              # Entregables semana01/02/03/04 y plan de empalmes
├── Unity/                # Proyecto Unity
│   └── Assets/
│       ├── Scripts/      # EdificioLoader.cs, AnalysisMap.cs, AnalysisMode.cs,
│       │                 # CameraController.cs, PickHighlight.cs, DataPanel.cs,
│       │                 # ViewerHud.cs, ModificationMode.cs, ElementSearchPanel.cs,
│       │                 # Plot2D.cs, TributaryInspector.cs,
│       │                 # DiaphragmData.cs, ElementTag.cs
│       └── StreamingAssets/   # Edificio.json + tributary_map.js + analysis_map.json (runtime)
├── data/                 # Datos compartidos (geometría, materiales, secciones)
├── tests/                # Verificaciones (equilibrio, superposición, tributarias, empalmes, camino de carga)
├── scripts/              # Utilidades (generar_modificaciones.py, ejecutar_modificacion.py,
│                         #   parte_d_fiber.py, parte_d_muros.py,
│                         #   sensibilidad_secciones.py, comparacion_rc.py, demanda_capacidad.py)
├── regla_g_walls.json    # Selección de muros para la regla G de conexiones
└── Enunciado_Proyecto1/  # Enunciado, cronograma y recursos
```

## Flujo de datos

`opensees` calcula los resultados y escribe archivos `edificio_full_results*.json`. Luego `exportar_analysis_map.py` genera `analysis_map.json`; Unity consume `Edificio.json` y `analysis_map.json` desde `StreamingAssets`.

```
data/ ──► opensees ──► resultados/01_casos_base/edificio_full_results*.json
                     └──► exportar_analysis_map.py ──► analysis_map.json
Edificio.json ───────────────────────────────────────► Unity/StreamingAssets
```

Los tipos de elemento soportados por el modelo: `column`, `beam_x`, `beam_y`, `wall`, `loza`, `steel_column` y `steel_beam` (acero A240ES). El orden de elementos debe mantenerse consistente entre `Edificio.json` y `analysis_map.json` para que el modo análisis indexe correctamente.

El modelo actual contiene **536 nodos, 722 elementos** (118 columnas, 141 vigas X, 165 vigas Y, 79 muros, 199 lozas, 10 columnas y 10 vigas metálicas) y **64 apoyos fijos**. Los valores se guardan en **cm** en el JSON.

## Ejecución

### OpenSeesPy
El FE principal es `opensees_edificio_v2.py`. Cada caso construye el modelo desde cero (`ops.wipe`) y exporta su archivo de resultados:

```bash
cd opensees
python opensees_edificio_v2.py --case G     # → resultados/01_casos_base/edificio_full_results.json
python opensees_edificio_v2.py --case Q     # → resultados/01_casos_base/edificio_full_results_Q.json
python opensees_edificio_v2.py --case EX    # → resultados/01_casos_base/edificio_full_results_EX.json
python opensees_edificio_v2.py --case EY    # → resultados/01_casos_base/edificio_full_results_EY.json
python opensees_edificio_v2.py --case COMBO --lambda-g 1.2 --lambda-q 1.0 --lambda-ex 1.4 --lambda-ey 1.4
                                            # → resultados/01_casos_base/edificio_full_results_COMBO.json
```

- **G**: peso propio + losa permanente; **Q**: sobrecarga de uso; **EX/EY**: sismo pseudostático en X/Y (carga lateral en el centro de masa de cada diafragma, `F = α·(G + 0.5·Q)` con `α=0.20`).
- **COMBO**: superposición `R = λG·G + λQ·Q + λEX·EX + λEY·EY`, concurrente en X e Y. Sin argumentos usa los defaults `λG=λQ=λEX=λEY=1.0`; pasar explícitamente los lambdas para cualquier otra combinación.
- El script imprime auditorías de equilibrio (ΣR = W), conservación de carga de losa, diafragma rígido, masa sísmica por piso y superposición del COMBO. Si usas los 5 casos, verifica cada resultado y luego regenera el mapa del visor.

También disponible: `benchmark_3d.py` (módulo de prueba 2D/3D) y `superposicion.py` (auditoría de la combinación; al correr completo exporta el resumen a `resultados/06_superposicion/verificacion.csv`). `exportar_analysis_map.py` adicionalmente exporta el sismo por piso a `resultados/05_sismo/sismo_por_piso.csv`.

### Modo análisis del visor (regenerar resultados)
Los resultados del análisis (deformada, M/N/V por caso y capacidad P-M) se exportan a `resultados/11_mapa_visor/analysis_map.json` para Unity. Regenerarlos tras un análisis nuevo:

```bash
cd opensees
python exportar_analysis_map.py
```

La capacidad P-M se genera con `scripts/parte_d_fiber.py` (columna 70×70 y muro 30×356) y `scripts/parte_d_muros.py` (los **14 muros del contrato restantes**, con la enfierradura proporcional de `sections.muro_tipificado()`). Las curvas P-M y M-φ se escriben en `resultados/07_capacidad/` (`mom_curv/`, `pm_columnas/`, `pm_muros/`). Los diagramas P-M se dibujan como **diamante completo simétrico** (rama ±M, espejo por simetría de la sección). Para el acero, `exportar_analysis_map.py` calcula las curvas P-M de los tubos `300×300×20` y `300×300×50` (elásticas, fy=240 MPa, `A` y `Zp`) en `capacidad.steel`; el visor no las dibuja (los metálicos muestran N/V/M/DEF en su lugar). El visor busca cada curva por el nombre de sección del elemento.

Además, al regenerar resultados de capacidad se corre el resto del módulo de capacidad (`scripts/`), que sobrescribe `resultados/`:

```bash
python scripts/sensibilidad_secciones.py   # audita convergencia de la malla de fibras → 07_capacidad/sensibilidad/
python scripts/comparacion_rc.py           # verificación RC (bloque ACI/NCh vs fiber) → 08_verificacion/verificacion_rc.json
python scripts/demanda_capacidad.py        # barre 128 columnas + 79 muros con el COMBO → 09_demanda_capacidad/
```

Luego copiar/sincronizar el mapa con `Unity/Assets/StreamingAssets/analysis_map.json` y abrir Unity.

### Unity
1. Abrir `Unity/` como proyecto en Unity Hub (requiere Unity 6 / 6000.x).
2. Al abrir por primera vez Unity regenera `Library/` y los paquetes (toma unos minutos).
3. Pulsar Play para ver el edificio: columnas, vigas, muros, lozas y los 6 diafragmas.
4. Usar las pestañas `Visualización`, `Modificaciones`, `Análisis` y `Datos`.
5. En `Visualización`, buscar por tipo+ID o hacer clic en un elemento para abrir su inspector.
6. En `Modificaciones`, aplicar `Base`, `Mod A` o `Mod B` desde Unity.
7. En `Análisis`, usar sliders `G/Q/EX/EY`, deformada, M/N/V, reacciones y SQ4.

Si se actualizó `Edificio.json`, copiarlo a `Unity/Assets/StreamingAssets/Edificio.json`. El inspector por clic lee sus cargas desde `StreamingAssets/tributary_map.js`; ambos deben estar sincronizados. El modo análisis lee `StreamingAssets/analysis_map.json`.

### Modificaciones reproducibles

Desde Unity: pestaña **Modificaciones** → `Restaurar Base`, `Aplicar Mod A` o `Aplicar Mod B`.

También se puede ejecutar por terminal:

```bash
python scripts/generar_modificaciones.py
python scripts/ejecutar_modificacion.py --tag modA --json Edificio_mod_A.json --element 147 --unity
python scripts/ejecutar_modificacion.py --tag modB --json Edificio_mod_B.json --element 76 --unity
python scripts/ejecutar_modificacion.py --restore
```

- **Mod A:** viga 147, sección 60×80 → 50×75 cm.
- **Mod B:** nodo 1, apoyo empotrado → articulado (`DOF=[1,1,1,0,0,0]`).
- Cambiar sección/apoyo requiere reanálisis; mover sliders de casos ya calculados no.

## Conexiones y camino de carga

- **Conexiones** (`opensees/conexiones.py`): implementa las reglas A-E que deciden qué nodos se conectan al FE con `rigidLink`, qué apoyos quedan fijos y cuáles "huérfanos" se soportan verticalmente. La selección de muros para la regla G se configura en `regla_g_walls.json`.
- **Camino de carga** (`opensees/verificador_camino_carga.py` + `tests/test_camino_carga.py`): verifica que cada losa se apoye y transmita su carga a través de vigas → columnas/muros → fundación, sin tramos perdidos ni elementos "flotantes".
- **Empalmes viga-viga** (`tests/test_empalmes_viga_viga.py` + `reports/plan_empalmes_viga_viga.md`): documenta cómo se subdividen las vigas (reglas B/F) y se conectan entre sí y con los muros; el visor dibuja las fracciones reales del FE para que el doblez del empalme se vea y no parezca flotar.

## Verificaciones

```bash
cd tests
python test_equilibrium.py
python test_superposicion.py
python test_areas_tributarias.py
python test_camino_carga.py
python test_empalmes_viga_viga.py
python test_fiber_sections.py
```

Además hay verificaciones *ad hoc* en `opensees/test_asymmetric.py`, `opensees/test_eleforce.py`, `opensees/verificador_camino_carga.py`, `fiber_sections/verification_ha.py` y en el módulo de capacidad (`scripts/sensibilidad_secciones.py`, `scripts/comparacion_rc.py`, `scripts/demanda_capacidad.py`). El detalle del modelo (masa por piso, momentos, equilibrios) queda auditado en consola por `opensees_edificio_v2.py`; resumen en `resultados/08_verificacion/verification.md`, con resultados RC en `verificacion_rc.json`.

## Ciclo de desarrollo

```
Issue → Plan → Build → Test → Review → Merge
```

## Documentación

- [Enunciado del proyecto](Enunciado_Proyecto1/)
- [Agentes IA](AGENTS.md)
- [Avance Semana 3 (entregable)](reports/semana03.md) — casos base, curvas M-φ/P-M, verificación RC y demanda-capacidad
- [Avance Semana 4 (entregable)](reports/semana04.md) — diagramas 2D M/V/N en el visor, auditoría de la convención de esfuerzos de extremo y **traspaso completo del visor a Unity** (modo análisis, HUD, doble clic P-M / N-V-M-DEF y panel DATOS)
