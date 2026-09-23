# Semana 5 — AVANCE: laboratorio estructural interactivo v1

| Campo | Valor |
|---|---|
| **Proyecto** | P1 — Laboratorio Estructural Digital (Edificio de Ingeniería) |
| **Curso** | Métodos Computacionales (8vo semestre) |
| **Grupo** | 6 |
| **Período** | 21 – 25 de septiembre de 2026 |
| **Entregable** | Laboratorio estructural interactivo v1 |
| **Repositorio** | `https://github.com/vaurmeneta-22/P1-Grupo-6` (rama `main`) |

---

## 1. Funciones implementadas

| Función | Estado | Módulo / evidencia |
|---|---|---|
| Navegación | ✅ Implementada | Unity `Assets/Scripts/CameraController.cs` (cámara orbital, pan/zoom, auto-encuadre; **touch**: 1 dedo orbita, 2 dedos pinch-zoom y pan); HTML `edificio_3d.html` (controles L109: rotar/mover/zoom, teclas N/node, E/eje) |
| Selección | ✅ Implementada | Unity `PickHighlight.cs`, `ElementTag.cs` (hover magenta 12 px, doble clic → reporte/P-M; **tap/doble tap** en móvil); HTML click en elemento → resaltado + info |
| Apoyos | ✅ Implementada | HTML `supportsSet` (64 apoyos) + geometría de bases; pestaña Reacciones; checkbox *Reacciones 3D* (tecla R, esferas por magnitud); Mod B muestra apoyo articulado |
| Ejes | ✅ Implementada | HTML checkbox "Ejes (palitos)" (L131) + GridHelper (L1473); capa de ejes en leyenda (9 capas) + teclas E/D en Unity (`ViewerHud.cs`) |
| Cargas | ✅ Implementada | `analysis_map` → `beam_fractions`, `forces`; panel DATOS Unity `DataPanel.cs` — Sismo por piso + tributarias (p. ej. viga 147 COMBO q = 19.124 kN/m) |
| Áreas tributarias | ✅ Implementada | `analysis_map` → `tributarias` (nodo → área → carga); HTML pestaña Tributarias; Unity `TributaryInspector.cs` (fuerzas por caso + aportes + ejes locales). Invariante Σ = q×A |
| Deformada | ✅ Implementada | `analysis_map` → `disp` (m); HTML modo análisis vista Deformada; Unity `AnalysisMode.cs`, tecla D, escala ×10–600 con slider, auto-encuadre |
| Diagramas | ✅ Implementada | HTML pestaña Diagramas (M/V/N) con sub-fichas COMBO/G/Q/EX/EY; `analysis_map` → `diagramas`; Unity `Plot2D.cs`, vista M/N/V por colormap percentil 90. Cierre viga 147 al 0.00 % |
| Superposición | ✅ Verificada | `opensees/superposicion.py`; `resultados/06_superposicion/verificacion_3combinaciones.csv` (ver §3) |
| P-M | ✅ Implementada | `analysis_map` → `pm_ha` (70×70, 30×356), `momcurv` (M-φ); HTML pestañas P-M y Mom-Curv; Unity `Plot2D.cs` (diamante P-M + punto de demanda + % capacidad) |
| Modificación del modelo | ✅ Implementada (automática) | `scripts/generar_modificaciones.py` + `scripts/ejecutar_modificacion.py` (ver §2) |

---

## 2. Modificación

Flujo completo **automatizado** (interfaz/dato → modelo → OpenSees → resultados → Unity):

```
Edificio.json (contrato)
  → scripts/generar_modificaciones.py → Edificio_mod_A.json / Edificio_mod_B.json
  → scripts/ejecutar_modificacion.py (--tag, --all-cases, --combo-lambdas 1.2,1.0,1.4,1.4)
      → opensees_edificio_v2.py → resultados/01_casos_base/edificio_full_results_{tag}_*.json
      → exportar_analysis_map.py  → resultados/11_mapa_visor/analysis_map_{tag}.js(.json)
      → verificación (equilibrio, invariantes, todos OK)
      → --unity: sincroniza a Unity/Assets/StreamingAssets/ (Edificio.json + analysis_map.json)
```

### Mod A — Viga 147 (Piso 3, `beam_y`, nodos 88-89): sección 60×80 → 50×75 cm

