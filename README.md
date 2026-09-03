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
- **Modo hormigón** (`H`): pinta todo el edificio en tonos de concreto (fundaciones más oscuras).

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
| `H` | Modo hormigón (concreto claro / fundaciones oscuras) |
| Clic izquierdo | Inspector de propiedades y cargas del elemento |

## Estructura

```
├── edificio_3d.html      # Visor 3D interactivo (Three.js, fuente de edición del modelo)
├── Edificio.json         # Contrato OpenSees↔Unity (regenerado desde el visor)
├── opensees/             # Scripts de análisis estructural
│   ├── loads/            # Definición de cargas
│   ├── fiber_sections/   # Secciones de fibras RC
│   ├── analysis/         # Análisis lineal y no lineal
│   ├── visualizar.py     # JSON → HTML (genera el visor desde el contrato)
│   └── results/          # Resultados exportados (JSON)
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

### Unity
1. Abrir `Unity/` como proyecto en Unity Hub (requiere Unity 6 / 6000.x).
2. Al abrir por primera vez Unity regenera `Library/` y los paquetes (toma unos minutos).
3. Pulsar Play para ver el edificio: columnas, vigas, muros, lozas y los 5 diafragmas.
4. Hacer clic en un elemento para abrir su inspector (propiedades y cargas tributarias G/Q en las vigas).
5. Usar las teclas de la tabla anterior para alternar capas, ejes y el modo hormigón.

Si se actualizó `Edificio.json`, copiarlo a `Unity/Assets/StreamingAssets/Edificio.json` (o seguir el flujo del visor con `html_to_json.py`). El inspector por clic lee sus cargas desde `StreamingAssets/tributary_map.js` (generado por el análisis tributario); ambos deben estar sincronizados con el `Edificio.json`.

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