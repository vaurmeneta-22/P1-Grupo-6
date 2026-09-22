# Informe de Avance — Semana 5

| Campo | Valor |
|---|---|
| **Proyecto** | P1 — Laboratorio Estructural Digital (Edificio de Ingeniería) |
| **Curso** | Métodos Computacionales (8vo semestre) |
| **Grupo** | 6 |
| **Período** | 21 – 25 de septiembre de 2026 |
| **Entregable** | Laboratorio estructural interactivo **v1** (estado real al corte 22-sep) |
| **Repositorio** | `https://github.com/vaurmeneta-22/P1-Grupo-6` (rama `main`) |

---

## 1. Objetivo de la semana

Según el cronograma, la Semana 5 busca **interactividad + modificación del modelo**:

- Viernes 25 (20 pts): laboratorio estructural interactivo v1, modificaciones/reanálisis, sidequests y preparación móvil.
- Jueves 24 (10 pts): sliders, superposición instantánea, modificación de parámetros y demanda/capacidad dinámica.

Este informe documenta **el estado real al corte del 22-sep** con evidencia verificable
(commits, tests, valores numéricos), separando lo implementado de lo pendiente y dejando
el plan concreto para cerrar el viernes 25.

---

## 2. Funciones implementadas (estado real)

El visor Unity replica 1:1 el visor HTML (`edificio_3d.html`) alimentado por
`StreamingAssets/analysis_map.json` (exportado por `opensees/exportar_analysis_map.py`).
Estado por función requerida de la rúbrica:

| # | Función | Estado | Control | Fuente de datos | Verificación |
|---|---|---|---|---|---|
| 1 | Navegación 3D | ✅ | Cámara orbital: rotar/pan/zoom, `FrameBounds()` auto-encuadre | geometría | `CameraController.cs` |
| 2 | Selección de elementos | ✅ | Hover magenta (12 px), doble clic → reporte / curva P-M | `AnalysisMap.EndForces` | `PickHighlight.cs` |
| 3 | Apoyos / reacciones | ✅ | Caso 1–5 + vista, checkbox *Reacciones 3D* (tecla R) | `AnalysisMap.Reacciones` (99 filas) | esferas por magnitud |
| 4 | Ejes del edificio | ✅ | Capa "palitos" de ejes en leyenda (malla de columnas + ejes) | geometría + `tributary_map.js` | `ViewerHud.cs` leyenda 9 capas |
| 5 | Cargas | ✅ | Panel DATOS → Sismo (12 columnas por piso) + tributarias | `AnalysisMap.Sismo`, `TribuInfo` | tablas de piso |
| 6 | Áreas tributarias | ✅ | Inspector por clic: fuerzas por caso + aportes tributarios + triada de ejes locales 3D | `resultados/mapa_visor` (306 filas) | `TributaryInspector.cs` |
| 7 | Deformada | ✅ | Vista DEFINIDA, tecla D, escala ×10–600 (slider), auto-encuadre | desplazamientos (516 nodos/caso) | palitos escalados |
| 8 | Diagramas M/N/V | ✅ | Vista M/N/V con colormap percentil 90 + pestaña Diagramas apilados | `AnalysisMap.DiagInfo` | cierre viga 147 al 0.00 % (semana 4) |
| 9 | Superposición | ⚠️ parcial | 5 casos pre-computados (COMBO/G/Q/EX/EY) con selector 1–5 | casos base + COMBO explícito | sección 4 de este informe |
| 10 | Curvas P-M + demanda | ✅ | Doble clic columna/muro → diamante P-M + punto de demanda + % capacidad | `PmInfo` (1254+670 filas), `demanda_capacidad_critica.json` | sección 5 |
| 11 | Modificación del modelo / reanálisis | ⚠️ **pendiente** en Unity | No hay UI de edición en Unity; flujo manual reproducible (sección 3) | datos + OpenSees | 2 modificaciones cerradas |

