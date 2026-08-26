# P1 - Recursos técnicos y estrategia de trabajo con IA

## 1. Principio

La IA puede escribir una gran parte del código, pero no puede reemplazar la verificación física.

Cada tarea importante debe tener:

- Objetivo
- Restricciones
- Criterio de aceptación
- Prueba
- Revisión

## 2. AGENTS.md

El repositorio debe contener un `AGENTS.md`.

Como mínimo:

```
# Project
Laboratorio estructural digital 3D de un edificio real.

# Units
SI.

# Structural model
- Global model: linear elastic 3D.
- Slabs are not FE modeled.
- Floor gravity load = slab self weight + uniform finishes.
- Slab loads are transferred through tributary areas.
- RC capacity analysis is separate from the global model.

# Architecture
- OpenSees owns structural analysis.
- Unity owns visualization/preprocessing/interaction.
- JSON is the contract between both.
- Mobile does not run OpenSees in the base project.

# Verification rules
- Check equilibrium.
- Check units.
- Check local axes.
- Check superposition.
- Never modify reference benchmark results without justification.
```

## 3. Flujo recomendado

### Plan

Pedir al agente:

> Inspecciona el repositorio, identifica archivos afectados, riesgos y pruebas necesarias. No edites.

### Build

Luego:

> Implementa solamente la tarea descrita. No modifiques el contrato JSON ni los resultados de referencia.

### Test

Ejecutar:

- Unit tests
- Benchmark estructural
- Invariantes físicos
- Comparación manual

### Review

Pedir:

> Revisa este cambio buscando errores de unidades, signos, ejes, IDs, supuestos físicos y tests faltantes. No edites.

## 4. Agentes especializados sugeridos

### structural-reviewer

Revisa:

- GDL
- Unidades
- Ejes
- Apoyos
- Equilibrio
- Cargas
- Superposición
- Diagramas
- Capacidad RC

### unity-reviewer

Revisa:

- Correspondencia elementTag ↔ GameObject
- Transformaciones
- Escalas
- Lectura/escritura JSON
- Selección
- Modificación de datos

### load-path-reviewer

Revisa:

- Áreas tributarias
- Conservación de cargas
- Asociación polígono-viga
- Cargas móviles/sidequest

### ar-reviewer

Revisa:

- Image tracking
- Pose
- Anchor
- Escala
- Transformación OpenSees → Unity → AR

### test-planner

Propone tests antes de implementar.

## 5. Invariantes útiles para los agentes

**Equilibrio global**

```
sum(F_aplicadas) + sum(R) ≈ 0
```

**Área tributaria**

```
sum(cargas transferidas) = q * A
```

**Superposición**

```
R(A+B) = R(A) + R(B)
```

**IDs**

Todo elementTag exportado debe existir exactamente una vez en el viewer.

**Unidades**

Cada campo del contrato de datos debe tener unidades explícitas o una convención global única.

## 6. Qué NO delegar sin revisión

- Elección de idealización estructural
- Significado de los ejes locales
- Distribución tributaria
- Definición de apoyos
- Criterio de capacidad
- Interpretación de P-M
- Regla de distribución del sidequest de carga móvil
- Alineamiento físico AR

## Recursos técnicos recomendados

### OpenSees / OpenSeesPy

- [OpenSees](https://opensees.berkeley.edu/)
- [OpenSees Documentation](https://opensees.github.io/OpenSeesDocumentation/)
- [OpenSeesPy](https://openseespydoc.readthedocs.io/)
- [elasticBeamColumn](https://openseespydoc.readthedocs.io/en/latest/src/elasticBeamColumn.html)
- [Transformaciones geométricas](https://openseespydoc.readthedocs.io/en/latest/src/geomTransf.html)
- [rigidDiaphragm](https://openseespydoc.readthedocs.io/en/latest/src/rigidDiaphragm.html)
- [Fiber Section](https://openseespydoc.readthedocs.io/en/latest/src/fibersection.html)
- [DisplacementControl](https://openseespydoc.readthedocs.io/en/latest/src/displacementControl.html)
- [Salidas / recorders](https://opensees.github.io/OpenSeesDocumentation/user/manual/output/ElementRecorder.html)

### Unity

- [Unity Manual](https://docs.unity3d.com/Manual/index.html)
- [Unity Scripting API](https://docs.unity3d.com/ScriptReference/)
- [glTF / GLB](https://www.khronos.org/gltf/)

### AR Foundation

- [AR Foundation](https://docs.unity3d.com/Packages/com.unity.xr.arfoundation@latest/)
- [Image Tracking](https://docs.unity3d.com/Packages/com.unity.xr.arfoundation@6.1/manual/features/image-tracking.html)
- [Anchors](https://docs.unity3d.com/Packages/com.unity.xr.arfoundation@6.0/manual/features/anchors/introduction.html)
- [Samples oficiales](https://github.com/Unity-Technologies/arfoundation-samples)
- [ARCore](https://developers.google.com/ar)
- [Dispositivos compatibles con ARCore](https://developers.google.com/ar/devices)

### Google Cardboard — Honors Track

- [Cardboard](https://developers.google.com/cardboard)
- [Quickstart Unity](https://developers.google.com/cardboard/develop/unity/quickstart?hl=es-419)
- [Cardboard XR Plugin](https://github.com/googlevr/cardboard-xr-plugin)

### Git / GitHub

- [Git](https://git-scm.com/doc)
- [GitHub Docs](https://docs.github.com/)
- [Issues](https://docs.github.com/en/issues/tracking-your-work-with-issues/about-issues)
- [Pull Requests](https://docs.github.com/en/pull-requests)
- [Code review](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests)

### OpenCode

- [Documentación](https://opencode.ai/docs/)
- [AGENTS.md](https://opencode.ai/docs/rules/)
- [Agents](https://opencode.ai/docs/agents/)
- [Permissions](https://opencode.ai/docs/permissions/)