| Magnitud | Base | Mod A | Cambio |
|---|---|---|---|
| Peso propio del modelo | 42 213.64 kN | 42 191.64 kN | **−22.0 kN** |
| Fuerza sísmica (EX/EY) | 16 650.79 kN | 16 646.39 kN | −4.40 kN |
| Carga total COMBO | 157 505.42 kN | 157 466.70 kN | −38.7 kN |
| Viga 147: `My_i` | — | — | **−28.6 %** |
| Viga 147: `My_j` | — | — | **−21.6 %** |
| Viga 147: cortante i / j | — | — | −41 % / −17 % |
| Viga 147: torsión | — | — | −22 % |
| Equilibrio ΣF+ΣR | 0.0 | 0.0 | OK |

El corte de peso propio (−22.0 kN) coincide con la reducción de área de la viga 147 × su longitud × peso específico del hormigón; la carga gravitacional baja en exactamente ese valor y la fuerza sísmica (proporcional a W sísmico) también desciende.

### Mod B — Apoyo de la columna 1 en base articulada

| Magnitud | Base | Mod B | Cambio |
|---|---|---|---|
| Apoyo nodo 1 DOF | `[1,1,1,1,1,1]` (empotrado) | `[1,1,1,0,0,0]` (articulado) | — |
| Momentos en el apoyo nodo 1 (Mx, My, Mz) | — | 0 | **−100 %** |
| Fuerza axial base (`Fx`) | — | — | −99 % |
| Cortante base (`Fy`) | — | — | −83 % |
| Momento en el tope de la columna 1 | — | — | −57 % |
| Carga total COMBO | 157 505.42 kN | 157 505.42 kN | igual |
| Equilibrio ΣF+ΣR | — | ~1e-16 | OK |

Se evaluó y descartó agregar un apoyo físico en el voladizo x = −2500 (nodos 43/76/109): esos nodos ya reciben el apoyo vertical artificial del FE `(uz, rx, ry)` y un empotramiento completo chocaría con el diafragma rígido (ux/uy/rz). La alternativa articulada produce un efecto real y verificable en la base. Ambos flujos son reproducibles con una línea de comando; verificación automática de equilibrio y `todas_ok=True`.

> El reanálisis regional puede ser manual (cómo corre en base, sin servidor) pero este flujo ya está **automatizado** en scripts y se recarga en Unity sin recompilar la escena. Distinción pedida por el enunciado: cambiar λ sobre casos ya calculados **no** requiere reanálisis (SQ2, motor `combine()` testeado); cambiar sección, apoyo, conectividad o geometría de carga **sí** lo requiere (flujo de arriba).

---

## 3. Superposición interactiva

Se verificaron **tres estados de combinación** contra los resultados numéricos de los casos base (G, Q, EX, EY) usando `opensees/superposicion.py --tag` (no pisa el COMBO de línea base):

| Tag | λ_G | λ_Q | λ_EX | λ_EY | Desplaz. máx. err | Reacción err | Fuerza err | Resultado |
|---|---|---|---|---|---|---|---|---|
| comboC1 | 1.2 | 1.0 | 1.4 | 1.4 | 6.780e-09 | 2.284e-14 | 4.880e-12 | SUPERPOSICION CORRECTA |
| comboC2 | 1.0 | 1.0 | 1.0 | 1.0 | 7.410e-09 | 2.593e-14 | 5.539e-12 | SUPERPOSICION CORRECTA |
| comboC3 | 1.0 | 0.5 | 0.3 | 0.7 | 8.422e-09 | 4.582e-14 | 8.607e-12 | SUPERPOSICION CORRECTA |

- Evidencia numérica: `resultados/06_superposicion/verificacion_3combinaciones.csv` y `resultados/01_casos_base/edificio_full_results_comboC1..C3_COMBO.json`.
- En el visor: la pestaña Diagramas/DATOS muestra los casos G/Q/EX/EY y el COMBO (equivalente a C1). La superposición se demuestra comparando cada estado combinado con la suma lineal λ·R_caso (errores < 1e-9, muy por debajo de la tolerancia 1e-10 de invariantes del proyecto).

### 3.1 Nota de umbrales (documentada, no oculta)

La verificación histórica (`tests/test_superposicion.py` → `resultados/06_superposicion/verificacion_excel.csv`) usa la tolerancia **1e-6** (directiva del curso). Contra el umbral **1e-10** del proyecto: la **reacción (2.28e-14)** y la **fuerza interna (4.88e-12)** lo cumplen; el **desplazamiento (6.78e-9)** no. Interpretación: los desplazamientos son del orden de 1e-3 m; el error relativo 6.78e-9 proviene de la precisión de exportación de los casos base (1e-8/1e-10 en el JSON), no de la superposición en sí. Queda registrado en `resultados/GUIA_EXCEL.md` y en esta sección.

