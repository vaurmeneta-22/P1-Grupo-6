# Informe de Avance — Semana 4

| Campo | Valor |
|---|---|
| **Proyecto** | P1 — Laboratorio Estructural Digital (Edificio de Ingeniería) |
| **Curso** | Métodos Computacionales (8vo semestre) |
| **Grupo** | 6 |
| **Período** | 14 – 18 de septiembre de 2026 |
| **Entregable** | Diagramas 2D M/V/N integrados en el visor + auditoría de coherencia de esfuerzos de extremo; **traspaso completo del visor a Unity** (modo análisis, HUD, doble clic P-M/N-V-M-DEF y panel DATOS) |
| **Repositorio** | `https://github.com/vaurmeneta-22/P1-Grupo-6` (rama `main`) |

---

## 1. Objetivo de la semana

1. Exponer los esfuerzos del modelo completo como **diagramas clásicos 2D** (momento, corte y axial) para elementos representativos, integrados en la pestaña **Diagramas** del visor `edificio_3d.html`.
2. **Verificar la coherencia** de los diagramas contra las fuerzas de extremo que entrega OpenSees, porque la parábola de momento de la viga no cerraba visualmente en el apoyo de la derecha.
3. Migrar todo el visor HTML a Unity: modo análisis, HUD, inspección por doble clic y panel DATOS (completado esta semana).

---

## 2. Integración de los diagramas en el visor

| Pieza | Ubicación |
|---|---|
| Generador de datos y figuras | `scripts/diagramas_2d.py` → `exportar_datos()`, `plot_viga()`, `plot_vertical()` |
| Empaquetado en el mapa del análisis | `opensees/exportar_analysis_map.py` (agrega la clave `diagramas`) |
| Datos incrustados | `resultados/11_mapa_visor/analysis_map.js` → `ANALYSIS.diagramas = {COMBO, G, Q, EX, EY}` → `{viga, columna, muro}` |
| Pestaña del visor | `edificio_3d.html`: botón `data-tab="dt-diag"` (l.148), `<div id="dt-diag">` (l.155), despacho `renderDiag()` (l.3060), dibujo `drawDiagramPanels()` (l.3303); sub-fichas de caso COMBO/G/Q/EX/EY |

El visor muestra tres paneles apilados (N azul-verde, V ámbar, M cian) sobre un lienzo de 420×480, con eje de cero punteado, valores extremos anotados y una línea de resumen. Dentro de la pestaña se eligió con **sub-fichas de caso: COMBO | G | Q | EX | EY** (se mantiene el selector de elemento Viga/Columna/Muro). Los **mismos elementos** se usan en los 5 casos (fijos por el grupo: **viga 147, columna 261, muro 446**):

```
Viga 147 · 60x80 · L 8.90 m · q=19.124 kN/m (losa, beamUniform, COMBO)
· corte 0.0% · momentoj 0.0% | M +776.6 → -1092.7 · V -124.9 → -295.1 · N 0.0 kN
```

### Cierre de la viga 147 en los 5 casos (verificado al 0.00 %)

Cada caso usa su carga repartida real del FE: G → `p_G`, Q → `p_Q`, EX/EY → `0` (sin beamUniform), COMBO → `1.2·p_G + 1.0·p_Q`. La parábola cierra contra `−M_j`/`−V_j` en todos.

| Caso | q (kN/m) | M_i (kN·m) | M(L) = −M_j (kN·m) | V_i (kN) | V(L) = −V_j (kN) | cerr. corte/mom |
|---|---|---|---|---|---|---|
| COMBO | 19.124 | +776.6 | −1092.7 | −124.9 | −295.1 | 0.0 % / 0.0 % |
| G | 9.944 | −81.8 | −36.2 | +49.4 | −39.1 | 0.0 % / 0.0 % |
| Q | 7.191 | −49.8 | −37.4 | +33.4 | −30.6 | 0.0 % / 0.0 % |
| EX | 0.0 | +0.1 | +0.0 | ≈ 0 | (constante) | 0.0 % / 0.0 % |
| EY | 0.0 | +660.3 | −722.9 | −155.4 | (constante) | 0.0 % / 0.0 % |

