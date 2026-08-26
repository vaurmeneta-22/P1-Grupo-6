# CONTEXTO COMPLETO — P1 Laboratorio Estructural Digital

> **Instrucción:** Copia este documento completo y pégalo como contexto inicial en cualquier sesión nueva de IA para que entienda TODO sobre el proyecto desde la primera interacción.

---

## 1. INFORMACIÓN DEL PROYECTO

- **Nombre:** P1 — Laboratorio Estructural Digital del Edificio de Ingeniería
- **Grupo:** 6
- **Curso:** Métodos Computacionales (8vo semestre)
- **Duración:** 7 semanas (19 ago – 9 oct 2026)
- **Integrantes:** 3 estudiantes
- **Tecnologías principales:** Python (OpenSeesPy), C# (Unity), AR Foundation
- **Unidades:** SI (kN, m, kg)

---

## 2. OBJETIVO FINAL

Construir un **laboratorio estructural digital** del Edificio de Ingeniería que permita:

1. Analizar estructuralmente un edificio real en 3D con OpenSees
2. Visualizar el modelo y resultados en Unity
3. Permitir inspección, modificación y comprensión del modelo
4. Ejecutar una experiencia básica de AR sobre el edificio real
5. Verificar numéricamente: equilibrio, superposición, capacidad RC, demanda vs capacidad

**NO es un videojuego. Es una herramienta de ingeniería.**

---

## 3. STACK TECNOLÓGICO