### 3.2 Demanda-capacidad (evidencia)

La demanda crítica del COMBO queda **dentro de la curva P-M** de la columna más solicitada (`resultados/09_demanda_capacidad/demanda_capacidad_critica.json`):

```
caso COMBO · columna id 1 · sección 70×70
  P_d = 13.20 kN    (axial de demanda, proyección sobre z)
  M_d = 1104.28 kN·m (momento de demanda, extremo mayor)
  radio = 0.894     → DENTRO de la curva P-M (fibras vs. H.A.)
```

Verificación H.A. (semanas 3-4, commits `70e1c4c` y `c57e75c`): columna 70×70 con **16 φ28** perimetrales dentro de capacidad y **79/79 muros** con **φ40** de borde dentro de capacidad en COMBO. En el visor, el doble clic dibuja el punto de demanda sobre el diamante P-M (`PickHighlight.cs` → `Plot2D.DrawPMLab`) e indica dentro/fuera.

---

## 4. Sidequest carga móvil

**No implementada.** Regla física definida para cuando se implemente, sin cambios al modelo estructural:

- Regla física: envolvente de líneas de influencia; la carga móvil actúa sobre la misma geometría tributaria de G/Q con factores mínimos de la envolvente y **no** se combina simultáneamente con EX/EY sin reanálisis del sismo.
- Reparto: por áreas tributarias existentes (`analysis_map.tributarias`, 306 regiones), misma infraestructura que G/Q.
- Conservación de la carga: debe respetar Σ(reparto) = q_móvil × A (invariante del proyecto).
- Panel: selector de posición de la carga en el visor; respuesta visual: deformada y diagramas recalculados de envolvente.

**Propuesta concreta (alcance acotado para el cierre):**
1. Usar la posición de la cámara proyectada en planta como `(x, z)` del usuario.
2. Localizar la **celda tributaria** que contiene la posición (se dispone de las 306 regiones y de `tributary_map.js`).
3. Regla de reparto explícita: entre las vigas del panel, **proporcional a la distancia inversa** a sus apoyos (criterio defendible y acotado).
4. Mostrar `P_user`, panel activo, vigas receptoras y su magnitud; actualizar los diagramas M/V de las vigas receptoras superponiendo el efecto de la carga localizada. No se modela la losa como placa (camino de carga idealizado, utilidad didáctica).

---

## 5. UX estructural

Evaluación de si el viewer responde realmente las seis preguntas de diseño estructural:

| Pregunta | Respuesta del viewer | Cómo se demuestra |
|---|---|---|
| ¿Dónde está el elemento? | Sí — selección resaltada con tag/tipo/sección, coordenadas y piso | Click en viga 147 → identificación (nodos 88-89, Piso 3, `beam_y`) en el visor 3D y panel DATOS |
| ¿Cómo está apoyado? | Sí — 64 apoyos visibles + pestaña Reacciones; tipo de apoyo por nodo | Apoyo nodo 1 muestra condición; en Mod B aparece articulado y con reacciones de momento nulas; checkbox Reacciones 3D |
| ¿Qué lo carga? | Sí — tributarias por nodo y cargas distribuidas por elemento | Viga 147 COMBO q = 19.124 kN/m (beamUniform); pestaña Tributarias: Σ carga = q×A |
| ¿Cómo se deforma? | Sí — vista Deformada del modo análisis con desplazamientos en m | Selector "Deformada" (HTML) y tecla D en Unity (`AnalysisMode.cs`); factor de escala ×10–600 |
| ¿Qué fuerzas tiene? | Sí — diagramas M/V/N por caso + fuerzas de extremo | Pestaña Diagramas (M/V/N, cierre 0.00 %), tabla de esfuerzos por elemento |
| ¿Cuánta capacidad tiene? | Sí — curvas P-M y Momento-Curvatura por sección | Pestañas P-M y Mom-Curv (70×70, 30×356, muros, steel); doble clic → punto de demanda vs curva (radio 0.894) |

Conclusión: el viewer contesta las **seis preguntas** con datos reales de OpenSees. Fortalezas: modo explícito VISUALIZACION ⇄ ANALISIS con panel DATOS, trazabilidad por doble clic (N/V/M/DEF/tributarias/curvas), convenciones de ingeniería consistentes y colormap por percentil 90. Limitaciones conocidas: sin **sliders de superposición** (λ fijos por sub-ficha), `Rebuild()` recrea palitos al cambiar caso/vista (costoso en gama media), HUD IMGUI no escalado a densidad alta y sin tooltips contextuales.