Además se generan las figuras PNG en `resultados/10_figuras/` (un trío por caso: **15 PNG** con sufijo `(COMBO|G|Q|EX|EY)`):

| Figura (por caso) | Valores de la viga 147 (M_i → M(L)) |
|---|---|
| `Diagrama 2D Momento-Corte-Axial Viga 147 (60x80) (COMBO).png` | +776.6 → −1092.7 kN·m; q = 19.124 kN/m |
| `... (G).png` | −81.8 → −36.2 kN·m; q = 9.944 kN/m |
| `... (Q).png` | −49.8 → −37.4 kN·m; q = 7.191 kN/m |
| `... (EX).png` | +0.1 → +0.0 kN·m; q = 0 (lineal) |
| `... (EY).png` | +660.3 → −722.9 kN·m; q = 0 (lineal) |
| Columna 261 / Muro 446 | `Diagrama 2D Axial-Corte-Momento Columna 261 (70x70) (CASO).png`, `... Muro 446 (30x1000) (CASO).png` |

> Nota de caché: los datos se cargan con `analysis_map.js?v=<hash>`. Se actualizó el sufijo a `?v=02db6ad7f9`; si el visor ya estaba abierto, hay que forzar **Ctrl+F5**.

---

## 3. Auditoría de la convención de esfuerzos de extremo

### 3.1 Modelo mínimo en OpenSeesPy

Se aclaró que el proyecto **no usa el ejecutable `OpenSees.exe`** sino el módulo de Python **OpenSeesPy** (`import openseespy.opensees as ops`), ya instalado. Con dos modelos mínimos se determinó la convención de reporte de `ops.eleForce()`:

| Ensayo | Entrada | Resultado del FE | Lectura |
|---|---|---|---|
| Axial puro | Compresión `P = 10 kN` en el nodo libre | `N_i = +10.0`, `N_j = −10.0` | El extremo **j** se reporta en "cara opuesta" (acción sobre el elemento) |
| Flexión pura | Momento `+My = 50 kN·m` en el nodo libre | `Mz_i = −50.0`, `Mz_j = +50.0` | Igual: `Mz_j = −Mz_i` para un momento interno constante |

Conclusión: **el esfuerzo interno de sección en el extremo j es `−M_j` (y `−V_j`)**, no `+M_j`. La convención de la fórmula con la que se integra la parábola debe cerrar contra el extremo j cambiado de signo.

### 3.2 Causa raíz de que la parábola "no cerrara"

1. **Carga equivocada en la curvatura.** El peso propio se aplica en el modelo como **cargas nodales**, mientras que la losa tributaria es la única carga repartida (`beamUniform`, ver `opensees/opensees_edificio_v2.py:847`). Por lo tanto la curvatura de la parábola usa `q = 1.2·p_G + 1.0·p_Q` (solo losa), **sin** sumar `1.2·peso propio`.
2. **Signo del extremo j.** El cierre debe compararse contra `−M_j` (regla B), no contra `+M_j` (regla A).

### 3.3 Prueba estadística sobre las 108 vigas de vano completo

Se auditó cada viga con tributaria de tramo completo (`scripts/verificar_diagramas_viga.py`), contrastando el cierre de corte y de momento a menos de 3 %:

| Regla / carga de curvatura | Vigas que cierran M y V (< 3 %) |
|---|---|
| Regla A (misma convención) + `q` con peso propio | 0 / 108 |
| Regla A + `q` de losa | 2 / 108 |
| **Regla B (cara opuesta en j) + `q` de losa** | **48 / 108** |
| Regla B + `q` con peso propio | 39 / 108 |

### 3.4 Caso verificado en detalle: viga 147

`60×80`, `L = 8.90 m`, `q_losa = 19.124 kN/m`, COMBO:

```
M(x) = +776.6 − 124.9·x − 19.124·x²/2
V(x) = −124.9 − 19.124·x
```

- Extremo i (sección): `M_i = +776.6 kN·m`, `V_i = −124.9 kN`.
- Extremo j (sección = −reportado): `M(L) = −1092.74` vs `−M_j = −1092.74` → **0.00 %**; `V(L) = −295.14` vs `−V_j = −295.14` → **0.0 %**.
- El caso EX queda despreciable (q=0, M_i≈+0.1); en cambio EY domina la componente sísmica del COMBO (M 660 → −723) y es quien más contribuye a la asimetría.