**Resumen:** 8/11 funciones completas y verificadas; **superposición interactiva por
sliders** y **modificación de parámetros desde interfaz** son las dos carencias del
jueves 24 (10 pts). El COMBO se puede **elegir y ver** (deformada, M/N/V, reacciones,
P-M, diagramas), pero **no se pueden variar λ en vivo** aún.

---

## 3. Modificación del modelo (2 modificaciones completas documentadas)

El producto debe permitir modificar **al menos dos familias de parámetros** desde una
interfaz reproducible. En base (no Honors) el reanálisis puede ser manual y recargarse
en Unity (lo permite el enunciado). Ambas modificaciones cierran el ciclo completo:

```
interfaz/dato → modelo (JSON/OpenSees) → correr OpenSees → resultados (JSON/CSV)
             → exportar_analysis_map.py → analysis_map.json → Unity (StreamingAssets)
```

### Modificación A — Sobrecarga de uso q_Q: 2.0 → 4.0 kN/m² (familia: carga)

| Paso | Acción | Comando / archivo | Evidencia |
|---|---|---|---|
| 1 | Cambiar intensidad de carga viva | `data/sections.json` + parámetro `q_Q` en `opensees/opensees_edificio_v2.py` | commit `7c72050` |
| 2 | Reanalizar 4 casos base | `python opensees/opensees_edificio_v2.py` | `resultados/01_casos_base/*.json` |
| 3 | Superponer COMBO | `python opensees/superposicion.py` | `edificio_full_results_COMBO.json` |
| 4 | Regenerar mapa del visor | `python opensees/exportar_analysis_map.py` | `analysis_map.json` (1.66 MB) |
| 5 | Recargar en Unity | copiar a `Unity/Assets/StreamingAssets/` | `AnalysisMap.Loaded` |

Resultado con Q=4 kN/m² (commit `7c72050`): **Q=22 697 kN, EX/EY=16 651 kN,
COMBO (1.2G+1.0Q+1.4EX+1.4EY) = 157 505 kN**. Se actualizó a su vez el renderizado
de Q en el visor y en los CSVs.

### Modificación B — Refuerzo de secciones (familia: sección/refuerzo)

Dos casos cerrados en semanas previas con ciclo completo:

| Modificación | Flujo | Evidencia |
|---|---|---|
| Columnas 70×70 con **16 φ28** perimetrales (config del plano) | editar red de fibras → `Fiber Section` → regenerar `P-M`/`M-φ` de col → exportar mapa → Unity | commit `70e1c4c`; demanda crítica dentro de capacidad (épsilon 0,894, sección 5) |
| **Configuración única φ40 en muros** de borde | idem para muros → regenerar `pm_muros` → exportar → Unity | commit `c57e75c`; **79/79 muros dentro de capacidad (COMBO)** |

### Distinción explícita requerida por el enunciado

- **Cambios que NO requieren reanálisis:** la superposición `R = Σ λᵢ·Rᵢ` sobre casos
  ya calculados (SQ2). Aún no hay slider, pero el motor algebraico existe y está
  testeado: `opensees/superposicion.py::combine()` + `tests/test_superposicion.py`.
- **Cambios que SÍ requieren reanálisis:** apoyo, sección, E, conectividad, remoción de
  elemento, geometría de carga. Corren manualmente en el computador y se recargan en
  Unity (flujo de arriba). No hay servidor de reanálisis (queda para Honors).

---

## 4. Superposición — verificación de 3 estados contra resultados numéricos

La capacidad de combinar casos está implementada y testeada en Python
(`superposicion.combine()`), y el visor muestra el resultado **pre-computado** por caso.
Se verifican **tres estados de combinación** contra la corrida numérica explícita:

| # | Estado / combinación | Verificación | Error rel. máx. | Cumple |
|---|---|---|---|---|
| 1 | **COMBO explícito** λ = (1.2, 1.0, 1.4, 1.4) vs `combine()` de los 4 casos base | `test_comparacion_explicita_directa_tolerancias` + `verificacion.csv` | desplazamiento **6.78e-9** (516), reacción **2.28e-14** (99), fuerza interna **4.88e-12** (701) | tol 1e-6 ✅ |
| 2 | **G sola** λ = (1,0,0,0) reproduce el caso G | `test_combinacion_solo_G_reproduce_caso_G` | < 1e-8 (desplazamientos) | ✅ |
| 3 | **EX sola** λ = (0,0,1,0) reproduce el caso EX (aislamiento del sismo X) | `test_combinacion_solo_EX_reproduce_caso_EX` | < 1e-8 (desplaz. y reacciones) | ✅ |

