# Informe de Avance — Semana 4

| Campo | Valor |
|---|---|
| **Proyecto** | P1 — Laboratorio Estructural Digital (Edificio de Ingeniería) |
| **Curso** | Métodos Computacionales (8vo semestre) |
| **Grupo** | 6 |
| **Período** | 14 – 18 de septiembre de 2026 |
| **Entregable** | Diagramas 2D M/V/N integrados en el visor + auditoría de coherencia de esfuerzos de extremo; traspaso del visor a Unity |
| **Repositorio** | `https://github.com/vaurmeneta-22/P1-Grupo-6` (rama `main`) |

---

## 1. Objetivo de la semana

1. Exponer los esfuerzos del modelo completo como **diagramas clásicos 2D** (momento, corte y axial) para elementos representativos, integrados en la pestaña **Diagramas** del visor `edificio_3d.html`.
2. **Verificar la coherencia** de los diagramas contra las fuerzas de extremo que entrega OpenSees, porque la parábola de momento de la viga no cerraba visualmente en el apoyo de la derecha.
3. Dejar preparado el terreno para **migrar todo el visor HTML a Unity**.

---

## 2. Integración de los diagramas en el visor

| Pieza | Ubicación |
|---|---|
| Generador de datos y figuras | `scripts/diagramas_2d.py` → `exportar_datos()`, `plot_viga()`, `plot_vertical()` |
| Empaquetado en el mapa del análisis | `opensees/exportar_analysis_map.py` (agrega la clave `diagramas`) |
| Datos incrustados | `resultados/11_mapa_visor/analysis_map.js` → `ANALYSIS.diagramas = {COMBO, G, Q, EX, EY}` → `{viga, columna, muro}` |
| Pestaña del visor | `edificio_3d.html`: botón `data-tab="dt-diag"` (l.148), `<div id="dt-diag">` (l.155), despacho `renderDiag()` (l.3060), dibujo `drawDiagramPanels()` (l.3303); sub-fichas de caso COMBO/G/Q/EX/EY |

El visor muestra tres paneles apilados (N azul-verde, V ámbar, M cian) sobre un lienzo de 420×480, con eje de cero punteado, valores extremos anotados y una línea de resumen. Dentro de la pestaña se eligió con **sub-fichas de caso: COMBO | G | Q | EX | EY** (se mantiene el selector de elemento Viga/Columna/Muro). Los **mismos elementos** se usan en los 5 casos (viga 234, columna 1, muro 473, elegidos una sola vez con COMBO):

```
Viga 234 · 60x80 · L 7.49 m · q=15.89 kN/m (losa, beamUniform)
· corte 0.0% · momentoj 0.0% | M -218.6 → 168.4 · V 111.2 → -7.8 · N 0.0 kN
```

### Cierre de la viga 234 en los 5 casos (verificado al 0.00 %)

Cada caso usa su carga repartida real del FE: G → `p_G`, Q → `p_Q`, EX/EY → `0` (sin beamUniform), COMBO → `1.2·p_G + 1.0·p_Q`. La parábola cierra contra `−M_j`/`−V_j` en todos.

| Caso | q (kN/m) | M_i (kN·m) | M(L) = −M_j (kN·m) | V_i (kN) | V(L) = −V_j (kN) | cerr. corte/mom |
|---|---|---|---|---|---|---|
| COMBO | 15.887 | −218.62 | +168.36 | +111.16 | −7.83 | 0.0 % / 0.0 % |
| G | 8.261 | −59.46 | +80.51 | +49.62 | −12.25 | 0.0 % / 0.0 % |
| Q | 5.974 | −29.39 | +16.93 | +28.56 | −16.19 | 0.0 % / 0.0 % |
| EX | 0.0 | −87.82 | +49.10 | +18.28 | (constante) | 0.0 % / 0.0 % |
| EY | 0.0 | +3.62 | −9.95 | −1.81 | (constante) | 0.0 % / 0.0 % |

Además se generan las figuras PNG en `resultados/10_figuras/` (un trío por caso: **15 PNG** con sufijo `(COMBO|G|Q|EX|EY)`):

| Figura (por caso) | Valores de la viga 234 (M_i → M(L)) |
|---|---|
| `Diagrama 2D Momento-Corte-Axial Viga 234 (60x80) (COMBO).png` | −218.6 → +170.3 (interior, x=7.0 m) → +168.4 kN·m; q = 15.89 kN/m |
| `... (G).png` | −59.5 → +80.5 kN·m; q = 8.26 kN/m |
| `... (Q).png` | −29.4 → +16.9 kN·m; q = 5.97 kN/m |
| `... (EX).png` | −87.8 → +49.1 kN·m; q = 0 (lineal) |
| `... (EY).png` | +3.6 → −9.9 kN·m; q = 0 (lineal) |
| Columna 1 / Muro 473 | `Diagrama 2D Axial-Corte-Momento Columna 1 (70x70) (CASO).png`, `... Muro 473 (30x310) (CASO).png` |

> Nota de caché: los datos se cargan con `analysis_map.js?v=<hash>`. Se actualizó el sufijo a `?v=2aa256e282`; si el visor ya estaba abierto, hay que forzar **Ctrl+F5**.

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

### 3.4 Caso verificado en detalle: viga 234

`60×80`, `L = 7.49 m`, `q_losa = 15.887 kN/m`, COMBO:

```
M(x) = −218.62 + 111.16·x − 15.887·x²/2
V(x) = 111.16 − 15.887·x
```

