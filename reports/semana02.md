# Informe de Avance — Semana 2

| Campo | Valor |
|---|---|
| **Proyecto** | P1 — Laboratorio Estructural Digital (Edificio de Ingeniería) |
| **Curso** | Métodos Computacionales (8vo semestre) |
| **Grupo** | 6 |
| **Período** | 31 ago – 4 sep de 2026 |
| **Entregable** | Modelo global v1 + transferencia de cargas por áreas tributarias |
| **Repositorio** | `https://github.com/vaurmeneta-22/P1-Grupo-6` (rama `main`) |

---

## 1. Trazabilidad desde planos

El modelo global se construye desde el contrato `Edificio.json`, que conserva la
trazabilidad completa `plano → nodo → elemento → sectionTag → elementTag`.
Cada elemento del contrato referencia sus nodos extremos (`node_i`, `node_j`)
y su sección (`section`), y cada nodo guarda sus coordenadas y su piso.

**Ejemplo 1 — Columna (`elementTag = 1`, `section = "70x70"`):**

```
[Edificio.json] "elements"[0]
  id        : 1
  type      : column
  section   : 70x70        → sectionTag "70x70" (b=70cm, h=70cm)
  node_i    : 1            → x=0,    y=0,    z=0     (Subterraneo, base)
  node_j    : 7            → x=0,    y=0,    z=356   (Piso 1, cabeza)
```

En `opensees_edificio_v2.py` el elemento se convierte en `elasticBeamColumn(1, 1, 7, …)`
con la sección rectangular 0.70×0.70 m (`sec_rect` → A=0.49 m², Iy=Iz=0.0200 m⁴, J=0.0714 m⁴).

**Ejemplo 2 — Viga X (`elementTag = 7`, `section = "60x80"`):**

```
id        : 7
type      : beam_x
section   : 60x80         → sectionTag "60x80" (b=60cm, h=80cm)
node_i    : 7             → x=0,     y=0,    z=356 (Piso 1)
node_j    : 10            → x=-1000, y=0,    z=356 (Piso 1)
```

**Ejemplo 3 — Muro equivalente (`elementTag = 295`):**

```
id        : 295
type      : wall
section   : 60x291.5      → b=60cm (espesor), h=291.5cm (largo en planta)
xi,yi,zi  : (3195, 0,   36.75)
xj,yj,zj  : (3195, 356, 36.75)   → muro vertical de z=0 a z=356 cm
```

Los muros no existen como nodos en el contrato; `opensees_edificio_v2.py` crea
nodos en sus extremos (tags ≥ 9000) reutilizando la convención `(x,y,z)` con
`z = altura`.

---

## 2. Estadísticas del modelo

| Ítem | Cantidad |
|---|---|
| Nodos (contrato) | 536 |
| Nodos totales modelados (contrato + muros) | 653 |
| Columnas | 118 |
| Vigas X (`beam_x`) | 141 |
| Vigas Y (`beam_y`) | 165 |
| Muros equivalentes (`wall`) | 79 |
| Losas (`loza`, NO modeladas como FE) | 199 |
| **Elementos totales** | **702** |
| Apoyos fijos | 64 |
| Diafragmas rígidos | 5 (uno por piso) |
| Pisos | 5 (Subterráneo, Piso 1–4) |

Elementos estructurales efectivamente creados en el análisis
(código `n_created`): 503 (columnas + vigas + muros; las 199 losas se omiten).

---

## 3. Carga superficial

Valores definidos en `data/materials.json` y `opensees_edificio_v2.py`:

| Parámetro | Valor |
|---|---|
| Peso específico concreto (γ) | 2400 kg/m³ = 23.544 kN/m³ |
| Módulo E (f'c = 25 MPa) | 25 000 MPa = 25 GPa |
| Espesor de losa (t) | 15 cm (loza15); contratado por loza en `t` (cm) |
| Terminaciones (`TERMINACIONES_KNM2`) | 2.0 kN/m² |
| Sobrecarga de uso (`SOBRECARGA_KNM2`) | 2.0 kN/m² |

**Carga superficial de losa (caso G):**

```
q_G = γ · t + terminaciones
    = 23.544 · 0.15 + 2.0
    = 3.5316 + 2.0
    = 5.5316 kN/m²
```

**Sobrecarga (caso Q):** `q_Q = 2.0 kN/m²` (solo sobrecarga, sin peso propio).

---

## 4. Áreas tributarias — método de 45°

Las losas se transfieren a las vigas de borde por áreas tributarias a 45°
(`opensees/areas_tributarias.py`), como carga lineal `p = w · A_trib / L_viga`.

A continuación tres vigas con su polígono tributario, área, longitud, carga
superficial, carga total y distribución aplicada (datos de
`edificio_full_results.json → tributary_by_viga`):

### Viga 8 — `beam_x` sección 60x80 (Piso 1)

| Parámetro | Valor |
|---|---|
| Polígono tributario | 2 triángulos a 45° sobre el vano largo en X |
| Área tributaria | 25.881 m² |
| Longitud | 10.0 m |
| Carga superficial (G) | q_G = 5.5316 kN/m² |
| Carga total (G) | W = q_G · A = 143.16 kN |
| **Distribución aplicada** | uniforme `p_G = 14.32 kN/m` (`beamUniform`) |
| Carga total (Q) | W_Q = 51.76 kN → `p_Q = 5.18 kN/m` |

### Viga 10 — `beam_y` sección 60x80 (Piso 1)

| Parámetro | Valor |
|---|---|
| Polígono tributario | 2 trapecios a 45° sobre el vano corto en Y |
| Área tributaria | 15.958 m² |
| Longitud | 7.25 m |
| Carga superficial (G) | q_G = 5.5316 kN/m² |
| Carga total (G) | W = 88.27 kN |
| **Distribución aplicada** | uniforme `p_G = 12.18 kN/m` |
| Carga total (Q) | W_Q = 31.92 kN → `p_Q = 4.40 kN/m` |

### Viga 12 — `beam_y` sección 60x80 (Piso 1)

| Parámetro | Valor |
|---|---|
| Polígono tributario | 2 trapecios (vano largo) |
| Área tributaria | 35.657 m² |
| Longitud | 8.90 m |
| Carga superficial (G) | q_G = 5.5316 kN/m² |
| Carga total (G) | W = 197.24 kN |
| **Distribución aplicada** | uniforme `p_G = 22.16 kN/m` |
| Carga total (Q) | W_Q = 71.31 kN → `p_Q = 8.01 kN/m` |

---

## 5. Conservación de carga

Se comprueba que la suma de cargas transferidas a las vigas es exactamente la
carga de los pisos, y que la suma de áreas tributarias es exactamente el área
de las losas. Tolerancia adoptada: `< 1e-10`.

| Verificación | Valor | ¿OK? |
|---|---|---|
| Σ áreas tributarias | 5674.7015 m² | — |
| Σ áreas de losas | 5674.7015 m² | — |
| Error relativo de áreas | 0.0 | ✓ |
| Error relativo de conservación (`ΣW_vigas = q_G·A_piso`) | 0.0 | ✓ |
| Error de equilibrio global (ΣFz = ΣRz) | 0.0 | ✓ |

Verificaciones exportadas en `edificio_full_results.json` (campo `verifications`)
y en `tests/test_equilibrium.py` (4 tests: equilibrio, conservación, suma de
áreas y compatibilidad de diafragma).

---

## 6. Apoyos y restricciones

Se usan tres tipos de restricción en el modelo global (`opensees_edificio_v2.py`):

| Tipo | DOF restringidos | Uso | Justificación |
|---|---|---|---|
| **Empotramiento (fijo)** | ux, uy, uz, rx, ry, rz | 64 apoyos de fundación del contrato + nodos base de muro | Conexión rígida a fundación |
| **Soporte vertical de piso** | uz, rx, ry | Nodos de losa/reticula en z>356 sin columna ni muro bajo (p.ej. 43/76/109) | Representa el sostén vertical de la losa (no modelada como FE) |
| **Soporte vertical de componente flotante** | uz, rx, ry | Master (nodo más conectado) de cada componente conectado sin fundación | Evita nodos aislados / matriz singular |

Convención (AGENTS.md): un apoyo vertical mínimo `(0,0,1,1,1,0)` — restringir
solo `uz` deja un mecanismo de giro fuera del plano (matriz singular), por lo
que `rx, ry` son DOF estrictamente necesarios; generan par, no reacción lateral.

Gráfico: el viewer (Unity `EdificioLoader.cs` / web `edificio_3d.html`) dibuja
los apoyos de fundación como cubo + esfera morada en cada nodo de base.

---

## 7. Diafragmas

Se impone un **diafragma rígido por piso** (`ops.rigidDiaphragm(3, master, *slaves)`,
`opensees_edificio_v2.py` líneas 436-472), donde `dirn=3` restringe el plano ux–uy–rz.
El maestro es el nodo no-apoyo de mayor grado de conexión del piso; el resto de
nodos del piso son esclavos.

**Cinemática:** todos los nodos de un piso se mueven en planta como un disco
rígido respecto al maestro:

```
ux_i = ux_m − rz_m · (y_i − y_m)
uy_i = uy_m + rz_m · (x_i − x_m)
```

**Verificación numérica:** se compara el desplazamiento real de cada esclavo con
el predicho por la cinemática del disco rígido. Resultado:

```
Diafragma rígido: error máximo = 0.000e+00 m  →  OK (5 pisos con diafragma)
```

Implícito está en `edificio_full_results.json` (`diafragma_compatibilidad_err_max_m = 0.0`)
y en `tests/test_equilibrium.py::test_diaphragm_compatibility`.

---

## 8. Viewer Unity

El proyecto Unity (`Unity/Assets/Scripts/EdificioLoader.cs`) carga `Edificio.json`
en runtime y construye la escena:

| Capacidad | Detalle |
|---|---|
| **Capas** | `Elementos` (volúmenes por tipo), `Ejes` (palitos por elemento), `Nodos` (esferas + etiquetas). Teclas **N** (nodos) y **E** (ejes) alternan visibilidad |
| **Selección / IDs** | Cada nodo muestra su id como etiqueta (billboard); elementos con nombre `COLUMN_n`, `BEAM_X_n`, etc. |
| **Ejes** | `CreateAxisLine` → `LineRenderer` por elemento, color por tipo; helper de ejes X/Y/Z |
| **Apoyos** | `CreateWeldSupport` → esfera + cubo de fundación, material morado |
| **Áreas tributarias** | Datos por viga en `opensees/results/tributary_map.js` y `tributary_by_viga`; visualización de polígonos tributarios |
| **Losas / muros** | Cubos semitransparentes (losas) y por tramo (muros) |

La cámara orbital se controla con `CameraController.cs`. También hay un visor
web equivalente generado por `opensees/visualizar.py` (`edificio_3d.html`,
Three.js: rotar, zoom, N/E, dimensiones, apoyos).

---

## 9. Modificación del modelo

Se implementó la modificación sencilla **cambiar la sección de una viga** desde
los datos del contrato, siguiendo el flujo del visor:

1. En `edificio_3d.html` se edita la sección de la viga elegida (p.ej. `60x80` → `80x80`).
2. Se regenera el contrato con `scripts/html_to_json.py`, que vuelca los cambios
   del HTML a `Edificio.json` (con respaldo `.bak`):

```bash
python scripts/html_to_json.py
```

3. La nueva sección (b, h) se propaga automáticamente al análisis
   (`opensees_edificio_v2.py` recalcula A, Iy, Iz, J con `sec_rect`).

> No se exige reanalizar automáticamente desde Unity en esta entrega, solo que
> la modificación sea realizable desde datos/interfaz, respetando el contrato.

---

## 10. Uso de IA — corrección de un error generado por el agente

Durante la Semana 2 el agente propuso exportar los resultados guardando las
fuerzas internas directamente como **coordenadas locales**, asumiendo que
`ops.eleForce` las devuelve en el sistema local del elemento.

**Error detectado y corregido:** el script `opensees/test_eleforce.py` demostró
que `eleForce` devuelve las fuerzas en **coordenadas globales**. Con una columna
cargada con `Fx=50, Fz=-100` se verificó:

```
eleForce(1) = [50.00, 0.00, 100.00, 0, 0, 0]   → GLOBAL (Fz = +100, signo de reacción)
```

y se comprobó que la lectura **local** esperada sería `[100, 0, 50, …]` según la
transformación `vecxz=(1,0,0)`.

**Corrección aplicada:** en `opensees_edificio_v2.py` y `exportar_resultados_csv.py`
se guardan las fuerzas como `global_i` (coordenadas globales), y la transformación
a locales se deja como paso posterior explícito, en lugar de asumir que OpenSees
las entrega locales. Esto evitó un error sistemático de interpretación de P, V y M
en todos los elementos del edificio.

---

## Conclusión

El modelo global v1 del edificio completo está armado y verificado en OpenSeesPy:
- 536+ nodos, 503 elementos estructurales, 64 apoyos, 5 pisos y 5 diafragmas.
- Carga de losa transferida a vigas por áreas tributarias (método 45°) con
  **conservación exacta** (ΣW_vigas = q_G·A, error 0).
- Diafragma rígido compatible numéricamente (error 0).
- Viewer Unity y web funcionales con capas, IDs, ejes, apoyos y datos tributarios.
- Modificación de secciones desde datos/interfaz, y corrección de un error de
  coordenadas (global vs local) generado por el agente.

**Pendiente Semana 3:** casos sísmicos EX/EY + superposición `Σ λ·R`.