> Nota de umbral (mantenida según directiva): la verificación existente usa **1e-6**.
> Contra el **1e-10** del `AGENTS.md`, la tabla `verificacion_excel.csv` muestra que
> `reaccion` y `fuerza interna` lo cumplen (2.28e-14 y 4.88e-12), pero **desplazamiento
> no** (6.78e-9). Queda documentado explícitamente en `resultados/GUIA_EXCEL.md` y en la
> tabla: `cumple_tol_proyecto = False` para desplazamiento.

**Interpretación estructural del desplazamiento:** los desplazamientos son `~1e-3 m`
(6.78e-9 es el error relativo, no el desplazamiento); la diferencia frente a 1e-10
proviene de la precisión de exportación de los casos base (1e-8/1e-10 en el JSON), no de
la superposición en sí.

---

## 5. Demanda–capacidad dinámica (evidencia del estado actual)

La demanda crítica de COMBO se mantiene dentro de la curva de capacidad de la columna
más solicitada (`resultados/09_demanda_capacidad/demanda_capacidad_critica.json`):

```
caso COMBO · id 1 · tipo 70x70
  P_d = 13.20 kN (axial de demanda)
  M_d = 1104.28 kN·m (momento de demanda, extremo mayor)
  radio = 0.894  → DENTRO de la curva P-M (Pcap/Mcap de fibra vs H.A.)
  criterio: P por proyección axial (z vertical), M flexión transversal al eje
```

En el visor, el doble clic sobre la columna dibuja el punto de demanda sobre el diamante
P-M (`PickHighlight.cs` → `Plot2D.DrawPMLab`) e indica si queda dentro o fuera. Para
demanda/capacidad **dinámica** (variar λ y ver cómo se mueve el punto de demanda) hace
falta el slider de combinación del jueves 24.

---

## 6. Sidequest carga móvil — SQ4 (estado: no implementada)

**No implementada al corte.** No existe ninguna fuente de posición de usuario ni lógica
de transferencia de carga localizada en Unity. El enunciado (SQ4) exige definir una regla
de transferencia simple y explícita:

- Posición del usuario → panel/región tributaria → vigas receptoras → carga adicional → respuesta.

**Propuesta para el viernes 25 (alcance acotado):**
1. Usar la posición de la cámara proyectada en planta (nivel `y`) como `(x, z)` del usuario.
2. Localizar la **celda tributaria** que contiene la posición (se dispone de las 306
   regiones tributarias y de `tributary_map.js`).
3. Regla explícita: reparto entre las vigas del panel **proporcional a la distancia**
   inversa a sus apoyos (regla defendible y acotada).
4. Mostrar `P_user`, panel activo, vigas receptoras y su magnitud; actualizar los
   diagramas M/V de las vigas receptoras superponiendo el efecto de la carga localizada.

No se modela la losa como placa (utilidad didáctica de camino de carga idealizado).

---

## 7. Preparación móvil (estado: sin build; plan para el viernes 25)

**Estado real:** el proyecto Unity no tiene build móvil (no hay APK/AAB). En
`ProjectSettings` hay configuraciones de plataforma **Android e iOS** declaradas, pero
ninguna build generada ni teléfono identificado.

**Plan de preparación (acciones concretas):**
1. **Identificar el teléfono compatible:** proponer un Android con soporte **ARCore**
   (necesario para la Semana 6) y GPU suficiente para IL2CPP; ejemplo candidato del
   grupo: Samsung Galaxy A54 5G (IMU + cámara compatibles con ARCore). Confirmar el
   dispositivo real del equipo antes del build.
