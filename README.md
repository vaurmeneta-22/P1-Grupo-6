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
| Visualización | Unity + C# |
| AR | AR Foundation + Image Tracking |
| Datos | JSON (contrato OpenSees↔Unity) |

## Estructura

```
├── opensees/          # Scripts de análisis estructural
│   ├── loads/         # Definición de cargas
│   ├── fiber_sections/# Secciones de fibras RC
│   ├── analysis/      # Análisis lineal y no lineal
│   └── results/       # Resultados exportados (JSON)
├── unity/             # Proyecto Unity
│   └── Assets/Scripts/# Scripts C#
├── data/              # Datos compartidos
├── tests/             # Verificaciones
├── scripts/           # Utilidades
└── docs/              # Documentación
```

## Ejecución

### OpenSeesPy
```bash
cd opensees
python benchmark_3d.py
```

### Unity
Abrir `unity/` como proyecto en Unity Hub.

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
- [Contexto completo](CONTEXTO_PROYECTO.md)
- [Agentes IA](AGENTS.md)