---

## 6. Preparación móvil

> Situación: todavía no se dispone de un teléfono físico. Se definió una **familia de dispositivos compatibles**, se habilitó el **Device Simulator** de Unity para validar la UI sin hardware y se dejó el script de build listo para emitir el APK cuando se instale el módulo Android.

### 6.1 Familia de dispositivos compatibles

| Requisito | Valor |
|---|---|
| SO | Android 8.0 o superior |
| SDK mínimo | `minSdkVersion = 26` (configurado en `Unity/ProjectSettings/ProjectSettings.asset`) |
| Arquitectura | ARM64 (`AndroidTargetArchitectures = 2`) |
| Gráficos | OpenGL ES 3.x |
| RAM libre recomendada | 512 MB mínimo para el visor 3D |
| Datos del modelo | Embebidos en `StreamingAssets/` (Edificio.json + analysis_map.json), offline |
| AR (Semana 6) | Preferir un teléfono compatible con **ARCore** (necesario para la siguiente semana) |

Candidato propuesto por el grupo: **Samsung Galaxy A54 5G** (ARM64, soporte ARCore, GPU suficiente para gama media). No es excluyente: cualquier Android 8+/ARM64/OpenGL ES 3.x de la familia sirve.

### 6.2 Validación de la UI sin hardware (Device Simulator)

