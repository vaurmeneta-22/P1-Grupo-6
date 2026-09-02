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
│       ├── Scripts/      # EdificioLoader.cs, CameraController.cs
│       └── StreamingAssets/Edificio.json   # Copia que Unity lee en runtime
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
3. Pulsar Play para ver el edificio: columnas, vigas, muros y lozas.

Si se actualizó `Edificio.json`, copiarlo a `Unity/Assets/StreamingAssets/Edificio.json` (o seguir el flujo del visor con `html_to_json.py`).

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