2. **Configuración del build Android:** `Build Settings → Android`, platform target
   ARM64, paquete com.grupo6.p1, scripting backend **IL2CPP**, memoria de texturas
   compatible con celulares gama media.
3. **Crear build inicial de prueba** (renderer URP, URP=Universal Render Pipeline ya en
   uso) y verificar que el visor arranca, carga `StreamingAssets/analysis_map.json` y
   permite navegar/inspeccionar en pantalla táctil (mínimo: navegación + doble clic
   táctil equivalente).
4. La AR se desarrolla en la Semana 6 (marker → pose → anchor → elemento + resultado).

---

## 8. UX estructural — evaluación del viewer (estado real)

Evaluación cualitativa sobre los comportamientos verificados en código y en la réplica
Unity del visor:

**Fortalezas (cumplen la mayoría de los "elementos mínimos" del enunciado):**
- **Cambio de modo explícito:** VISUALIZACION ⇄ ANALISIS (TAB) + panel DATOS (B) con
  modebar superior central y leyenda inferior con capas activables (9 capas: columnas,
  vigas X/Y, muros, losas, metálicas, nodos, ejes, diafragmas).
- **Trazabilidad a los datos:** doble clic sobre viga → N/V/M/DEF + cargas tributarias;
  sobre columna/muro hormigón → curva P-M + punto de demanda (`VerifPanel.cs` para 147/261/446).
- **Convenciones de ingeniería consistentes:** coordenadas `(x, altura, z)=(f0,f2,f1)`,
  momentos `(f3,f5,f4)`, demanda P-M = `|F·u|` y `|M−(M·u)u|`; colormap por **percentil 90**
  evita outliers dominantes; barra de colores con unidades por vista (mm / kN·m / kN).
- **Verificación por render.** El mapa JSON que alimenta Unity se coteja contra los CSVs
  y contra los valores fuente al exportar (GUIA_EXCEL), evitando divergencias HTML/Unity.

**Debilidades / pendientes de UX:**
- Sin **superposición instantánea** (sliders λ) — la acción más valiosa de la semana.
- Sin **latencia controlada**: `Rebuild()` recrea todos los palitos al cambiar caso/vista;
  en celulares de gama media requerirá caché (objeto pool) en la preparación móvil.
- HUD IMGUI no escalado a densidad de píxeles alta; en build móvil se debe revisar
  `Screen.width`/`height` y el área del panel.
- Sin **ayuda contextual** (tooltips) que explique qué calcula OpenSees y qué representa
  Unity (objetivo de aprendizaje del enunciado).

---

## 9. Uso de IA (funcionalidad compleja implementada por agente + verificación)