- Extremo i (sección): `M_i = −218.62 kN·m`, `V_i = +111.16 kN`.
- Extremo j (sección = −reportado): `M(L) = +168.23` vs `−M_j = +168.36` → **0.08 %**; `V(L) = −7.83` vs `−V_j = +7.83` → **0.0 %**.
- Comprobación cruzada: integrar la parábola desde i y desde j da **el mismo momento en el centro** (+86.2 kN·m), lo que confirma que la curva es la sección interna consistente.
- Resultado del script: cierre de corte **0.0 %** y de momento j **0.0 %**.

La selección automática de la viga representativa ahora exige cerrar **corte y momento** simultáneamente (residuos < 3 %).

---

## 4. Cambios implementados

| Archivo | Cambio |
|---|---|
| `scripts/diagramas_2d.py` | `q` por caso (`_q_caso`: G→pG, Q→pQ, EX/EY→0, COMBO→1.2pG+pQ); cierre contra `−M_j`/`−V_j`; `resMJ`; selección de elementos hecha **una sola vez con COMBO** y reusada en los 5 casos; `exportar_datos()` → 5 casos × 3 elementos |
| `scripts/verificar_diagramas_viga.py` | **Nuevo.** Auditoría de las 108 vigas (hipótesis A vs B, `wlosa` vs `weq`, cierre de corte y momento) |
| `opensees/exportar_analysis_map.py` | Embebe `diagramas` y lo reporta en el resumen |
| `resultados/11_mapa_visor/analysis_map.js` | Regenerado con `diagramas` de los 5 casos (1.62 MB) |
| `edificio_3d.html` | Pestaña Diagramas con **sub-fichas de caso (COMBO/G/Q/EX/EY)** y selector de elemento; `renderDiag`/`drawDiagramPanels`; línea de info con `q` y residuos; cache-buster actualizado |
| `reports/semana03.md` | Sección 10.3 actualizada con la convención verificada y los valores corregidos |

También se corrigió un error de parseo de JavaScript (un paréntesis sin cerrar en la construcción del HTML de `renderDiag`) que rompía **todo** el script de análisis y era la causa de que la tecla **Tab no cambiara al modo ANÁLISIS**. El balance de los scripts del HTML quedó verificado (2/2 OK).

---

## 5. Pendientes (bloqueantes para el cierre)

> **P1 — Verificar los diagramas.** Ya con la convención y la carga corregidas (cierre al 0.00 % en los 5 casos) y con las sub-fichas G/Q/EX/EY + G+Q disponibles en el visor, **el usuario sigue viendo los diagramas "mal" en el navegador**. Hay que verificar en detalle:
> 1. Que la forma esperada sea la correcta: la viga 234 presenta **hogging en i y sagging en j** bajo COMBO (y bajo G: −59.5 → +80.5); confirmar si el equipo espera otro patrón (p. ej. doble empotramiento con hogging en ambos apoyos) o si corresponde a la componente sísmica del COMBO.
> 2. Revisar si el problema es de **representación** (escalas, eje de cero, paneles demasiado pequeños, orden N/V/M, colores) y no de cálculo.
> 3. El aislamiento gravitacional/sísmico ya es posible directamente en el visor (sub-fichas); comparar G/Q/EX/EY vs COMBO para decidir qué patrón debe verse.
> 4. Confirmar el **signo físico del momento en el apoyo j** (si se dibuja con la convención de sección o con la acción nodal).
>
> **P2 — Implementar todo el visor HTML en Unity.** Migrar a Unity la totalidad de la funcionalidad del visor `edificio_3d.html` (geometría, casos de carga, tubos N/V/M, mapa de análisis, reacciones, tributarias, **pestaña de diagramas 2D**, curvas P-M, etc.). Hoy el visor HTML es la fuente de verdad manual y no está reproducido por el generador.
>
> **P3 — Evitar pérdida del visor al regenerar.** `opensees/visualizar.py` escribe `edificio_3d.html` pero **no incluye** el tag `<script src=".../analysis_map.js">` ni la pestaña Diagramas; si se vuelve a ejecutar, se perdería la integración. Hay que incorporar esa línea al generador (o desacoplar el visor de `visualizar.py`).

---

## 6. Lecciones aprendidas

- **OpenSeesPy vs OpenSees.exe:** el proyecto usa el módulo de Python; basta `import openseespy.opensees`. La confusión inicial surgió de buscar sólo el ejecutable.
- **Peso propio nodal vs carga repartida:** la distinción es crítica para la curvatura de los diagramas. Sólo lo aplicado como `beamUniform` genera parábola; lo nodal sólo modifica las fuerzas de extremo.
- **Convención de extremo j:** `ops.eleForce()` entrega el extremo j como **acción sobre el elemento** (cara opuesta); un modelo mínimo lo revela en dos líneas. Ignorarlo hacía que ninguna de las 108 vigas cerrara.
- **La causa del "Tab no responde" no estaba en el manejo de teclado** sino en un paréntesis desbalanceado dentro de un `innerHTML` que impedía parsear todo el bloque `<script>`.

## Próximos pasos (Semana 5)

1. Cerrar **P1**: definir el patrón esperado del diagrama de momento, corregir la representación y validar en navegador viga a viga.
2. Iniciar **P2**: plan de migración del visor HTML a Unity (inventario de módulos, datos de entrada `analysis_map.js`/`Edificio.json`, y reutilización del `CameraController.cs` existente).
3. Resolver **P3** para que la pestaña Diagramas sobreviva a la regeneración del HTML.
