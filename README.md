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

- **5 diafragmas rígidos** (niveles 3.56, 7.12, 10.68, 14.24 y 17.8 m) por la huella real de piso: plano casi transparente con borde cian y triangulación de polígono cóncavo (tecla `D`).
- **Capas alternables por familia** a través de teclas, igual que el panel de checkboxes del HTML.
- **Inspector por clic**: al hacer clic sobre una viga, columna, muro o losa se muestra un panel con sus propiedades y, en vigas, el área tributaria y las **cargas** G (permanente) y Q (sobrecarga) calculadas en el análisis.
- **Modo análisis** (tecla `TAB` o botón central): superpone al modelo los resultados del análisis lineal con OpenSees — deformada y diagramas de momento (M), axial (N) y corte (V).
- **Modo hormigón** (`H`): pinta todo el edificio en tonos de concreto (fundaciones más oscuras).

### Modo análisis del visor (TAB)

Accesible desde `edificio_3d.html` con `TAB` o el botón `ANALISIS` de la barra superior:

- **Vistas**: deformada (con amplificación ajustable), Momento M, Axial N y Corte V.
- **Casos de carga**: G (permanente), Q (sobrecarga), EX, EY y COMBO (combinación). El case COMBO agrupa los resultados combinados exportados.
- **Color por valor**: cada elemento se pinta con un colormap azul→verde→rojo normalizado por el **percentil 90** de los valores (evita que uno o dos muros en la base dominen la escala y dejen el resto en azul). La leyenda inferior derecha muestra los rangos reales en las unidades de cada vista (mm en deformada, kN·m en momento, kN en axial/corte).
- **P-M por clic**: con el modo análisis activo, dar **doble clic** sobre una columna o muro dibuja en el inspector la **curva de capacidad** P-M (de las secciones de fibra RC) y marca el punto de demanda del caso activo (P axial y M resultante del extremo i del elemento), reportando el % de la **capacidad interpolada a esa misma carga axial** y si la demanda cae dentro de la curva (una demanda fuera de la curva se marca en rojo). El inspector se cierra con la **X** de su esquina superior.
- Deformada: `38.5 mm` máx. a escala x120 por defecto (deslizador `x`). M/N/V en respuesta lineal del modelo global.

Los datos se cargan desde `opensees/results/analysis_map.js`, generado por `exportar_analysis_map.py` a partir de los resultados `edificio_full_results*.json`.

### Atajos de teclado

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
| Clic izquierdo | Inspector de propiedades y cargas del elemento (en modo análisis: **doble clic** para la curva P-M, cierre con **X**)|

## Estructura

```
├── edificio_3d.html      # Visor 3D interactivo (Three.js, fuente de edición del modelo)
├── Edificio.json         # Contrato OpenSees↔Unity (regenerado desde el visor)
├── opensees/             # Scripts de análisis estructural
│   ├── loads/            # Definición de cargas
│   ├── fiber_sections/   # Secciones de fibras RC
│   ├── analysis/         # Análisis lineal y no lineal
│   ├── visualizar.py     # JSON → HTML (genera el visor desde el contrato)
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
├── tests/                # Verificaciones
├── scripts/              # Utilidades (scripts/html_to_json.py)
└── docs/                 # Documentación
```

## Flujo de datos

`opensees` calcula y escribe `Edificio.json`; `visualizar.py` genera el HTML para verlo; Unity lee el JSON. Si el modelo se edita a mano en el visor, `scripts/html_to_json.py` devuelve esos cambios al contrato:

```
data/ ──► opensees ──► Edificio.json ──► Unity (visualización)
                ▲            │
                └────────────┘  visualizar.py: JSON→HTML
    edificio_3d.html ──► scripts/html_to_json.py: HTML→JSON
```

El modelo actual contiene **536 nodos, 702 elementos** (118 columnas, 141 vigas X, 165 vigas Y, 79 muros, 199 lozas) y **64 apoyos fijos**. Los valores se guardan en **cm** en el JSON.

## Ejecución

### Visor 3D (edición del modelo)
Abrir `edificio_3d.html` en un navegador. Después de editar (agregar/quitar nodos, lozas, vigas, muros), regenerar el contrato:

```bash
python scripts/html_to_json.py          # actualiza Edificio.json desde el visor
```

### OpenSeesPy
```bash
cd opensees
python benchmark_3d.py
```

### Modo análisis del visor (regenerar resultados)
Los resultados del análisis (deformada, M/N/V por caso y capacidad P-M) se exportan a `opensees/results/analysis_map.js`, que el visor carga con `<script>`. Regenerarlos tras un análisis nuevo:

```bash
cd opensees
python exportar_analysis_map.py
```

Luego abrir `edificio_3d.html` y usar `TAB` para el modo análisis.

### Unity
1. Abrir `Unity/` como proyecto en Unity Hub (requiere Unity 6 / 6000.x).
2. Al abrir por primera vez Unity regenera `Library/` y los paquetes (toma unos minutos).
3. Pulsar Play para ver el edificio: columnas, vigas, muros, lozas y los 5 diafragmas.
4. Hacer clic en un elemento para abrir su inspector (propiedades y cargas tributarias G/Q en las vigas).
5. Usar las teclas de la tabla anterior para alternar capas, ejes y el modo hormigón.

Si se actualizó `Edificio.json`, copiarlo a `Unity/Assets/StreamingAssets/Edificio.json` (o seguir el flujo del visor con `html_to_json.py`). El inspector por clic lee sus cargas desde `StreamingAssets/tributary_map.js` (generado por el análisis tributario); ambos deben estar sincronizados con el `Edificio.json`. El modo análisis del visor lee `opensees/results/analysis_map.js` y no está disponible en Unity.

## Verificaciones

```bash
cd tests
python test_equilibrium.py
python test_superposition.py
python test_tributary_areas.py
```

## Ciclo de desarrollo

```
Issue → Plan → Build → Test → Review → Merge
```

## Documentación

- [Enunciado del proyecto](Enunciado_Proyecto1/)
- [Agentes IA](AGENTS.md)