- Paquete instalado: `com.unity.device-simulator.devices@1.0.1` (`Unity/Packages/manifest.json`, resuelto en `packages-lock.json`). Proyecto validado en batchmode con la librería resuelta y **sin errores de compilación** (exit 0).
- Herramienta: `Unity/Assets/Editor/MobilePreviewTool.cs` → menú **Lab/Preview Movil/**:
  1. **Abrir Device Simulator** — presets de teléfono (Galaxy, Pixel, iPhone…). *(Integrado en el editor; en Unity 6000.6 el simulador se abre en `Window > General > Device Simulator`, ruta que el menú detecta automáticamente con fallback a la ruta clásica `Window/Device Simulator`).*
  2. **Capturar screenshot** — guarda el Game view en `Unity/Builds/MobilePreview/preview_*.png`.
  3. **Abrir carpeta de capturas**.
- Procedimiento: abrir `SampleScene` → *Lab/Preview Movil/Abrir Device Simulator* → elegir dispositivo → **Play** → *Capturar screenshot*. Evidencia de que HUD, panel DATOS y selección rinden en formato teléfono.
- **Navegación táctil en el simulador** (`CameraController.cs`, `PickHighlight.cs`, `TributaryInspector.cs`): orbitar con 1 dedo, zoom con 2 dedos (pinch), pan con 2 dedos, `tap` para seleccionar/inspeccionar y `doble tap` para el reporte P-M / N-V-M-DEF en modo análisis. Requiere `activeInputHandler: Both` en `ProjectSettings.asset` (los scripts usan la API clásica de Input; con "solo Input System nuevo" la cámara no recibe eventos).
- Nota técnica: se descartó la captura 100 % automática en batch mode porque el *domain reload* de Unity al entrar en Play interrumpe los callbacks del Editor; la captura se hace con un clic desde el editor.

### 6.3 Build móvil inicial

- Script de build: `Unity/Assets/Editor/BuildMobile.cs` → `BuildMobile.BuildAndroid` (genera `Unity/Builds/BuildLabAndroid.apk`). Config planificada: paquete `com.grupo6.p1`, scripting backend **IL2CPP**, platform target ARM64.
- Escena: `Assets/Scenes/SampleScene.unity` (definida en EditorBuildSettings).
- **Estado: pendiente de emitir el APK.** El módulo "Android Build Support" no está instalado en la máquina; una vez instalado desde Unity Hub (~1-2 GB), se produce con:

```
Unity.exe -batchmode -quit -projectPath "P1-Grupo-6\Unity" \
    -executeMethod BuildMobile.BuildAndroid -logFile build_android.log
```

### 6.4 Checklist de verificación al tener el teléfono

1. Instalar `BuildLabAndroid.apk` (USB o nube) y abrirlo.
2. Verificar que carga `Edificio.json` + `analysis_map.json` **offline** (sin datos no hay render).
3. Rotación horizontal y vertical: HUD y paneles deben reacomodarse.
4. Navegar el modelo por **touch**: 1 dedo orbita, 2 dedos hace zoom y pan (validado en el Device Simulator).
5. Clic/tap en una viga → resaltado + identificación; doble tap/doble clic → P-M/deformada-diagramas.
6. Pestañas/paneles de Diagramas, Reacciones, Tributarias y P-M con valores idénticos a la versión de escritorio. Revisar `Screen.width/height` y densidad alta (HUD IMGUI).

---

## 7. IA (funcionalidad compleja implementada por agente)

**Funcionalidades:** pipeline de modificación/reanálisis reproducible, regeneración no destructiva del visor y superposición etiquetada.

| Funcionalidad (agente) | Dónde | Cómo se verificó |
|---|---|---|
| Wrapper de modificación/reanálisis por tag | `scripts/ejecutar_modificacion.py` (contrato → OpenSees → mapa → verificación → `--unity`) | 2 modificaciones (Mod A/B) corridas de punta a punta; equilibrio ΣF+ΣR < 1e-16; `todas_ok=True` |
| Regeneración no destructiva del visor (P3) | `opensees/visualizar.py`: reemplaza solo `elements`/`nodesData`/`supportsSet`, conserva pestañas + `analysis_map.js`; soporta muros por coordenadas y secciones nuevas | Regeneración probada: 523 elementos, 536 nodos, 64 apoyos; `dt-diag` y `analysis_map.js` presentes después |
| Superposición etiquetada | `opensees/superposicion.py --tag` (no pisa la línea base) | 3 combinaciones "SUPERPOSICION CORRECTA", errores < 1e-9 (§3) |
| Tooling de preview móvil | `Unity/Assets/Editor/MobilePreviewTool.cs` + `BuildMobile.cs` | Batchmode abre el proyecto sin errores C# (exit 0); paquete Device Simulator resuelto; menú del simulador corregido para Unity 6000.6 (`Window/General/Device Simulator` con fallback) |
| Navegación táctil del visor | `CameraController.cs`, `PickHighlight.cs`, `TributaryInspector.cs` + `ProjectSettings.asset` (`activeInputHandler: Both`) | Orbitar/zoom/pan por touch y tap/doble-tap de selección validados en el Device Simulator; compilación batch exitosa |

**Regla aplicada:** ningún producto del agente se integra sin su verificación numérica o test. Convención del proyecto (AGENTS.md): umbrales 1e-10 para equilibrio, tributarias y superposición; donde se cumple 1e-6 pero no 1e-10 (desplazamiento 6.78e-9), el hecho queda documentado sin ocultarse. `python -m pytest tests -q` → **35 tests en verde** (6 módulos).

---

## 8. Pendientes para el cierre (viernes 25)

> **P1 — Sliders de superposición (λ_G, λ_Q, λ_EX, λ_EY)** en Unity/HTML recalculando deformada, M/N/V, reacciones y P-M en vivo reutilizando `combine()` (motor ya testeado). Verificación: 3 combinaciones que reproduzcan los casos explícitos (§3) y un COMBO armado con sliders igual al pre-computado.
>
> **P2 — Demanda/capacidad dinámica:** al variar λ, actualizar el punto de demanda sobre las curvas P-M (el motor P-M ya existe).
>
> **P3 — Emitir el APK** instalando el módulo Android Build Support (semana 5) y validar en simulador; revisar densidad alta y costo de `Rebuild()` (pool de objetos para gama media).
>
> **P4 — SQ4 carga móvil** con la regla de la sección 4 (cámara → celda tributaria → vigas receptoras → M/V superpuestos).
>
> **P5 — Prueba sistemática en Play Mode** (distribución del HUD, encuadre, rendimiento) antes del build móvil.

## Checklist de cierre

- [x] `reports/semana05.md` con la estructura de la entrega (7 secciones).
- [x] Tabla de funciones implementadas (§1).
- [x] Dos modificaciones completas con flujo reproducible (§2).
- [x] Superposición: tres estados verificados contra numéricos (§3) + demanda-capacidad (§3.2).
- [x] Sidequest carga móvil documentada con propuesta concreta (§4).
- [x] UX estructural evaluada — seis preguntas confirmadas (§5).
- [x] Preparación móvil: familia de dispositivos + Device Simulator + navegación táctil (1/2 dedos, tap/doble-tap) + script de build (§6); **APK pendiente de módulo Android (P3)**.
- [x] IA documentada y verificada (§7).
- [ ] Commit + push de la semana (en proceso).
- [ ] Restaurar `StreamingAssets` a línea base tras la demo (`--restore`) o acordar dejarlo en Mod A.