Se documentan las piezas de mayor complejidad generadas/revisadas por agentes y **cómo
se verificó cada una** (criterio del curso: "verificar críticamente el código generado
por IA"):

| Funcionalidad (agente) | Dónde | Cómo se verificó |
|---|---|---|
| Traspaso completo del visor HTML → Unity (modo análisis, HUD, doble clic, panel DATOS) | `Unity/Assets/Scripts/{AnalysisMode, ViewerHud, PickHighlight, DataPanel, Plot2D}.cs` | Compilación batch-mode sin errores C# (`Exiting batchmode successfully`), cotejo de valores con el análisis fuente y con el visor HTML |
| Exportadores CSV compatibles con Excel (tablas + fuerzas por caso) | `opensees/exportar_tablas_excel.py`, `exportar_fuerzas_por_caso.py` | Reapertura de cada CSV contra el JSON de origen y conversión decimal; fuerzas/desplazamientos cotejados con Unity (GUIA_EXCEL, commit `d0bac9b`) |
| Diagramas 2D M/V/N de viga/columna/muro con sectores de extremo | `scripts/diagramas_2d.py` | Auditoría sobre las 108 vigas de vano completo (`verificar_diagramas_viga.py`): cierre corte+momento a < 3 %, viga 147 al **0.00 %**, regla B de extremo j |
| Curvas P-M diamante simétrico + demanda | `exportar_analysis_map.py` embebe P-M; `Plot2D.DrawPMLab` | Rama +/− y conectividad Pcap/Mcap comparadas contra la curva de fibra; radio de demanda 0.894 dentro (sección 5) |
| Configuraciones de refuerzo (φ40 muros, 16φ28 columna) | `scripts/parte_d_muros.py`, `parte_d_fiber.py` | 79/79 muros y columna 70×70 dentro de capacidad en COMBO (commits `c57e75c`, `70e1c4c`) |
| Verificación de superposición composicional | `opensees/superposicion.py`, `tests/test_superposicion.py` | 4 tests que incluyen: suma ponderada exacta, COMBO explícito vs `combine()` (tol 1e-6), G sola, EX sola (sección 4) |

**Regla aplicada:** ningún producto del agente se integra sin su verificación numérica o
sin test. La convención del proyecto (AGENTS.md) exige umbrales 1e-10 para equilibrio,
tributarias y superposición; donde el resultado existente cumple 1e-6 pero no 1e-10
(desplazamientos), el hecho queda documentado y no se oculta.

---

## 10. Cambios implementados en la semana (hasta el corte)

| Commit | Cambio |
|---|---|
| `a197b43` | Mejora de interfaz del visor Unity y resaltado de selección corregido |
| `d0bac9b` | Exportadores a CSV compatibles con Excel (27 tablas + 5 CSV de fuerzas por caso) + `GUIA_EXCEL.md` + `00_readme.md` actualizado |

(Los traspasos de funcionalidad del visor originan de `8472043` y `da2e7b3`, semana 4;
las modificaciones de sección/carga originan de `70e1c4c`, `c57e75c`, `7c72050`, semana 3.)

---

## 11. Pendientes para el cierre del viernes 25 (bloqueantes)

> **P1 — Superposición interactiva (sliders λ).** Implementar en Unity el control de los
> 4 λ sobre los casos base y recalcular deformada/M/N/V/reacciones/P-M en vivo reutilizando
> `combine()` (o su equivalente en C# sobre `AnalysisMap`). Verificación: un mínimo de 3
> combinaciones que reproduzcan los casos explícitos (sección 4) y un COMBO armado con
> sliders igual a `COMBO` pre-computado.
>
> **P2 — Demanda/capacidad dinámica:** al variar λ con los sliders, actualizar el punto de
> demanda sobre las curvas P-M (el motor de interacción P-M ya existe).
>
> **P3 — Preparación móvil:** identificar teléfono compatible, configurar el build Android
> (IL2CPP/ARM64) y generar el APK de prueba; revisar HUD a densidad alta y pool de objetos
> para el costo de `Rebuild()`.
>
> **P4 — SQ4 (carga móvil):** definir la regla de transferencia (propuesta en sección 6)
> y visualizar panel activo + vigas receptoras + cambio de diagramas; requiere alineación
> de coordenadas cámara ↔ planta.
>
> **P5 — Prueba sistemática del visor en Play Mode** (distribución del HUD, encuadre,
> rendimiento) antes del build móvil.

---

## 12. Lecciones aprendidas

- **Separar "ver la combinación" de "combinar interactivamente":** el catálogo de casos
  (1–5) ya muestra el resultado pre-computado; la interactividad real de la semana son los
  λ editables, y el motor algebraico para ellos ya está testeado (`combine()`), no hay que
  reinvertir la matemática.
- **El reanálisis manual es una ruta legítima del proyecto base:** el ciclo
  dato → OpenSees → exportar_analysis_map → StreamingAssets ya está probado 2 veces
  (carga y refuerzo de muros) y recarga en Unity sin recompilar la escena.
- **Ser explícito con los umbrales:** la verificación cumple 1e-6 y útiles 1e-10 en
  reacción/fuerza, pero desplazamiento queda en 6.78e-9; documentarlo antes de que el
  umbral aparezca como fallo en la evaluación.
- **UX de ingeniería ≥ gráficos:** el valor está en hacer preguntable el modelo
  (doble clic → datos verificados), no en el realismo; mantener la traza de qué calcula
  OpenSees y qué representa Unity.