| Componente | Tecnología | Rol |
|-----------|-----------|-----|
| Análisis estructural | OpenSeesPy (Python) | Cálculo de fuerzas, deformadas, reacciones, fiber sections |
| Contrato de datos | JSON | Puente entre OpenSees y Unity |
| Visualización/Interacción | Unity (C#) | Viewer 3D, diagramas, UI interactiva, pre/postproceso |
| AR | AR Foundation + Image Tracking | Realidad aumentada sobre el edificio real |
| Control de versiones | Git + GitHub | Repositorio del proyecto |
| Asistente de código | OpenCode | IA para desarrollo (con AGENTS.md) |

---

## 4. MODELO ESTRUCTURAL

### 4.1 Tipo de modelo global
- **Lineal elástico 3D**
- Nodos con **6 GDL** (3 traslacionales + 3 rotacionales)
- Elementos **elasticBeamColumn** para vigas, columnas y muros equivalentes
- **Diafragmas rígidos** por piso (rigidDiaphragm)
- Apoyos idealizados según planos reales
- **NO se modelan losas con elementos finitos**

### 4.2 Transformaciones geométricas
- Usar `geomTransf` de OpenSees
- Definir ejes locales correctamente
- Los ejes locales determinan la dirección de momentos y fuerzas internas
- **Siempre verificar** que el eje local coincida con la convención del curso

### 4.3 Diafragmas
- Un diafragma rígido por piso
- Vincula GDL de todos los nodos del piso
- Solo permite: traslación X, traslación Y, rotación Z

---

## 5. SISTEMA DE CARGAS

### 5.1 Cargas gravitacionales (G)
- **Peso propio de losa** (densidad × espesor)
- **Cargas de terminaciones** (carga superficial uniforme adicional)
- Ambas se combinan como **q_G** (carga superficial total)
- Transferencia a vigas mediante **áreas tributarias** (obligatorio y explícito)

### 5.2 Carga viva (Q)
- Misma geometría tributaria que G
- Intensidad diferente: **q_Q**

### 5.3 Peso propio de elementos
- Vigas, columnas y muros según convención del profesor
- El ejercicio obligatorio se concentra en la transferencia de losa + terminaciones

### 5.4 Sismo pseudoestático
- Patrón lateral idealizado
- **EX:** carga lateral en X
- **EY:** carga lateral en Y
- No se busca procedimiento normativo sísmico completo

### 5.5 Casos de carga base
| Caso | Descripción |
|------|-------------|
| G | Gravedad |
| Q | Carga viva |
| EX | Sismo en X |
| EY | Sismo en Y |

### 5.6 Combinaciones y superposición
```
R = λ_G · R_G + λ_Q · R_Q + λ_EX · R_EX + λ_EY · R_EY
```

**Verificación obligatoria:**
```
R(A+B) = R(A) + R(B)   (exactitud numérica)
```

**Regla:** Cambios de factores de combinación **NO** requieren reanálisis OpenSees.

---

## 6. ÁREAS TRIBUTARIAS

### 6.1 Principio
La carga superficial de losa se asigna a vigas bordeadoras según polígonos tributarios.

### 6.2 Conservación de carga (INVARIANTE)
```
∑(cargas transferidas a vigas) = q × A_tributaria
```
Tolerancia: **1e-10**

### 6.3 Sidequest SQ1 — Tributary Area Inspector
- Seleccionar piso → seleccionar viga → crear polígono → calcular área
- Asociar q_G o q_Q → calcular q×A → convertir a carga lineal
- Visualizar polígono y carga → exportar JSON

---

## 7. FIBER SECTIONS Y CAPACIDAD RC

### 7.1 Fiber Section
- Sección transversal dividida en fibras
- Cada fibra: material (concreto confinado/no confinado, acero)
- Comportamiento **no lineal axial-flexural**

### 7.2 Curva M-phi
- Momento vs curvatura de una sección representativa
- Obtener con **DisplacementControl**

### 7.3 Curva P-M
- Interacción axial-momento para **columna** y **muro**
- Generar variando carga axial y calculando capacidad a flexión

### 7.4 Demanda vs Capacidad
- Tomar fuerzas internas del modelo global
- Superponer sobre curva P-M
- Dentro = adecuada | Fuera = insuficiente

### 7.5 LIMITACIONES de la Fiber Section
**NO modela:**
- Capacidad de corte
- Respuesta no lineal completa del edificio
- Inestabilidad/pandeo de barras
- Falla por adherencia
- Otros mecanormanismos no modelados

---

## 8. SIDEQUESTS

| SQ | Nombre | Descripción |
|----|--------|-------------|
| SQ1 | Tributary Area Inspector | Definir/editar áreas tributarias, conservación de carga |
| SQ2 | Load Combination Explorer | Modificar λ_G, λ_Q, λ_EX, λ_EY, observar respuesta |
| SQ3 | Section Capacity Explorer | Sección, refuerzo, M-phi, P-M, punto de demanda |
| SQ4 | Carga móvil del usuario | Posición del usuario → carga localizada → vigas receptoras → diagramas |

---

## 9. UNITY — FUNCIONALIDADES REQUERIDAS

### 9.1 Viewer debe poder activar/desactivar:
- Nodos, vigas, columnas, muros
- Diafragmas
- Apoyos/restricciones
- Ejes locales
- IDs (nodeTag, elementTag)
- Áreas tributarias
- Cargas aplicadas
- Deformada
- Diagramas de esfuerzos
- Indicadores demanda-capacidad
- Curvas de interacción

### 9.2 Modificación del modelo
**NO requiere reanálisis:**
- Cambiar λ de combinaciones lineales

**SÍ requiere reanálisis:**
- Apoyo, sección, E, conectividad, remoción de elemento, geometría de carga

**Proyecto base:** reanálisis manual + recarga en Unity
**Honors:** reanálisis automático cliente-servidor

---

## 10. REALIDAD AUMENTADA (Semana 6)

### 10.1 Flujo
```
Image Tracking → Pose → Anchor → Objeto virtual → Resultado OpenSees
```

### 10.2 Tecnologías
- AR Foundation (Unity)
- Image Tracking (marker/reconocimiento de imagen)
- ARCore (Android) / ARKit (iOS)

### 10.3 Verificación
- Transformación de coordenadas correcta
- Error de registro aceptable
- QA global AR

---

## 11. CRONOGRAMA DETALLADO

### Semana 0 (19-21 ago) — COMPLETADA
- LAB: Modelo 2D mínimo en OpenSees

### Semana 1 (24-28 ago) — EN CURSO
| Día | Tarea | Pts |
|-----|-------|-----|
| Lun 24 | Benchmark 3D OpenSeesPy completo | — |
| Mar 25 | Verificar equilibrio + exportar JSON | — |
| Mié 26 | Plan del proyecto: geometría, materiales, cargas | — |
| Jue 27 | **LAB:** Benchmark 3D funcionando + grilla inicial | 10 |
| Vie 28 | **AVANCE:** Verificación cuantitativa + interpretación + arquitectura | 20 |

**Benchmark 3D debe incluir:**
1. Nodos 3D con 6 GDL
2. Elementos elasticBeamColumn
3. Transformación geométrica (geomTransf)
4. Apoyos empotrados
5. Carga puntual
6. Reacciones (verificar ΣF = 0, ΣM = 0)
7. Fuerzas internas
8. Exportar resultados a JSON

### Semana 2 (31 ago – 4 sep)
| Día | Tarea | Pts |
|-----|-------|-----|
| Jue 3 | Geometría completa + primeros chequeos + viewer 3D | 10 |
| Vie 4 | Modelo global + carga losa+terminaciones + áreas tributarias + QA Unity | 20 |

### Semana 3 (7-11 sep)
| Día | Tarea | Pts |
|-----|-------|-----|
| Jue 10 | G, Q, EX, EY + superposición + Fiber Section + M-phi | 10 |
| Vie 11 | Superposición verificada + curvas P-M + demanda/capacidad | 20 |

### Semana 4 (14-18 sep)
| Día | Tarea | Pts |
|-----|-------|-----|
| Jue 17 | Selección, apoyos, cargas, áreas tributarias, deformada, diagramas, P-M | 10 |
| Vie 18 | Contrato OpenSees↔Unity + QA + diagramas + demanda-capacidad + tests | 20 |

### Semana 5 (21-25 sep)
| Día | Tarea | Pts |
|-----|-------|-----|
| Jue 24 | Sliders, superposición instantánea, modificación parámetros | 10 |
| Vie 25 | Laboratorio interactivo v1 + modificaciones/reanálisis + sidequests | 20 |

### Semana 6 (28 sep – 2 oct)
| Día | Tarea | Pts |
|-----|-------|-----|
| Jue 1 oct | AR: marker → pose → anchor → elemento real + resultado OpenSees | 10 |
| Vie 2 oct | Validación AR + transformación coordenadas + error registro + QA global | 20 |

### Semana 7 (5-9 oct)
| Día | Tarea | Pts |
|-----|-------|-----|
| Jue 8 | **DEMO FINAL + defensa individual + Honors** | 70 |
| Vie 9 | **INFORME FINAL + release reproducible + documentación Honors** | 20 |

---

## 12. ARQUITECTURA DE ARCHIVOS

```
P1-Grupo-6/
├── AGENTS.md
├── CONTEXTO_PROYECTO.md          # Este archivo
├── opensees/
│   ├── benchmark_3d.py           # Semana 1
│   ├── building_model.py         # Semana 2
│   ├── loads/
│   │   ├── gravity.py            # Semana 2
│   │   ├── live_load.py          # Semana 3
│   │   └── seismic.py            # Semana 3
│   ├── fiber_sections/
│   │   ├── m_phi.py              # Semana 3
│   │   └── p_m.py                # Semana 3
│   ├── analysis/
│   │   ├── linear.py             # Semana 2
│   │   └── displacement_control.py # Semana 3
│   └── results/                  # JSON exportados
│       ├── nodes.json
│       ├── elements.json
│       ├── reactions.json
│       ├── forces.json
│       ├── deformations.json
│       └── combinations.json
├── unity/
│   ├── Assets/
│   │   ├── Scripts/
│   │   │   ├── ModelLoader.cs
│   │   │   ├── ViewerController.cs
│   │   │   ├── DiagramRenderer.cs
│   │   │   ├── DeformationVisualizer.cs
│   │   │   ├── PMInteractionPlotter.cs
│   │   │   ├── ARManager.cs
│   │   │   ├── TributaryAreaDrawer.cs
│   │   │   ├── LoadVisualizer.cs
│   │   │   └── UI/
│   │   │       ├── PanelController.cs
│   │   │       ├── SliderController.cs
│   │   │       └── SelectionManager.cs
│   │   ├── Prefabs/
│   │   ├── Materials/
│   │   └── Scenes/
│   └── Packages/
├── data/
│   ├── tributary_areas.json
│   ├── building_geometry.json
│   ├── materials.json
│   ├── sections.json
│   └── load_patterns.json
├── docs/
│   ├── P1_Informe.md
│   ├── ia_log.md                # Registro semanal de uso de IA
│   └── verification_notes.md
├── tests/
│   ├── test_equilibrium.py
│   ├── test_superposition.py
│   ├── test_tributary_areas.py
│   ├── test_units.py
│   └── test_ids.py
└── scripts/
    ├── export_json.py
    └── verify_results.py
```

---

## 13. AGENTS.md (para OpenCode)

```markdown
# Project
Laboratorio estructural digital 3D del Edificio de Ingeniería.

# Units
SI. Siempre: kN, m, kg, Pa, N·m.

# Structural model
- Global model: linear elastic 3D.
- 6 DOF per node.
- elasticBeamColumn for beams, columns, and equivalent walls.
- Rigid diaphragms per floor.
- Slabs are NOT modeled with FE.
- Floor gravity load = slab self weight + uniform finishes (q_G).
- Slab loads transferred through tributary areas.
- RC capacity analysis is SEPARATE from the global model.
- Fiber sections for M-phi and P-M curves.

# Loads
- G: gravity (slab + finishes)
- Q: live load
- EX: seismic lateral in X
- EY: seismic lateral in Y
- Superposition: R = λ_G·R_G + λ_Q·R_Q + λ_EX·R_EX + λ_EY·R_EY

# Architecture
- OpenSeesPy owns structural analysis.
- Unity (C#) owns visualization/preprocessing/interaction.
- JSON is the contract between both.
- Mobile does not run OpenSees in the base project.
- AR uses AR Foundation with image tracking.

# Verification rules (ALWAYS CHECK)
- Equilibrium: ΣF_applied + ΣR = 0
- Tributary areas: Σ(cargas transferidas) = q × A (tolerance 1e-10)
- Superposition: R(A+B) = R(A) + R(B)
- IDs: every exported elementTag must exist exactly once in viewer
- Units: every JSON field must have explicit units or global convention
- Local axes: verify direction matches course convention

# What NOT to delegate without review
- Structural idealization choices
- Local axis meaning
- Tributary distribution rules
- Support definitions
- Capacity criteria
- P-M interpretation
- SQ4 load distribution rule
- AR physical alignment

# Invariants
- sum(F_applied) + sum(R) ≈ 0
- sum(transferred_loads) = q * A
- R(A+B) = R(A) + R(B)
- Every elementTag appears exactly once in viewer
- All fields have explicit units
```

---

## 14. INVARIANTES FÍSICOS (VERIFICACIONES OBLIGATORIAS)

| Invariante | Fórmula | Tolerancia |
|-----------|---------|-----------|
| Equilibrio global | ∑F_aplicadas + ∑R = 0 | < 1e-10 |
| Conservación de carga tributaria | ∑(cargas transferidas) = q × A | < 1e-10 |
| Superposición lineal | R(A+B) = R(A) + R(B) | < 1e-10 |
| Unicidad de IDs | Cada elementTag → exactamente 1 GameObject | Exacto |
| Unidades | Todos los campos con unidades explícitas | Convención global |

---

## 15. QUÉ NO DELEGAR SIN REVISIÓN HUMANA

1. Idealización estructural del edificio
2. Significado de ejes locales
3. Reglas de distribución tributaria
4. Definición de apoyos y restricciones
5. Criterio de capacidad RC
6. Interpretación de curvas P-M
7. Regla de distribución del sidequest SQ4
8. Alineamiento físico en AR
9. Verificación de equilibrio
10. Cualquier cambio a resultados de referencia

---

## 16. CICLO DE DESARROLLO CON IA

```
1. Issue     → Definir tarea con objetivo, restricciones, criterio de aceptación
2. Plan      → IA inspecciona, identifica archivos, riesgos, pruebas (NO edita)
3. Build     → IA implementa solo lo descrito (NO modifica contrato ni resultados)
4. Test      → Ejecutar tests, invariantes, comparación manual
5. Review    → IA revisa buscando errores de unidades, signos, ejes, física (NO edita)
6. Merge     → Aprobar y combinar
```

**Ejemplo de buen encargo:**
> Implementar la lectura de tributary_areas.json. No modificar el esquema. Verificar que la suma de cargas transferidas sea igual q×A dentro de tolerancia 1e-10.

**Ejemplo de mal encargo:**
> Haz la herramienta de áreas tributarias.

---

## 17. RECURSOS TÉCNICOS

### OpenSees/OpenSeesPy
- https://opensees.berkeley.edu/
- https://openseespydoc.readthedocs.io/
- https://opensees.github.io/OpenSeesDocumentation/

### Unity
- https://docs.unity3d.com/Manual/index.html
- https://docs.unity3d.com/ScriptReference/

### AR Foundation
- https://docs.unity3d.com/Packages/com.unity.xr.arfoundation@latest/
- https://developers.google.com/ar

### Google Cardboard (Honors)
- https://developers.google.com/cardboard/develop/unity/quickstart

---

## 18. EVALUACIÓN

### Criterios de éxito (en orden de prioridad)
1. Corrección estructural
2. Verificación numérica
3. Trazabilidad
4. Comprensión del modelo
5. Calidad del software
6. Utilidad de la visualización
7. Calidad de la experiencia AR/XR

### Evaluación individual
Cualquier integrante debe poder explicar:
- GDL, ejes locales, rigidez
- Apoyos, diafragmas
- Áreas tributarias, equilibrio
- Superposición, diagramas
- Fiber sections, curvas P-M
- OpenSees ↔ Unity
- Transformación AR
- Limitaciones del modelo

---

## 19. CONTEXTO PARA OTRA SESIÓN DE IA

**Cuando pegues este documento en una nueva sesión, usa esta instrucción:**

> Lee el archivo CONTEXTO_PROYECTO.md que te paso. Es el contexto completo de un proyecto de ingeniería estructural. Necesito que actúes como desarrollador experto en OpenSeesPy, Unity (C#), y AR Foundation. Siempre verifica: equilibrio, unidades, superposición, conservación de cargas, y unicidad de IDs. Usa el ciclo Issue→Plan→Build→Test→Review. No edites archivos de referencia sin justificación. Pregunta antes de asumir dimensiones del edificio.

---

## 20. ESTADO ACTUAL

- **Semana completada:** 0
- **Semana en curso:** 1
- **Avance:** Modelo 2D mínimo completado (LAB 0)
- **Pendiente Semana 1:** Benchmark 3D + verificación + plan del proyecto + grilla del edificio
- **Próxima entrega:** Jue 27 ago (LAB, 10 pts) + Vie 28 ago (AVANCE, 20 pts)
