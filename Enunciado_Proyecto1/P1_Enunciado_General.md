# P1 - Enunciado General

## Contexto

Durante 7 semanas, cada grupo de 3 estudiantes desarrollará un laboratorio estructural digital del Edificio de Ingeniería.

El proyecto combina:

- Análisis estructural 3D con OpenSees/OpenSeesPy
- Idealización a partir de planos reales
- Cargas gravitacionales mediante áreas tributarias
- Carga viva
- Sismo pseudoestático idealizado
- Principio de superposición
- Análisis no lineal de secciones de hormigón armado
- Curvas de interacción P-M para columnas y muros
- Visualización y pre/postproceso 3D en Unity
- Modificación e inspección del modelo
- Una experiencia básica de realidad aumentada (AR) en el edificio real
- Uso intensivo, documentado y crítico de agentes de IA (OpenCode, probar vía la terminal siguiendo [estas instrucciones](https://opencode.ai/docs/windows-wsl))

El propósito no es construir un videojuego. El propósito es construir y verificar un modelo estructural y luego desarrollar una interfaz que permita interrogar, modificar y comprender ese modelo.

## Objetivos de aprendizaje

Al finalizar el proyecto, cada estudiante deberá ser capaz de:

- Interpretar un modelo estructural espacial con 6 GDL por nodo
- Distinguir ejes locales y globales
- Interpretar apoyos, restricciones y diafragmas rígidos
- Convertir cargas superficiales de losa en cargas de vigas mediante áreas tributarias
- Construir y verificar casos de carga lineales independientes
- Demostrar numéricamente el principio de superposición
- Interpretar deformadas, reacciones y diagramas de esfuerzos
- Construir una Fiber Section de hormigón armado
- Obtener y verificar una curva momento-curvatura
- Generar una curva de interacción P-M
- Distinguir demanda global de capacidad de sección
- Explicar qué calcula OpenSees y qué calcula/representa Unity
- Relacionar un objeto gráfico con un nodeTag o elementTag
- Explicar una transformación de coordenadas OpenSees → Unity → AR
- Verificar críticamente código generado por IA

## Alcance estructural obligatorio

### Modelo global

El edificio se modelará como un sistema lineal elástico 3D.

Se usarán:

- Nodos 3D con 6 GDL
- Elementos lineales de viga-columna para vigas y columnas
- Muros representados mediante elementos lineales equivalentes de acuerdo con la convención entregada en el curso
- Diafragmas rígidos
- Apoyos idealizados
- Cargas gravitacionales, vivas y sísmicas pseudoestáticas

**No se modelarán losas con elementos finitos.** (!)

### Carga gravitacional

Para simplificar el alcance, la carga gravitacional distribuida proveniente de pisos se definirá como:

- Peso propio de la losa
- Una carga superficial uniforme adicional que representa terminaciones
- Peso propio de los elementos estructurales

Ambas (losa + terminaciones) se tratarán conjuntamente como una carga superficial **q_G**.

La transferencia desde la losa a las vigas debe hacerse explícitamente mediante áreas tributarias.

El peso propio de vigas, columnas y muros podrá incorporarse según la convención entregada por el profesor, pero el ejercicio obligatorio de transferencia de cargas de piso se concentra en la losa + terminaciones.

### Carga viva

La carga viva **q_Q** utilizará la misma geometría tributaria definida para las cargas gravitacionales, pero con una intensidad diferente.

### Sismo pseudoestático

Se utilizará un patrón lateral idealizado entregado o parametrizado por el profesor.

No es objetivo del proyecto desarrollar un procedimiento normativo sísmico completo.

Se espera trabajar, como mínimo, con casos base independientes:

- **G**: gravedad
- **Q**: carga viva
- **EX**: carga lateral en X
- **EY**: carga lateral en Y

### Capacidad no lineal

En forma separada del modelo global lineal se construirán secciones de fibras de hormigón armado.

El alcance obligatorio incluye:

- Una curva M-phi para una sección representativa
- Una curva P-M para una columna
- Una curva P-M para un muro
- Al menos una comparación independiente con contenidos del curso de hormigón armado
- Superposición de la demanda del modelo global sobre la curva de capacidad

La Fiber Section representa principalmente comportamiento axial-flexural de sección.

No se debe interpretar automáticamente como:

- Capacidad de corte
- Capacidad de miembro incluyendo inestabilidad
- Respuesta no lineal completa del edificio
- Falla por adherencia, pandeo de barras u otros mecanismos no modelados

## Unity como herramienta de ingeniería

Unity entra desde la Semana 2.

Al comienzo se utilizará principalmente para:

- Visualizar geometría
- Detectar errores de conectividad
- Mostrar IDs
- Mostrar ejes
- Mostrar apoyos
- Visualizar diafragmas
- Visualizar cargas
- Definir o inspeccionar áreas tributarias

Posteriormente evolucionará hacia:

- Postproceso
- Diagramas
- Deformada
- Combinación interactiva de cargas
- Demanda-capacidad (curvas de interacción)
- Modificación de parámetros del modelo
- Navegación tipo videojuego
- AR

### Elementos mínimos que el viewer debe poder activar/desactivar

- Nodos
- Vigas
- Columnas
- Muros
- Diafragmas
- Apoyos/restricciones
- Ejes locales
- IDs
- Áreas tributarias
- Cargas aplicadas
- Deformada
- Diagramas de esfuerzos
- Indicadores demanda-capacidad
- Curvas de interacción

## Modificación del modelo

El producto final debe permitir modificar al menos dos familias de parámetros del modelo desde una interfaz reproducible.

Ejemplos:

- Intensidad de cargas
- Condiciones de apoyo
- Sección de un elemento
- Propiedad de material
- Activación/desactivación de un elemento
- Geometría tributaria

El grupo debe distinguir:

### Cambios que NO requieren reanálisis OpenSees

Cambios de factores de combinación de casos lineales ya calculados:

```
R = sum(lambda_i * R_i)
```

### Cambios que SÍ requieren reanálisis

Por ejemplo:

- Apoyo
- Sección
- E (módulo de elasticidad)
- Conectividad
- Remoción de elemento
- Geometría de carga que cambia los casos base

Para el proyecto base, el reanálisis puede ejecutarse manualmente en el computador y luego recargarse en Unity.

El reanálisis automático cliente-servidor queda en Honors.

## Sidequests

Los sidequests son funcionalidades acotadas que ayudan a construir el producto y pueden integrarse en la aplicación final.

### SQ1 — Tributary Area Inspector

Herramienta para:

- Seleccionar una planta
- Seleccionar una viga
- Definir/editar un polígono tributario
- Calcular su área
- Asociarlo a un elementTag
- Calcular carga total q*A
- Convertirla a una distribución sobre la viga
- Visualizar el polígono y la carga

Debe existir conservación de carga:

```
carga transferida = q * A_tributaria
```

### SQ2 — Load Combination Explorer

Permite modificar lambda_G, lambda_Q, lambda_EX, lambda_EY y observar respuestas combinadas.

Debe verificarse contra una corrida OpenSees explícita.

### SQ3 — Section Capacity Explorer

Permite seleccionar una sección y mostrar:

- M-phi
- P-M
- Demanda actual
- Cambio del punto de demanda al variar combinaciones

### SQ4 — "¿Qué carga genero donde estoy?"

Extensión interactiva vinculada a la posición del usuario.

La aplicación asume una carga viva localizada idealizada **P_user** asociada a la posición (x,y) del usuario sobre un piso.

El grupo debe definir y documentar una regla simple y físicamente interpretable para transferir esa carga a las vigas cercanas, por ejemplo:

- Asignación a la celda/panel que contiene al usuario
- Distribución a vigas de borde mediante una regla geométrica explícita

Al desplazarse el usuario:

- Cambia el panel activo
- Cambian las vigas receptoras
- Se actualizan visualmente las cargas
- Puede mostrarse el cambio correspondiente en fuerzas internas

No se exige modelar la losa como placa ni pretender que esta regla reproduce exactamente su comportamiento bidireccional. El valor está en visualizar el camino de carga idealizado.

## Arquitectura computacional recomendada

La geometría y datos estructurales deben existir en formatos independientes de la escena Unity.

Unity puede ayudar a crearlos o editarlos, pero la escena no debe ser la única fuente de verdad del modelo.

## Uso de IA

El uso de OpenCode está permitido y esperado.

Cada grupo debe mantener:

- AGENTS.md
- Issues o tareas equivalentes
- Criterios de aceptación
- Registro semanal del uso de IA
- Pruebas o verificaciones asociadas a cambios importantes

Se recomienda el ciclo:

```
Issue → Plan → Build → Test → Review → Merge
```

**Ejemplo de buen encargo a un agente:**

> Implementar la lectura de tributary_areas.json. No modificar el esquema. Verificar que la suma de cargas transferidas sea igual a q*A dentro de tolerancia 1e-10.

**Ejemplo de mal encargo:**

> Haz la herramienta de áreas tributarias.

## Evaluación individual

Aunque exista división de tareas, cualquier integrante puede ser consultado sobre:

- GDL
- Ejes locales
- Rigidez
- Apoyos
- Diafragmas
- Áreas tributarias
- Equilibrio
- Superposición
- Diagramas
- Fiber Sections
- Curvas P-M
- Correspondencia OpenSees–Unity
- Transformación AR
- Limitaciones del modelo

## Secuencia del proyecto

| Semana | Foco |
|---|---|
| 1 | Benchmark 3D OpenSees y verificación |
| 2 | Edificio completo + gravedad + Unity como preprocesador |
| 3 | Carga viva + sismo + superposición + capacidad RC |
| 4 | Integración completa de resultados en Unity |
| 5 | Interactividad, modificación del modelo y experiencia estructural |
| 6 | AR básica obligatoria |
| 7 | Integración final + Honors Track |

## Criterio de éxito

El proyecto no se evalúa por realismo gráfico.

La prioridad es:

- Corrección estructural
- Verificación
- Trazabilidad
- Comprensión
- Calidad del software
- Utilidad de la visualización
- Calidad de la experiencia AR/XR

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