Los elementos representativos ahora son **fijos del grupo** (constantes `VIGA_TAG=147`, `COL_TAG=261`, `MURO_TAG=446` en `diagramas_2d.py`), eliminando la selección automática; se mantiene el requisito de que la viga elegida cierre **corte y momento** a < 3 % (la 147 cierra al 0.00 %).

---

## 4. Traspaso completo del visor HTML a Unity (P2 — completado)

Se replicó en Unity la totalidad de la funcionalidad de `edificio_3d.html` usando la API real de `AnalysisMap` (que lee `StreamingAssets/analysis_map.json`, el mismo JSON que exporta `exportar_analysis_map.py`). Nada de la interacción nueva depende de assets serializados: `EdificioLoader.SetupPickHighlight()` y `SetupViewerHud()` crean los GameObjects en runtime.

| Módulo | Archivo | Qué replica |
|---|---|---|
| Datos | `AnalysisMap.cs` | Lee `analysis_map.json` (fuerzas, desplazamientos, reacciones, sismo, tributarias, momcurv, P-M, diagramas, capacidad, ejes locales) |
| Modo análisis | `AnalysisMode.cs` | Palitos de deformada y M/N/V con colormap por **percentil 90**; casos `1`–`5`; vistas `M/N/V/D`; escala `+/-` (10–600); reacciones 3D (`R`); panel de control a la izquierda; barra de colores abajo-derecha con `GUI.DrawTexture` sobre textura blanca + `GUI.color` (colores reales, no gris); **auto-encuadre** `FrameDeformada()` + `CameraController.FrameBounds()` |
| HUD | `ViewerHud.cs` | #modebar superior central (`Modo:` + `VISUALIZACION/ANALISIS` [TAB] + `DATOS`), #info arriba-izquierda (contadores de nodos/elementos) y #legend abajo-izquierda con swatches de color **14×14** (GUIStyle + textura blanca tintada) y **checkboxes de capas en 2 columnas** (`Todo`) |
| Inspección | `PickHighlight.cs` | Hover magenta (palito de 12 px, raycast con prioridad no-loza); **doble clic** → viga: reporte N/V/M/DEF (DEF en mm) + cargas tributarias; columna/muro de hormigón: **curva P-M** tipo diamante con punto de demanda, `Mcap` interpolado y % de capacidad (dentro/fuera de la curva) vía `DrawPMLab` |
| Panel DATOS | `DataPanel.cs` | Ventana derecha con **6 pestañas**: Sismo (12 columnas: piso, z, G, Q, W, masa, F_X/F_Y/\|F\|, ux/uy/Rz en mm/rad), Mom-Curv, **P-M fibra vs H.A.** superpuestas, Reacciones (checkbox *Pintar en 3D* ligado a `AnalysisMode.PintarReac`), Tributarias y **Diagramas apilados N/V/M** con selector de caso y de elemento |
| Gráficos 2D | `Plot2D.cs` | `Draw`, `DrawMulti`, `DrawDiag` y `DrawPMLab`; orientación vertical corregida (fila 0 abajo, valores positivos arriba, convención S en Diagramas) |
| Control de cámara | `CameraController.cs` | `FrameBounds(Bounds)` — encuadra la deformada completa respetando la rotación previa |

Apuntes técnicos de la replicación:

- **Índices paralelos:** los palitos del modo análisis usan un índice `Drew` paralelo a los elementos (los tubos van en los índices `[0..N-1]` antes de las esferas de reacción), por lo que `PalitoAt(i)` localiza el palito del elemento `i`.
- **Convenciones:** coordenadas estructurales `(x, altura, z) = (f[0], f[2], f[1])`; momentos `(f[3], f[5], f[4])`; demanda P-M = `|F·u|` y `|M − (M·u)u|` con `u` desde los ejes locales de `StructCoords`.
- **Búsqueda de capacidad por sección:** `id70 → columna_id70`, elementos de borde → `columna_borde`, muros → `muros[sección]`, `"70x70" → columna`, `"30x356" → muro`, acero → `steel[sección]`.
- **Acero:** el `Edificio.json` actual contiene **702** elementos (118 columnas + 141 vigas X + 165 vigas Y + 79 muros + 199 lozas) y aún no incluye los 20 metálicos del visor HTML (la leyenda del HUD ya tiene la fila *Refuerzo metálico*); cuando existan, el doble clic les mostrará el reporte N/V/M/DEF (sin P-M), como en el HTML.

