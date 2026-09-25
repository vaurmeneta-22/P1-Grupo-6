# Semana 5 — AVANCE: laboratorio estructural interactivo v1

> Estado al cierre (24-09): sliders **G/Q/EX/EY** implementados en Unity; la
> combinación vive en memoria (`AnalysisMapCombination.cs`) y actualiza deformada,
> fuerzas de extremo, reacciones, diagramas y demanda P-M sin reanálisis. En esta
> sesión se verificó el motor C# real sobre los dos mapas (147 945 comprobaciones por
> mapa, §3.3) y la suite Python (`35 passed`). La validación **visual** en
> Play Mode queda aprobada para el flujo de escritorio; queda el ensayo en el dispositivo final. Discrepancia de desplazamiento
> 6.78e-9 documentada en §3.1 (no se declara cumplimiento de 1e-10). El HTML queda
> obsoleto; el visor oficial es Unity. SQ4 se incorporó como prototipo Unity
> (`MobileLoadSQ4.cs`): en modo ANÁLISIS, doble clic sobre losa fija el panel,
> resalta losa/vigas receptoras, muestra reparto de `P_user`, conservacion de
> carga y respuesta visual con martillo/carga móvil arrastrable, lineas y flechas.
> La interfaz Unity quedó organizada en cuatro pestañas: **Visualización / Modificaciones / Análisis / Datos**. Desde **Modificaciones** se ejecutan Mod A, Mod B y restauración base sin abrir VS Code; desde **Visualización** se añadió buscador por tipo+ID con auto-encuadre, resaltado y restauración de vista.
> [Guion reproducible y alcance actual](../docs/demo_laboratorio_interactivo.md).
>
> **Objetivo del avance:** convertir el visor Unity en un laboratorio interactivo en
> el que el usuario combine G/Q/EX/EY con sliders, observe deformada/fuerzas/
> reacciones/diagramas/P-M y distinga cuándo basta combinar casos ya calculados y
> cuándo se requiere reanálisis (sección, apoyo, material, conectividad o geometría
> de carga), conservando la trazabilidad con las corridas OpenSees y las dos
> modificaciones reproducibles (§2).

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
| Superposición interactiva (sliders λ) | ✅ Implementada y validada en Play Mode | `AnalysisMode.cs` (UI) + `AnalysisMapCombination.cs` (motor C# en memoria, ver §3.3); verificado por `tests/test_viewer_combination.ps1` (147 945 comprobaciones por mapa) |
| P-M | ✅ Implementada | `analysis_map` → `pm_ha` (70×70, 30×356), `momcurv` (M-φ); HTML pestañas P-M y Mom-Curv; Unity `Plot2D.cs` (diamante P-M + punto de demanda + % capacidad) |
| Modificación del modelo | ✅ Implementada (automática) | `scripts/generar_modificaciones.py` + `scripts/ejecutar_modificacion.py` (ver §2) |
| Modificación desde Unity | ✅ Implementada | `ModificationMode.cs`: pestaña **MODIFICACIONES**, botones Base/Mod A/Mod B, ejecución de Python/OpenSees, log, historial persistente y recarga de escena |
| Buscador de elementos | ✅ Implementado | `ElementSearchPanel.cs`: en **VISUALIZACIÓN**, búsqueda por tipo+ID, auto-encuadre, resaltado amarillo y limpieza/restauración de cámara/materiales |
| SQ4 carga móvil | ✅ Prototipo Unity validado en Play Mode | `MobileLoadSQ4.cs`: en modo ANÁLISIS, doble clic sobre losa; regla física declarada, panel, reparto, conservación `ΣP_i=P_user` y respuesta visual con losa/vigas/martillo arrastrable/flechas |

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

Además del uso por terminal, el flujo quedó integrado en Unity mediante la pestaña
**MODIFICACIONES** (`ModificationMode.cs`). El usuario puede ejecutar:

- **Restaurar Base**: corre `scripts/ejecutar_modificacion.py --restore` y vuelve a sincronizar `StreamingAssets` con la línea base.
- **Aplicar Mod A**: genera modificaciones y ejecuta `--tag modA --json Edificio_mod_A.json --element 147 --unity`.
- **Aplicar Mod B**: genera modificaciones y ejecuta `--tag modB --json Edificio_mod_B.json --element 76 --unity`.

Unity lanza Python/OpenSees con `System.Diagnostics.Process`, captura el log en el
panel, registra un historial persistente de modificaciones realizadas (`PlayerPrefs`)
y recarga la escena al terminar correctamente para leer el nuevo `Edificio.json` y
`analysis_map.json`. Esta integración evita abrir VS Code para la demostración, pero
mantiene la regla estructural: sección/apoyo sí requieren reanálisis.

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

- Evidencia numérica: `resultados/06_superposicion/verificacion_3combinaciones.csv` y las corridas explícitas `resultados/01_casos_base/edificio_full_results_comboC1_COMBO.json`, `..._comboC2_COMBO.json` y `..._comboC3_COMBO.json`.
- La tabla anterior contrasta combinaciones con corridas independientes. Los errores de desplazamiento son del orden de 1e-9 y **superan** la tolerancia 1e-10 del proyecto; ver §3.1. La prueba del motor Unity (§3.3) verifica por separado que los sliders reconstruyen exactamente la suma λ·componente de los casos exportados.

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

### 3.3 Motor de combinación en Unity (sliders λ)

`AnalysisMapCombination.cs` lee los cuatro casos base del mapa exportado y publica `COMBO` en memoria con el mismo contrato JSON (unidades y signos conservados: kN, kN·m, m). Reglas del motor:

- Suma lineal por componente con signo: `R = λ_G·R_G + λ_Q·R_Q + λ_EX·R_EX + λ_EY·R_EY`.
- Los casos base **no se mutan**: cada `TryCombine` vuelve a sumar desde ellos.
- Resultantes, extremos, diagramas y demanda P-M se calculan **después** de la suma (no se suman magnitudes, radios ni porcentajes de utilización).
- Rango λ ∈ [−10, 10]; en la UI los sliders van 0..2 para G/Q y −2..2 para EX/EY. Rechazo atómico si falta un caso, hay IDs incompatibles, malla de diagrama distinta o resultado no finito (no se publica nada a medias).
- `CombinationRevision` fuerza la actualización del inspector y de la ficha P-M del elemento activo (`TributaryInspector.cs`, `PickHighlight.cs`).
- El visor HTML conserva su funcionamiento anterior (λ fijos por sub-ficha); los sliders se incorporaron en Unity.

Verificación ejecutable del motor sobre los mapas reales:

```powershell
./tests/test_viewer_combination.ps1                                  # StreamingAssets (modelo activo)
./tests/test_viewer_combination.ps1 -Map resultados/11_mapa_visor/analysis_map.json   # línea base
```

Resultado en esta sesión: **147 945 comprobaciones por mapa** — siete combinaciones (cero, cada caso aislado, sismo negativo, 1.2/1.0/1.4/1.4 y 1.0/0.5/−0.3/0.7), inmutabilidad de los casos base y rechazo atómico ante NaN/caso ausente. Tolerancia absoluta 1e-10 sobre componentes exportadas. Esta prueba verifica la suma en el viewer; no sustituye el contraste con una corrida OpenSees independiente (esa contrastación es la de la tabla de §3).

---

## 4. Sidequest carga móvil

**Implementada como prototipo Unity**, sin cambios al modelo estructural ni al visor HTML (obsoleto):

- Activación: doble clic sobre una losa en modo **ANÁLISIS** (`MobileLoadSQ4.cs` + `PickHighlight.cs`). La tecla `U` permite cerrar/reabrir el último estado activo.
- Identificación: raycast del doble clic; si el primer elemento interceptado es una losa, toma ese panel/región y lo fija hasta cerrar SQ4 o seleccionar otra losa.
- Reparto: busca las vigas receptoras en `analysis_map.tributarias` filtrando los aportes cuyo campo `losa` coincide con el panel detectado. Si no hay coincidencia por ID, toma las cuatro vigas mas cercanas del mismo nivel.
- Regla explícita: reparte `P_user` proporcional al área tributaria `area_m2` que ese panel entrega a cada viga; si falta área, usa distancia inversa con `d_min=0.25 m`.
- Conservación: el panel muestra `Σ asignada`, `P_user` y `Error conserv. = |ΣP_i - P_user|`.
- Visualización: resalta en amarillo el panel activo y las vigas receptoras; agrega martillo/carga móvil rosado, líneas de transferencia, flechas proporcionales a `P_i` y etiquetas `P=... kN`.
- Interacción: el martillo se arrastra dentro de la losa; durante el arrastre se bloquea la cámara para evitar conflicto entre navegación y carga móvil. Los paneles IMGUI también bloquean selección/hover del modelo de fondo.
- Limpieza visual: losas delgadas y translúcidas con borde, flechas en el tope de las vigas receptoras y etiquetas compactas para mejorar lectura en Play Mode.
- Alcance: prototipo didáctico de camino de carga y reparto tributario. No recalcula OpenSees, no altera rigidez ni casos base, y no se presenta como envolvente normativa exacta.

Para obtener respuesta estructural exacta por carga móvil localizada se requiere reanálisis o casos de influencia precomputados. La conservación del prototipo se verifica visualmente por la suma `Σ asignada = P_user` en el panel SQ4.

---

## 5. UX estructural

Evaluación de si el viewer responde realmente las seis preguntas de diseño estructural:

| Pregunta | Respuesta del viewer | Cómo se demuestra |
|---|---|---|
| ¿Dónde está el elemento? | Sí — selección resaltada con tag/tipo/sección, coordenadas y piso; buscador por tipo+ID | Click en viga 147 o **Visualización → Buscar elemento → Viga 147**: auto-encuadre, resaltado amarillo y restauración con Limpiar |
| ¿Cómo está apoyado? | Sí — 64 apoyos visibles + pestaña Reacciones; tipo de apoyo por nodo | Apoyo nodo 1 muestra condición; en Mod B aparece articulado y con reacciones de momento nulas; checkbox Reacciones 3D |
| ¿Qué lo carga? | Sí — tributarias por nodo y cargas distribuidas por elemento | Viga 147 COMBO q = 19.124 kN/m (beamUniform); pestaña Tributarias: Σ carga = q×A |
| ¿Cómo se deforma? | Sí — vista Deformada del modo análisis con desplazamientos en m | Selector "Deformada" (HTML) y tecla D en Unity (`AnalysisMode.cs`); factor de escala ×10–600 |
| ¿Qué fuerzas tiene? | Sí — diagramas M/V/N por caso + fuerzas de extremo | Pestaña Diagramas (M/V/N, cierre 0.00 %), tabla de esfuerzos por elemento |
| ¿Cuánta capacidad tiene? | Sí — curvas P-M y Momento-Curvatura por sección | Pestañas P-M y Mom-Curv (70×70, 30×356, muros, steel); doble clic → punto de demanda vs curva (radio 0.894) |

Conclusión: el viewer contesta las **seis preguntas** con datos reales de OpenSees. Fortalezas: navegación explícita **VISUALIZACION / MODIFICACIONES / ANALISIS / DATOS**, trazabilidad por doble clic (N/V/M/DEF/tributarias/curvas), buscador de elemento por tipo+ID, convenciones de ingeniería consistentes y colormap por percentil 90. Limitaciones conocidas: la superposición interactiva se incorporó en **Unity** (§3.3) pero **HTML** mantiene λ fijos por sub-ficha; `Rebuild()` recrea palitos al cambiar caso/vista (costoso en gama media), HUD IMGUI no escalado a densidad alta y sin tooltips contextuales.

---

## 6. Preparación móvil

> Situación: se implementó la preparación móvil inicial. Se identificó una **familia de dispositivos compatibles**, se seleccionó un teléfono candidato, se habilitó el **Device Simulator** de Unity para validar la UI sin hardware y se dejó configurado el flujo de build móvil inicial. El APK final queda condicionado a instalar el módulo Android Build Support en Unity Hub.

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

- Script de build: `Unity/Assets/Editor/BuildMobile.cs` → `BuildMobile.BuildAndroid` (genera `Unity/Builds/BuildLabAndroid.apk`). Config inicial preparada: paquete `com.grupo6.p1`, scripting backend **IL2CPP**, platform target ARM64.
- Escena: `Assets/Scenes/SampleScene.unity` (definida en EditorBuildSettings).
- **Estado:** build móvil inicial configurado; pendiente emitir el APK final porque el módulo "Android Build Support" no está instalado en la máquina. Una vez instalado desde Unity Hub (~1-2 GB), se produce con:

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
| Motor C# de superposición en vivo | `Unity/Assets/Scripts/AnalysisMapCombination.cs` (motor) + `AnalysisMode.cs` (UI slider) + `MiniJson.cs`/`AnalysisMap.cs` (parser parcial existente) | Harness `tests/test_viewer_combination.ps1` sobre los **dos** mapas (línea base y Mod A): 147 945 comprobaciones por mapa, 7 combinaciones, casos base inmutables y rechazo atómico (§3.3) |
| Interfaz Unity de modificaciones | `Unity/Assets/Scripts/ModificationMode.cs`, `ViewerHud.cs`, `EdificioLoader.cs` | Desde Play Mode: Base/Mod A/Mod B ejecutan scripts Python/OpenSees, muestran log, guardan historial persistente y recargan escena |
| Buscador visual de elementos | `Unity/Assets/Scripts/ElementSearchPanel.cs`, `CameraController.cs`, `ElementInfoStyle.cs` | Búsqueda por tipo+ID en Visualización; auto-encuadre, resaltado amarillo, bloqueo de interacción de fondo y restauración con Limpiar |

**Regla aplicada:** ningún producto del agente se integra sin su verificación numérica o test. Convención del proyecto (AGENTS.md): umbrales 1e-10 para equilibrio, tributarias y superposición; donde se cumple 1e-6 pero no 1e-10 (desplazamiento 6.78e-9), el hecho queda documentado sin ocultarse. `python -m pytest tests -q` → **35 tests en verde** (6 módulos), re-ejecutada en el cierre del 24-09 con el mismo resultado.

---

## 8. Pendientes para el cierre (viernes 25)

> **P1 — Sliders de superposición:** implementados en Unity con un motor C# que suma los cuatro casos exportados. Prueba numérica, compilación y validación visual en Play Mode aprobadas. HTML mantiene su funcionamiento anterior.
>
> **P2 — Demanda/capacidad dinámica:** conectada al COMBO en memoria. La ficha sigue el caso activo; validación visual en Play Mode aprobada para el flujo de escritorio.
>
> **P3 — Preparación móvil:** familia compatible, teléfono candidato, Device Simulator, navegación táctil y build móvil inicial configurados. Pendiente emitir APK final al instalar Android Build Support y ensayar en teléfono físico.
>
> **P4 — SQ4 carga móvil:** prototipo implementado y validado visualmente en Unity para panel/región, vigas receptoras, martillo arrastrable y reparto de carga. Pendiente solo si se desea una respuesta estructural exacta M/V/deformada: incorporar casos de influencia o reanalizar.
>
> **P5 — Ensayo final:** probar guion completo en el equipo de presentación y, cuando exista APK, en el dispositivo Android final. Advertencia observada en Editor: `Ran out of Graphics Ring Buffer space`; no bloquea funcionalidad confirmada, pero conviene monitorearla en hardware final.

## 9. Verificación ejecutada en el cierre (24-09)

Comandos y resultados **reales** de esta sesión (no se inventaron comprobaciones visuales):

| Comando | Resultado |
|---|---|
| `./tests/test_viewer_combination.ps1` (StreamingAssets = modelo activo) | **PASS**: 147 945 comprobaciones C# |
| `./tests/test_viewer_combination.ps1 -Map resultados/11_mapa_visor/analysis_map.json` (línea base) | **PASS**: 147 945 comprobaciones C# |
| `python -m pytest tests -q` | **35 passed** (6 módulos) en 0.97 s |
| `python -c "import openseespy"` | OpenSeesPy **3.8.0.0** disponible (numpy 2.5.2) |

Limitaciones registradas:

- La validación visual en Play Mode del flujo de escritorio queda aprobada. La prueba del motor valida la suma de componentes exportadas; el render se confirmó manualmente en Unity.
- El reanálisis OpenSees de los cuatro casos base **no** se re-ejecutó en esta sesión; las corridas previas permanecen en `resultados/01_casos_base/` (G/Q/EX/EY, COMBO, comboC1..C3, modA, modB) y se citan como evidencia de las semanas anteriores.
- La sesión previa reportó no poder ejecutar la suite Python por dependencias locales incompletas y un fallo de permisos al repararlas. En el cierre el entorno ya las tiene (numpy, OpenSeesPy) y la suite corre completa: la limitación quedó superada y se registra así, sin reclamar un resultado que no se hubiera obtenido.
- Decisiones de integración: `Unity/.vsconfig` se incluye (configuración de Visual Studio con el workload ManagedGame para el proyecto Unity). Los cuatro assets de Unity sin cambio real de contenido (`EditorBuildSettings.asset`, `ShaderGraphSettings.asset`, `ProjectAuditorSettings.asset`, `UniversalRenderPipelineGlobalSettings.asset`) no se suben como modificación: sus blobs son byte-idénticos a `main` y su estado `M` es artefacto de stat/CRLF.

## Checklist de cierre

- [x] `reports/semana05.md` con la estructura de la entrega (7 secciones).
- [x] Tabla de funciones implementadas (§1).
- [x] Dos modificaciones completas con flujo reproducible (§2).
- [x] Superposición: tres estados verificados contra numéricos (§3) + demanda-capacidad (§3.2).
- [x] Sidequest carga móvil implementada como prototipo Unity (§4), validada visualmente en Play Mode.
- [x] UX estructural evaluada — seis preguntas confirmadas (§5).
- [x] Preparación móvil: familia de dispositivos + teléfono candidato + Device Simulator + navegación táctil (1/2 dedos, tap/doble-tap) + build móvil inicial configurado (§6); **APK final pendiente de módulo Android (P3)**.
- [x] IA documentada y verificada (§7).
- [ ] Commit + push final del avance actualizado (rama `main`).
- [x] `StreamingAssets` restaurable desde Unity o terminal; la pestaña **Modificaciones** permite alternar Base/Mod A/Mod B sin recompilar.
- [x] Validación visual en Play Mode del flujo de escritorio.
- [ ] Ensayo del guion en dispositivo Android final cuando exista APK.
