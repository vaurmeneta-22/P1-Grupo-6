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
| Visualización | Unity + C# (Unity 6, 6000.5.10f1) |
| AR | AR Foundation + Image Tracking |
| Datos | JSON (contrato OpenSees↔Unity) |

## Funcionalidades del visor Unity

El visor replica las interacciones del `edificio_3d.html`:

- **6 diafragmas rígidos** (niveles 0.00, 3.56, 7.12, 10.68, 14.24 y 17.8 m) por la huella real de piso: plano casi transparente con borde cian y triangulación de polígono cóncavo (tecla `D`).
- **Capas alternables por familia** a través de teclas, igual que el panel de checkboxes del HTML.
- **Inspector por clic**: al hacer clic sobre una viga, columna, muro o losa se muestra un panel con sus propiedades y, en vigas, el área tributaria y las **cargas** G (permanente) y Q (sobrecarga) calculadas en el análisis.
- **Modo análisis** (tecla `TAB` o botón central): superpone al modelo los resultados del análisis lineal con OpenSees — deformada y diagramas de momento (M), axial (N) y corte (V).
- **Modo hormigón** (`H`): pinta todo el edificio en tonos de concreto (fundaciones más oscuras).

### Modo análisis del visor (TAB)

Accesible desde `edificio_3d.html` con `TAB` o el botón `ANALISIS` de la barra superior:

- **Vistas**: deformada (con amplificación ajustable), Momento M, Axial N y Corte V.
- **Casos de carga**: G (permanente), Q (sobrecarga), EX, EY y COMBO (combinación por superposición `R = λG·G + λQ·Q + λEX·EX + λEY·EY`). El COMBO actual se exportó con `λG=1.2, λQ=1.0, λEX=1.4, λEY=1.4` (sismo X e Y simultáneos; corte basal ±21722 kN por eje). Los lambdas los define la corrida de OpenSees vía CLI (ver *Ejecución*).
- **Color por valor**: cada elemento se pinta con un colormap azul→verde→rojo normalizado por el **percentil 90** de los valores (evita que uno o dos muros en la base dominen la escala y dejen el resto en azul). La leyenda inferior derecha muestra los rangos reales en las unidades de cada vista (mm en deformada, kN·m en momento, kN en axial/corte).
- **Doble clic en análisis**: sobre una **columna o muro de hormigón** dibuja en el inspector la **curva de capacidad** P-M (de las secciones de fibra RC) y marca el punto de demanda del caso activo (P axial y M resultante del extremo i del elemento), reportando el % de la **capacidad interpolada a esa misma carga axial** y si la demanda cae dentro de la curva (una demanda fuera de la curva se marca en rojo). Sobre una **viga** —y también sobre los **refuerzos metálicos** (columnas y vigas de acero, que no usan P-M)— muestra una tabla con los valores **numéricos** de N (axial), V (corte), M (momento resultante) y DEF (desplazamiento nodal) para los **dos extremos** i y j del elemento del caso activo. El inspector se cierra con la **X** de su esquina superior.
- **Refuerzos metálicos**: 20 elementos de acero A240ES (10 columnas `300x300x20` y 10 vigas diagonales `300x300x50`, en color amarillo) insertados entre los niveles 2–3 y 4–Techo. Su capacidad P-M (tubo, fy=240 MPa) está exportada en `capacidad.steel` del `analysis_map.js`, pero por diseño el visor solo les muestra el reporte N/V/M/DEF.
- Deformada amplificable con el deslizador `x` (escala x120 por defecto, rango 10–600). M/N/V en respuesta lineal del modelo global.

Los datos se cargan desde `opensees/results/analysis_map.js`, generado por `exportar_analysis_map.py` a partir de los resultados `edificio_full_results*.json`.

### Atajos de teclado

En `edificio_3d.html` las capas se alternan con los checkboxes del panel izquierdo (Columnas, Vigas X/Y, Muros, Losas, **Metálicas**, Nodos, Ejes, Diafragmas). Teclas del HTML: `N` alterna nodos, `E` alterna sólidos+ejes y `TAB` conmuta visualización↔análisis. El visor Unity replica las capas con las teclas siguientes:

| Tecla | Acción |
|-------|--------|
| `C` | Alternar columnas |
| `X` | Alternar vigas X |
| `Y` | Alternar vigas Y |
| `W` | Alternar muros |
| `L` | Alternar lozas |
| `P` | Alternar apoyos (fundaciones) |
| `N` | Alternar nodos |
| `E` | Alternar solo los ejes |
| `D` | Alternar diafragmas rígidos |
| `TAB` | Alternar modo visualización ↔ análisis (deformada / M / N / V) |
| `H` | Modo hormigón (concreto claro / fundaciones oscuras) |
| Clic izquierdo | Inspector de propiedades y cargas del elemento (en modo análisis: **doble clic** sobre columna/muro de hormigón = curva P-M; **doble clic** sobre viga o **metálico** = valores M/V/N/DEF numéricos; cierre con **X**)|

## Estructura

```
├── edificio_3d.html      # Visor 3D interactivo (Three.js, fuente de edición del modelo)
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
│   ├── visualizar.py     # JSON → HTML (genera el visor desde el contrato)
│   ├── _rebuild_html_elements.py  # Regenera el array de elementos embebido en el HTML desde el JSON
│   ├── exportar_analysis_map.py   # Resultados → analysis_map.js (modo análisis del visor)
│   ├── exportar_resultados_csv.py # Resultados → CSV
│   └── results/          # Resultados exportados (JSON/JS)
│       ├── analysis_map.js        # Deformada, M, N, V y capacidad P-M por caso (G/Q/EX/EY/COMBO)
│       ├── edificio_full_results*.json   # Resultados por caso (G, Q, EX, EY, COMBO)
│       └── tributary_map.js        # Áreas y cargas tributarias (inspector por clic)
├── Unity/                # Proyecto Unity
│   └── Assets/
│       ├── Scripts/      # EdificioLoader.cs, CameraController.cs,
│       │                 # DiaphragmData.cs, ElementTag.cs, TributaryInspector.cs
│       └── StreamingAssets/   # Edificio.json + tributary_map.js (leídos en runtime)
├── data/                 # Datos compartidos (geometría, materiales, secciones)
├── tests/                # Verificaciones (equilibrio, superposición, tributarias, empalmes, camino de carga)
├── scripts/              # Utilidades (html_to_json.py, parte_d_fiber.py, parte_d_muros.py)
├── reports/              # Reportes de avance y del plan de empalmes viga-viga
├── regla_g_walls.json    # Selección de muros para la regla G de conexiones
├── figures/              # Figuras: P-M de columnas/muros, diagramas 2D/3D
└── Enunciado_Proyecto1/  # Enunciado, cronograma y recursos
```

## Flujo de datos

`opensees` calcula los resultados y escribe `Edificio.json`; `opensees/_rebuild_html_elements.py` regenera el array de elementos embebido en `edificio_3d.html`; Unity lee el JSON. Si el modelo se edita a mano en el visor, `scripts/html_to_json.py` devuelve esos cambios al contrato (incluidos los tipos nuevos `steel_column`/`steel_beam`, resolviendo `node_i`/`node_j` por proximidad de coordenadas):

```
data/ ──► opensees ──► Edificio.json ──► Unity (visualización)
                ▲            │
                └────────────┘  opensees/_rebuild_html_elements.py: JSON→HTML
    edificio_3d.html ──► scripts/html_to_json.py: HTML→JSON
    opensees/results/edificio_full_results*.json ──► exportar_analysis_map.py ──► analysis_map.js
```

Los tipos de elemento soportados por el modelo: `column`, `beam_x`, `beam_y`, `wall`, `loza`, `steel_column` y `steel_beam` (acero A240ES). El orden del array de elementos es **1:1** entre `edificio_3d.html`, `Edificio.json` y `analysis_map.js`: agregar elementos a uno requiere regenerar los otros dos para que el modo análisis del visor siga indexando correctamente (usar `_rebuild_html_elements.py` y `html_to_json.py` en ese orden).

El modelo actual contiene **536 nodos, 722 elementos** (118 columnas, 141 vigas X, 165 vigas Y, 79 muros, 199 lozas, 10 columnas y 10 vigas metálicas) y **64 apoyos fijos**. Los valores se guardan en **cm** en el JSON.

## Ejecución

### Visor 3D (edición del modelo)
Abrir `edificio_3d.html` en un navegador. Después de editar (agregar/quitar nodos, lozas, vigas, muros), regenerar el contrato:

```bash
python scripts/html_to_json.py          # actualiza Edificio.json desde el visor
```

### OpenSeesPy
El FE principal es `opensees_edificio_v2.py`. Cada caso construye el modelo desde cero (`ops.wipe`) y exporta su archivo de resultados:

```bash
cd opensees
python opensees_edificio_v2.py --case G     # → results/edificio_full_results.json
python opensees_edificio_v2.py --case Q     # → results/edificio_full_results_Q.json
python opensees_edificio_v2.py --case EX    # → results/edificio_full_results_EX.json
python opensees_edificio_v2.py --case EY    # → results/edificio_full_results_EY.json
python opensees_edificio_v2.py --case COMBO --lambda-g 1.2 --lambda-q 1.0 --lambda-ex 1.4 --lambda-ey 1.4
                                            # → results/edificio_full_results_COMBO.json
```

- **G**: peso propio + losa permanente; **Q**: sobrecarga de uso; **EX/EY**: sismo pseudostático en X/Y (carga lateral en el centro de masa de cada diafragma, `F = α·(G + 0.5·Q)` con `α=0.20`).
- **COMBO**: superposición `R = λG·G + λQ·Q + λEX·EX + λEY·EY`, concurrente en X e Y. Sin argumentos usa los defaults `λG=λQ=λEX=λEY=1.0`; pasar explícitamente los lambdas para cualquier otra combinación.
- El script imprime auditorías de equilibrio (ΣR = W), conservación de carga de losa, diafragma rígido, masa sísmica por piso y superposición del COMBO. Si usas los 5 casos, verifica cada resultado y luego regenera el mapa del visor.

También disponible: `benchmark_3d.py` (módulo de prueba 2D/3D) y `superposicion.py` (auditoría de la combinación).

### Modo análisis del visor (regenerar resultados)
Los resultados del análisis (deformada, M/N/V por caso y capacidad P-M) se exportan a `opensees/results/analysis_map.js`, que el visor carga con `<script>`. Regenerarlos tras un análisis nuevo:

```bash
cd opensees
python exportar_analysis_map.py
```

La capacidad P-M se genera con `scripts/parte_d_fiber.py` (columna 70x70 y muro 30x356) y `scripts/parte_d_muros.py` (los **14 muros del contrato restantes**, con la enfierradura proporcional de `sections.muro_tipificado()`). Para el acero, `exportar_analysis_map.py` calcula las curvas P-M de los tubos `300x300x20` y `300x300x50` (elásticas, fy=240 MPa, `A` y `Zp`) en `capacidad.steel`; el visor no las dibuja (los metálicos muestran N/V/M/DEF en su lugar). El visor busca cada curva por el nombre de sección del elemento.

Luego abrir `edificio_3d.html` y usar `TAB` para el modo análisis.

### Unity
1. Abrir `Unity/` como proyecto en Unity Hub (requiere Unity 6 / 6000.x).
2. Al abrir por primera vez Unity regenera `Library/` y los paquetes (toma unos minutos).
3. Pulsar Play para ver el edificio: columnas, vigas, muros, lozas y los 6 diafragmas.
4. Hacer clic en un elemento para abrir su inspector (propiedades y cargas tributarias G/Q en las vigas).
5. Usar las teclas de la tabla anterior para alternar capas, ejes y el modo hormigón.

Si se actualizó `Edificio.json`, copiarlo a `Unity/Assets/StreamingAssets/Edificio.json` (o seguir el flujo del visor con `html_to_json.py`). El inspector por clic lee sus cargas desde `StreamingAssets/tributary_map.js` (generado por el análisis tributario); ambos deben estar sincronizados con el `Edificio.json`. El modo análisis del visor lee `opensees/results/analysis_map.js` y no está disponible en Unity.

## Conexiones y camino de carga

- **Conexiones** (`opensees/conexiones.py`): implementa las reglas A-E que deciden qué nodos se conectan al FE con `rigidLink`, qué apoyos quedan fijos y cuáles "huérfanos" se soportan verticalmente. La selección de muros para la regla G se configura en `regla_g_walls.json` (editada con `muro_seleccion.html`, que vive fuera del repo como herramienta local).
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

Además hay verificaciones *ad hoc* en `opensees/test_asymmetric.py`, `opensees/test_eleforce.py`, `opensees/verificador_camino_carga.py` y `fiber_sections/verification_ha.py`. El detalle del modelo (masa por piso, momentos, equilibrios) queda auditado en consola por `opensees_edificio_v2.py`; resumen en `opensees/results/verification.md`.

## Ciclo de desarrollo

```
Issue → Plan → Build → Test → Review → Merge
```

## Documentación

- [Enunciado del proyecto](Enunciado_Proyecto1/)
- [Agentes IA](AGENTS.md)