La compilación se verificó en batch-mode con Unity 6000.5.10f1 (editor cerrado), con salida `Exiting batchmode successfully now!` y sin errores C#.

---

## 5. Cambios implementados

| Archivo | Cambio |
|---|---|
| `scripts/diagramas_2d.py` | `q` por caso (`_q_caso`: G→pG, Q→pQ, EX/EY→0, COMBO→1.2pG+pQ); cierre contra `−M_j`/`−V_j`; `resMJ`; **elementos fijos del grupo** `VIGA_TAG=147, COL_TAG=261, MURO_TAG=446` reusados en los 5 casos (se eliminó `_seleccion`); `exportar_datos()` → 5 casos × 3 elementos |
| `scripts/verificar_diagramas_viga.py` | **Nuevo.** Auditoría de las 108 vigas (hipótesis A vs B, `wlosa` vs `weq`, cierre de corte y momento) |
| `opensees/exportar_analysis_map.py` | Embebe `diagramas` y lo reporta en el resumen |
| `resultados/11_mapa_visor/analysis_map.js` | Regenerado con `diagramas` de los 5 casos (1.62 MB) |
| `edificio_3d.html` | Pestaña Diagramas con **sub-fichas de caso (COMBO/G/Q/EX/EY)** y selector de elemento; `renderDiag`/`drawDiagramPanels`; línea de info con `q` y residuos; cache-buster actualizado |
| `reports/semana03.md` | Sección 10.3 actualizada con la convención verificada y los valores corregidos |
| `Unity/Assets/Scripts/AnalysisMode.cs` | Palitos con índice paralelo a `Drew`, colormap percentil 90, reacciones 3D, panel de control a la izquierda, barra de colores abajo-derecha con colores reales y **auto-encuadre de la deformada** |
| `Unity/Assets/Scripts/ViewerHud.cs` | **Nuevo.** Modebar, HUD de información y leyenda de capas con swatches 14×14 + checkboxes (2 columnas, `Todo`) |
| `Unity/Assets/Scripts/PickHighlight.cs` | **Nuevo.** Hover magenta (12 px) y doble clic: reporte de viga N/V/M/DEF + tributarias, o curva P-M con demanda y `Mcap` interpolado |
| `Unity/Assets/Scripts/DataPanel.cs` | Ventana DATOS con 6 pestañas reales de `AnalysisMap` (Sismo 12 columnas, Mom-Curv, P-M fibra vs H.A., Reacciones con *Pintar en 3D*, Tributarias, Diagramas) |
| `Unity/Assets/Scripts/Plot2D.cs` | `DrawMulti`/`DrawDiag`/`DrawPMLab` con orientación vertical corregida (positivos arriba) |
| `Unity/Assets/Scripts/CameraController.cs` | `FrameBounds(Bounds)` para encuadrar la deformada respetando la rotación previa |
| `Unity/Assets/Scripts/EdificioLoader.cs`, `AnalysisMap.cs` | Setup de HUD/inspección en runtime y carga de `StreamingAssets/analysis_map.json` |
| `resultados/11_mapa_visor/analysis_map.json` | JSON plano adicional exportado por `exportar_analysis_map.py` para alimentar Unity |

También se corrigió un error de parseo de JavaScript (un paréntesis sin cerrar en la construcción del HTML de `renderDiag`) que rompía **todo** el script de análisis y era la causa de que la tecla **Tab no cambiara al modo ANÁLISIS**. El balance de los scripts del HTML quedó verificado (2/2 OK).

---

## 6. Pendientes (bloqueantes para el cierre)

> **P1 — Verificar los diagramas.** Ya con la convención y la carga corregidas (cierre al 0.00 % en los 5 casos) y con las sub-fichas G/Q/EX/EY + G+Q disponibles en el visor, **el usuario sigue viendo los diagramas "mal" en el navegador**. Hay que verificar en detalle:
> 1. Que la forma esperada sea la correcta: la viga 147 presenta **hogging en i (+776.6) y hogging mayor en j (−1092.7)** bajo COMBO; bajo G ambas mitades son hogging moderado (−81.8 → −36.2) y bajo EY el diagrama es lineal asimétrico (+660.3 → −722.9). Confirmar si el equipo espera ese patrón (o doble empotramiento simétrico con sagging interior), o si corresponde a la componente sísmica del COMBO.
> 2. Revisar si el problema es de **representación** (escalas, eje de cero, paneles demasiado pequeños, orden N/V/M, colores) y no de cálculo.
> 3. El aislamiento gravitacional/sísmico ya es posible directamente en el visor (sub-fichas); comparar G/Q/EX/EY vs COMBO para decidir qué patrón debe verse.
> 4. Confirmar el **signo físico del momento en el apoyo j** (si se dibuja con la convención de sección o con la acción nodal).
>    *Nota:* en la réplica de Unity los diagramas apilados ya se dibujan con la convención de sección corregida (positivos arriba), restando solo validar la misma representación en el navegador.
>
> **P2 — Implementar todo el visor HTML en Unity.** ✅ **Resuelto en esta semana** (sección 4): modo análisis, HUD, inspección por doble clic (P-M y N/V/M/DEF) y panel DATOS con las 6 pestañas, alimentados por `analysis_map.json` copiado a `StreamingAssets`.
>
> **P3 — Evitar pérdida del visor al regenerar.** `opensees/visualizar.py` escribe `edificio_3d.html` pero **no incluye** el tag `<script src=".../analysis_map.js">` ni la pestaña Diagramas; si se vuelve a ejecutar, se perdería la integración. Hay que incorporar esa línea al generador (o desacoplar el visor de `visualizar.py`).

---

## 7. Lecciones aprendidas

- **OpenSeesPy vs OpenSees.exe:** el proyecto usa el módulo de Python; basta `import openseespy.opensees`. La confusión inicial surgió de buscar sólo el ejecutable.
- **Peso propio nodal vs carga repartida:** la distinción es crítica para la curvatura de los diagramas. Sólo lo aplicado como `beamUniform` genera parábola; lo nodal sólo modifica las fuerzas de extremo.
- **Convención de extremo j:** `ops.eleForce()` entrega el extremo j como **acción sobre el elemento** (cara opuesta); un modelo mínimo lo revela en dos líneas. Ignorarlo hacía que ninguna de las 108 vigas cerrara.
- **La causa del "Tab no responde" no estaba en el manejo de teclado** sino en un paréntesis desbalanceado dentro de un `innerHTML` que impedía parsear todo el bloque `<script>`.
- **Replicar 1:1 el HTML en Unity pagó**: usar la API real de `AnalysisMap` (en vez de re-derivar datos en C#) evitó divergencias de convenciones entre navegador y Unity; los índices de palitos y de elementos se mantienen paralelos (tuberías antes de esferas de reacción).
- **El color gris en IMGUI era la textura por defecto de `GUI.DrawTexture`**: con una textura blanca 1×1 y `GUI.color` se obtienen los colores reales (swatches de la leyenda y barra de colores).
- **`Unity.exe -batchmode` solo compila con el editor cerrado**: si el proyecto está abierto en el Hub, la compilación aborta con un error de instancia en ejecución; se verifica cerrando Unity antes de compilar.

## Próximos pasos (Semana 5)

1. Cerrar **P1**: definir el patrón esperado del diagrama de momento, corregir la representación y validar en navegador viga a viga.
2. **P2 (Unity)**: validar el visor Unity en Play Mode (distribución del HUD, encuadre, rendimiento) y cerrar los aceros (regenerar el contrato con los 20 metálicos o alinear los conteos del README).
3. Resolver **P3** para que la pestaña Diagramas sobreviva a la regeneración del HTML.
