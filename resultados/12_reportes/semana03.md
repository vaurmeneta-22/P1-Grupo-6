# Informe de Avance — Semana 3

| Campo | Valor |
|---|---|
| **Proyecto** | P1 — Laboratorio Estructural Digital (Edificio de Ingeniería) |
| **Curso** | Métodos Computacionales (8vo semestre) |
| **Grupo** | 6 |
| **Período** | 7 – 11 de septiembre de 2026 |
| **Entregable** | Casos base, sismo pseudoestático, superposición, curvas M-φ y P-M, verificación RC, demanda-capacidad |
| **Repositorio** | `https://github.com/vaurmeneta-22/P1-Grupo-6` (rama `main`) |

---

## 1. Casos de carga base

El modelo del edificio completo (536 nodos, 702 elementos, 64 apoyos, 5 diafragmas rígidos) se resuelve con los siguientes casos de carga:

| Caso | Descripción | Carga superficial | Carga total |
|---|---|---|---|
| **G** | Gravedad (peso propio de losa + terminaciones + peso propio estructural) | q_G = 5.5316 kN/m² | **73 488.03 kN** |
| **Q** | Sobrecarga de uso (solo sobrecarga, sin peso propio) | q_Q = 4.0 kN/m² | **22 697.57 kN** |
| **EX** | Sismo pseudoestático en dirección X | — | **F = 16 650.79 kN** |
| **EY** | Sismo pseudoestático en dirección Y | — | **F = 16 650.79 kN** |

**Carga superficial de losa (caso G):**

```
q_G = γ · t + terminaciones
    = 23.544 · 0.15 + 2.0
    = 3.5316 + 2.0
    = 5.5316 kN/m²
```

**Carga superficial de sobrecarga (caso Q):**

```
q_Q = 4.0 kN/m²
```

Cada caso se resuelve de forma independiente (`python opensees_edificio_v2.py --case G`). Los resultados se exportan a `resultados/01_casos_base/edificio_full_results[_Q,_EX,_EY].json`.

### Verificación de cada caso base

| Verificación | G | Q | EX | EY |
|---|---|---|---|---|
| Equilibrio global (ΣF + ΣR = 0) | error = 0.0 | error = 0.0 | error = 0.0 | error = 0.0 |
| Conservación de carga (ΣW_vigas = q·A) | error = 0.0 | error = 0.0 | — | — |
| Conservación de áreas tributarias | error = 0.0 | — | — | — |
| Compatibilidad de diafragma | err_max = 0.0 m | — | err_max = 0.0 m | err_max = 0.0 m |
| Corte basal: F_aplicada vs α·W_efectivo | — | — | error = 0.0 | error = 0.0 |

---

## 2. Carga viva Q

La carga viva reutiliza la **misma geometría de áreas tributarias** calculada en la Semana 2 (método de 45°, `opensees/areas_tributarias.py`). La única diferencia es la intensidad: `q_Q = 4.0 kN/m²` (sobrecarga de uso) en lugar de `q_G = 5.5316 kN/m²`.

| Parámetro | G | Q |
|---|---|---|
| Carga superficial de losa | q_G = 5.5316 kN/m² | q_Q = 4.0 kN/m² |
| Suma de áreas tributarias | 5674.39 m² | 5674.39 m² |
| Suma de cargas transferidas a vigas | 31 274.39 kN | 22 697.57 kN |
| Error de conservación | 0.0 | 0.0 |

La conservación se verifica con la identidad `Σ(W_vigas) = q · Σ(A_trib)`, que se cumple con exactitud numérica (tolerancia < 1e-10). Las mismas áreas tributarias (polígonos a 45° sobre vigas de borde) se usan para ambos casos, garantizando consistencia geométrica.

---

## 3. Sismo pseudoestático

### 3.1 Masa sísmica

La masa sísmica se calcula como `W_sismico = G + 0.50·Q` (fracción de sobrecarga considerada: 50%). El parámetro de aceleración es `α = 0.20`.

| Piso | G_floor (kN) | Q_floor (kN) | W_sismico (kN) | Masa (kg) | F = α·W (kN) |
|---|---|---|---|---|---|
| Piso 1 | 9 711.90 | 2 503.59 | 10 963.70 | 1 117 604 | 2 192.74 |
| Piso 2 | 14 921.67 | 4 565.03 | 17 204.18 | 1 753 739 | 3 440.84 |
| Piso 3 | 15 325.41 | 4 986.43 | 17 818.63 | 1 816 374 | 3 563.73 |
| Piso 4 | 16 584.42 | 5 274.04 | 19 221.44 | 1 959 372 | 3 844.29 |
| Techo | 15 361.78 | 5 368.48 | 18 046.02 | 1 839 553 | 3 609.20 |
| **Σ** (efectivo) | **71 905.18** | **22 697.57** | **83 253.97** | **8 486 642** | **16 650.79** |

Nota: el peso del Subterráneo (G = 1 582.85 kN) se excluye de la masa sísmica porque no participa en carga lateral (no hay diafragma rígido en z=0).

**Masa sísmica total (W_sismico):** `G_total + 0.50·Q_total = 73 488.03 + 0.50 × 22 697.57 = 84 836.81 kN`.

### 3.2 Fuerzas por piso

Las fuerzas sísmicas se aplican en el **centro de masa** de cada piso (calculado independientemente del nodo master del diafragma). La fuerza se aplica en el master como carga equivalente con momento correctivo: `F_master = F; Mz = (x_CM − x_master)·Fy − (y_CM − y_master)·Fx`.

| Piso | Fx (caso EX) | Fy (caso EY) | CM_x (m) | CM_y (m) |
|---|---|---|---|---|
| Piso 1 | 2 192.74 | 2 192.74 | — | — |
| Piso 2 | 3 440.84 | 3 440.84 | — | — |
| Piso 3 | 3 563.73 | 3 563.73 | — | — |
| Piso 4 | 3 844.29 | 3 844.29 | — | — |
| Techo | 3 609.20 | 3 609.20 | — | — |

El centro de masa varía entre pisos porque la distribución de elementos estructurales y losas no es uniforme. La posición del CM se pondera con `W_estructura + 0.50·Q_losa` por nodo y por losa.

### 3.3 Corte basal

```
V_total = Σ F_floor = 16 650.79 kN
W_efectivo (sin fundación) = 83 253.97 kN
V / W_efectivo = 0.200 = α   ✓
```

Se verifica independientemente: la fuerza calculada desde `G_floor` y `Q_floor` coincide exactamente con la fuerza aplicada por el script (error < 1e-10).

### 3.4 Desplazamientos

Los desplazamientos de CM por piso se exportan junto con el resto en `resultados/05_sismo/sismo_por_piso.csv`:

| Piso | ux (EX, mm) | uy (EY, mm) |
|---|---|---|
| Piso 1 | 0.71 | 4.78 |
| Piso 2 | 2.34 | 10.18 |
| Piso 3 | 4.28 | 17.87 |
| Piso 4 | 6.06 | 23.67 |
| Techo | **7.54** | **26.91** |

- **EX:** desplazamiento máximo en el techo = **7.5 mm** en X.
- **EY:** desplazamiento máximo en el techo = **26.9 mm** en Y (sistema más flexible en Y).

### 3.5 Rotación de diafragmas

Las rotaciones `Rz` son del orden de 10⁻⁵ rad en EX y hasta 8.8e-5 rad en EY (Piso 2), lo que confirma que el diafragma rígido trabaja como disco rígido en planta. La mayor rotación ocurre en el Piso 2 bajo EY (8.8e-5 rad), consistente con la asimetría de la planta. Todo ello se exporta en `resultados/05_sismo/sismo_por_piso.csv`.

---

## 4. Superposición

La superposición lineal se implementa en `opensees/superposicion.py`. La combinación general es:

```
R = λ_G · R_G + λ_Q · R_Q + λ_EX · R_EX + λ_EY · R_EY
```

### 4.1 Combinaciones verificadas

Se verificaron al menos 3 combinaciones:

| # | λ_G | λ_Q | λ_EX | λ_EY | Descripción |
|---|---|---|---|---|---|
| 1 | 1.2 | 1.0 | 1.4 | 1.4 | Combinación de diseño (últimos estados límite) |
| 2 | 1.0 | 1.0 | 1.0 | 1.0 | Combinación de servicio completa |
| 3 | 1.0 | 0.0 | 1.0 | 0.0 | Solo sismo en X (verificación de simetría) |

### 4.2 Comparación: superposición directa vs corrida explícita

El script `superposicion.py` compara dos enfoques:

1. **Superposición directa** (sin OpenSees): lee los JSON de cada caso base y combina linealmente desplazamientos, reacciones y fuerzas internas.
2. **Corrida explícita** (OpenSees): resuelve el modelo con la combinación de cargas aplicada directamente en un solo paso.

**Resultado para λ_G = 1.2, λ_Q = 1.0, λ_EX = 1.4, λ_EY = 1.4:** (valores reales del `resultados/06_superposicion/verificacion.csv`)

| Cantidad | Error relativo (norma) | n_medidas | ¿OK? |
|---|---|---|---|
| Desplazamientos | 6.78e-09 | 516 nodos | ✓ |
| Reacciones | 2.28e-14 | 99 reacciones | ✓ |
| Fuerzas internas | 4.88e-12 | 701 elementos | ✓ |

**Conclusión:** la superposición lineal es exacta dentro de la tolerancia numérica (tol = 1e-6), confirmando que el modelo es elástico lineal y la implementación es correcta. El resultado se exporta automáticamente a `resultados/06_superposicion/verificacion.csv` al final de la corrida completa de `superposicion.py`.

### 4.3 Resultados del caso COMBO (λ_G=1.2, λ_Q=1.0, λ_EX=1.4, λ_EY=1.4)

| Campo | Valor |
|---|---|
| Carga total COMBO | **157 505.42 kN** |
| F_lateral X (λ_EX · ΣF_EX) | 23 311.11 kN |
| F_lateral Y (λ_EY · ΣF_EY) | 23 311.11 kN |
| Equilibrio global | error = 0.0 |
| Compatibilidad de diafragma | err_max = 0.0 m |
| Conservación de carga | error = 0.0 |

---

## 5. Momento-curvatura

### 5.1 Definición de la sección representativa

Se analiza la sección de la **columna 70×70 cm** (`COLUMNA` en `opensees/fiber_sections/sections.py`):

| Parámetro | Valor |
|---|---|
| Dimensión | b = 700 mm, h = 700 mm |
| Acero longitudinal | 16 φ28 (A_s = 9 852 mm²) |
| Recubrimiento | 64.0 mm (al centro de la barra) |
| Disposición | Perimetral: 5 arriba + 5 abajo + 3 por costado (sin repetir esquinas) |
| Concreto | f'c = 35 MPa, ε_cu = 0.0035 |
| Acero | fy = 420 MPa, E_s = 200 000 MPa |
| Modelo de material | Concrete02 (concreto) + Steel01 (acero) |
| Discretización | 24 × 8 fibras de concreto |

### 5.2 Carga axial

La curva M-φ se genera con **P = 0 kN** (flexión pura), que representa la condición más desfavorable para la columna en situaciones de servicio.

### 5.3 Curva M-φ

La curva se obtiene con un modelo de viga cantilever de un solo elemento (`dispBeamColumn`, 5 puntos de Lobatto), controlando la rotación en la punta. La curvatura se calcula como `φ = θ / L`, con `L = 100 mm`.

| Parámetro | Valor |
|---|---|
| Curvatura inicial | φ ≈ 6.0 × 10⁻⁶ 1/m |
| Curvatura en el pico (falla) | φ_pico = 0.0245 1/m |
| Momento último (pico) | **M_ult = 1232.70 kN·m** |
| Pasos convergidos | 4 795 |
| Criterio de término | ε_fibra_extrema ≤ −ε_cu = −0.0035 |

La curva muestra el comportamiento elástico lineal inicial, seguido de la plastificación del acero y finalmente la falla por compresión del concreto.

### 5.4 Rigidez inicial

La rigidez inicial se obtiene como la pendiente de la rama elástica:

```
EI = M / φ ≈ (M_elast) / (φ_elast)
```

Para la columna 70×70 con P=0 la sensibilidad numérica reporta `EI = 671 533 kN·m²` (rama elástica convergida, incluye el refuerzo).

### 5.5 Criterio de término

El análisis se detiene cuando la deformación de la fibra extrema comprimida alcanza `ε_cu = 0.0035` (falla por concreto, norma ACI/NCh). Este criterio se aplica tanto para M-φ como para P-M.

### 5.6 Sensibilidad de discretización

La convergencia de la discretización de fibras se audita con `scripts/sensibilidad_secciones.py` (`resultados/07_capacidad/sensibilidad/sensibilidad_secciones.json`), barriendo la malla de fibras para ambas secciones con P = 0:

| Sección | Escenarios (n_fib) | M_ult (kN·m) | ΔM máx rel. |
|---|---|---|--:|
| Columna 70×70 | 48 → 3072 | 1232.70 (invariante) | 0.0% |
| Muro 30×356 | 80 → 960 | 3400.85 → 3401.14 | 0.02% |

La columna converge desde 48 fibras (M_ult idéntico en los 4 escenarios); el muro varía ≤ 0.02% en momento último y ≤ 3% en curvatura de falla entre 80 y 960 fibras. La malla de trabajo (columna 24×8 = 192 fibras, muro 40×6 = 240) está por tanto dentro del rango convergido.

---

## 6. Curva P-M de columna

### 6.1 Generación de la envolvente

La envolvente P-M se genera barriendo una grilla de cargas axiales `P = [0, 500, 1500, 2500, 3500, 4500, 5000, 5500, 6000, 7000, 8000, 9000, 10000, 11000, 12000, 13000, 14000, 15000, 16000, 17000, 18000, 19000] kN`. Para cada valor de P se resuelve la curva M-φ completa y se toma el **momento máximo** (pico de la curva) como la capacidad a flexión para ese nivel de carga axial.

### 6.2 Explicación de puntos característicos

| P (kN) | M_cap (kN·m) | Descripción |
|---|---|---|
| 0 | 1 232.7 | Flexión pura (P=0) |
| 3 500 | 1 874.5 | Zona de compresión moderada |
| 6 000 | **2 071.5** | Momento máximo absoluto de la envolvente |
| 7 000 | 2 032.4 | Compresión alta (meseta de balance) |
| 10 000 | 1 886.6 | Compresión alta (acero cede en tracción) |
| 15 000 | 1 208.0 | Compresión muy alta |
| 19 000 | 432.8 | Compresión pura (P_0 analítico ≈ 18 422 kN) |

La envolvente tiene forma de "ojo": el momento máximo ocurre en la zona de balance (P ≈ 6 000 kN), donde el acero de tracción alcanza fy justo cuando el concreto llega a ε_cu. Para P > P_balance, el momento disminuye porque la sección está dominada por compresión. El refuerzo perimetral (16 φ28, configuración original del plano) aporta A_s = 98.5 cm² y desplaza la envolvente respecto a la simplificación anterior (18 φ25): el momento máximo sube de 1 817.6 a 2 071.5 kN·m.

### 6.3 Columna del pórtico extremo (reforzada: 4 φ28 + 16 φ36)

En el plano estructural, las **12 columnas 70×70 del pórtico extremo** (los 4 ejes × las 3 líneas del extremo X−, ids 66-113) tienen una enfierradura **distinta** a la del resto: **20 barras perimetrales mixtas** — 4 φ28 en las esquinas + 16 φ36 intermedias (etiquetadas B1/B2/B3 en el plano: 4 en la cara superior, 4 en la inferior, 4 por costado), con recubrimiento al centro de barra de 68 mm. A_s = 4×6.16 + 16×10.18 = **187.5 cm²** (ρ = 3.83 %). Se implementó como sección `columna_borde_70x70` en `sections.py` y se generó su envolvente P-M con la misma metodología (`pm_columna_borde_70x70.json/.png`):

| P (kN) | M_cap (kN·m) | Descripción |
|---|---|---|
| 0 | 2 127.3 | Flexión pura (P=0) |
| 6 000 | **2 699.0** | Momento máximo absoluto de la envolvente |
| 10 000 | 2 392.8 | Compresión alta |
| 15 000 | 1 689.3 | Compresión muy alta |
| 23 500 | 239.5 | Compresión pura (P_0 analítico ≈ 21 894 kN) |

La curva equivale a ~1.7× la capacidad de la columna base (flexión pura 2 127 vs 1 233 kN·m; pico 2 699 vs 2 072 kN·m). Esta sección se asigna en el mapa (`borde: true`) a los **48 elementos** que forman las 12 columnas reales del pórtico extremo (4 tramos apilados por cada columna).

---

## 7. Curva P-M de muro

### 7.1 Envolvente del muro 30×356

La envolvente se genera con la misma metodología: `P = [0, 2000, 5000, 8000, 11000, 14000, 17000, 20000, 23000, 26000, 29000, 32000, 35000] kN`.

| Parámetro | Valor |
|---|---|
| Sección | bw = 300 mm, Lw = 3560 mm |
| Elementos de borde | 2 × 400 mm con 4 φ16 cada uno |
| Malla central | φ10 @ 20 cm, doble capa |
| M_max | **16 682.2 kN·m** @ P = 17 000 kN |
| P_0 (compresión pura) | ~35 000 kN |
| M @ P=0 (flexión pura) | 3 400.8 kN·m |

### 7.2 Muros adicionales

Se generaron curvas P-M para las 14 secciones de muro restantes del contrato usando la regla proporcional (`muro_tipificado()` en `sections.py`). Las secciones son:

`60x291.5`, `60x292`, `25x795`, `25x585`, `30x2695`, `25x282`, `30x725`, `30x1000`, `30x890`, `30x615`, `25x158`, `25x365`, `30x225`, `30x310`.

La regla de escala usa las proporciones del muro 30×356 como referencia: borde = 11.2% del largo, filas de acero a 2.25% y 6.74%, malla central constante.

---

## 8. Verificación RC

### 8.1 Método independiente: bloque rectangular ACI/NCh

Se implementó una verificación independiente (`opensees/fiber_sections/verification_ha.py` + `scripts/comparacion_rc.py`, que la automatiza sobre los P-M reales de fibras) usando el **diagrama de compresión rectangular equivalente** del curso de Hormigón Armado:

- **α₁ = β₁ = 0.80** (para f'c = 35 MPa: `0.85 − 0.05 × (35−28)/7 = 0.80`)
- **ε_cu = 0.0035** (ruina controlada por concreto)
- **Compatibilidad de deformaciones:** `ε_s = ε_cu · (c − d_i) / c`
- **Equilibrio:** `P = C_c + ΣF_s`, `M = C_c·(h/2 − a/2) + ΣF_s·(h/2 − d_i)`
- Se barre c desde 0.05h (tracción pura) hasta h (compresión pura)

### 8.2 Comparación fiber vs bloque rectangular

La comparación automatizada (`scripts/comparacion_rc.py`, salida en `resultados/08_verificacion/verificacion_rc.json`):

| Sección | Punto | M_analítico (kN·m) | M_fiber (kN·m) | Diferencia |
|---|---|---|---|---|
| Columna 70×70 | Flexión pura | 1 214.4 | 1 232.7 | 1.5% |
| Columna 70×70 | Balanceado (P = 6 542 kN) | 2 018.8 | 2 050.3 | 1.6% |
| Columna pórtico extremo (4φ28+16φ36) | Flexión pura | 2 137.2 | 2 127.3 | -0.5% |
| Columna pórtico extremo | Balanceado (P = 6 843 kN) | 2 674.9 | 2 632.7 | -1.6% |
| Muro 30×356 | Flexión pura | 3 323.6 | 3 400.8 | 2.3% |
| Muro 30×356 | Balanceado (P = 14 930 kN) | 14 884.5 | 16 376.2 | 10.0% |

Las diferencias son esperables: el modelo de fibras captura la distribución de esfuerzos más refinada (Concrete02 con degradación, Steel01 con endurecimiento), mientras que el bloque rectangular asume distribución uniforme de esfuerzo en el concreto. La concordancia es buena en flexión pura y en el balanceado de las columnas (≤ 2.3% en la base, ≤ 1.6% en la del pórtico extremo), y se mantiene razonable en el balanceado del muro (10%).

---

## 9. Primera demanda-capacidad

### 9.1 Barrido automático

El script `scripts/demanda_capacidad.py` barre las **118 columnas de hormigón** del modelo con el caso COMBO (λ_G=1.2, λ_Q=1.0, λ_EX=1.4, λ_EY=1.4): para cada columna toma el P axial y el momento resultante del extremo con mayor demanda y los contrasta contra la curva P-M de **su** sección (`columna` 16 φ28 o `columna_borde` 4 φ28+16 φ36 según el flag `borde` del elemento; criterio `Pcap`/`Mcap` de `demanda_capacidad_critica.json`).

### 9.2 Columna crítica: id=70 (sección 70×70 del pórtico extremo)

| Campo | Valor |
|---|---|
| Elemento | Columna id=70, sección 70×70 (pórtico extremo, curva reforzada 4φ28+16φ36) |
| P_demanda | 1 145.8 kN |
| M_demanda | 2 383.2 kN·m |
| **Radio de utilización (M_d / M_cap)** | **1.031** |
| **Resultado** | **~3 % por encima de la curva** |

### 9.3 Columnas que no cumplen

Con la corrección del pórtico extremo (las 12 columnas 70×70 en x = -20/-30/-40/-45 pasan a su enfierradura real del plano: 4 φ28 + 16 φ36), el número de columnas **fuera de la curva pasa de 12 a 1** (solo la id=70, +3.1 %). Las 11 columnas críticas que antes fallaban (ids 66-77) bajan su radio máximo de 1.612 a 1.031:

| id | P (kN) | M (kN·m) | radio (base) | radio (borde) |
|---|---|---|---|---|
| 70 | 1 145.8 | 2 383.2 | 1.612 | **1.031** |
| 66 | 930.5 | 2 169.2 | 1.514 | **0.952** |
| 74 | 991.0 | 2 171.8 | 1.503 | **0.949** |
| 71 | 981.5 | 2 119.8 | 1.469 | **0.927** |
| 67 | 789.2 | 1 969.0 | 1.404 | **0.872** |
| 75 | 862.1 | 1 929.5 | 1.361 | **0.851** |
| 72 | 861.2 | 1 876.9 | 1.324 | **0.827** |
| 68 | 749.4 | 1 836.2 | 1.317 | **0.816** |
| 73 | 751.2 | 1 721.9 | 1.235 | **0.765** |
| 69 | 600.6 | 1 629.2 | 1.196 | **0.731** |
| 76 | 698.2 | 1 637.0 | 1.183 | **0.730** |
| 77 | 564.7 | 1 444.7 | 1.066 | **0.650** |

La pronta columna que permanece fuera (id=70) queda solo 3.1 % por encima con su enfierradura real del plano: su demanda (M_d = 2 383 kN·m) excede incluso el pico absoluto de la curva base (2 072 kN·m), y la nueva curva alcanza ~2 312 kN·m en ese nivel de carga axial — la corrección de enfierradura recupera 11 de las 12 columnas críticas y deja la restante al borde del criterio nominal (sin factores φ, ver sección 10). Las 106 columnas restantes (no pórtico extremo) se mantienen todas dentro: el radio máximo fuera del pórtico extremo es 0.933 (id=285).

---

## 10. Uso de IA

### 10.1 Convención de coordenadas para eleForce (Semana 2, corregida en Semana 3)

Durante la Semana 2, el agente propuso exportar las fuerzas internas directamente como coordenadas locales, asumiendo que `ops.eleForce` devuelve las fuerzas en el sistema local del elemento.

**Problema detectado:** el script `opensees/test_eleforce.py` demostró que `eleForce` devuelve las fuerzas en **coordenadas globales**. Con una columna cargada con `Fx=50, Fz=-100` se verificó que la lectura era global (Fz = +100, signo de reacción), no local como esperaba el agente.

**Revisión del grupo:** el equipo verificó el resultado con un cantiléver simple y confirmó que la convención de OpenSees es global. Se corrigió la exportación para guardar las fuerzas como `global_i` / `global_j`, y la transformación a locales se dejó como paso separado. Este error, de no haberse detectado, habría producido errores sistemáticos en P, V y M de todos los elementos del edificio.

### 10.2 Criterio de capacidad: momento pico vs momento de falla

El agente inicialmente propuso usar el **momento último** de la curva M-φ como capacidad nominal, definido como el último punto convergido antes de la pérdida de convergencia. Tras revisión con el grupo, se acordó usar el **pico de la curva** (máximo absoluto del momento), que es más conservador y consistente con la interpretación del curso de H.A.: la capacidad es el momento máximo que la sección puede resistir antes de perder resistencia.

---

## Entregables Semana 3

| Entregable | Archivo |
|---|---|
| Script principal | `opensees/opensees_edificio_v2.py` |
| Superposición | `opensees/superposicion.py` |
| Fiber sections | `opensees/fiber_sections/{sections,analysis,materials,verification_ha}.py` |
| Generador M-φ + P-M columna/muro | `scripts/parte_d_fiber.py` |
| P-M muros adicionales | `scripts/parte_d_muros.py` |
| Sensibilidad de fibras | `scripts/sensibilidad_secciones.py` |
| Verificación RC | `scripts/comparacion_rc.py` |
| Demanda-capacidad | `scripts/demanda_capacidad.py` |
| Resultados G | `resultados/01_casos_base/edificio_full_results.json` |
| Resultados Q | `resultados/01_casos_base/edificio_full_results_Q.json` |
| Resultados EX | `resultados/01_casos_base/edificio_full_results_EX.json` |
| Resultados EY | `resultados/01_casos_base/edificio_full_results_EY.json` |
| Resultados COMBO | `resultados/01_casos_base/edificio_full_results_COMBO.json` |
| Sismo por piso (CSV) | `resultados/05_sismo/sismo_por_piso.csv` |
| Verificación superposición (CSV) | `resultados/06_superposicion/verificacion.csv` |
| Curva M-φ columna | `resultados/07_capacidad/mom_curv/mom_curv_columna_70x70.json/.png` |
| P-M columna | `resultados/07_capacidad/pm_columnas/pm_columna_70x70.json/.png` |
| P-M columna pórtico extremo (4φ28+16φ36) | `resultados/07_capacidad/pm_columnas/pm_columna_borde_70x70.json/.png` |
| P-M muro 30×356 | `resultados/07_capacidad/pm_muros/pm_muro_30x356.json/.png` |
| P-M muros adicionales | `resultados/07_capacidad/pm_muros/pm_<seccion>.json/.png` (14 archivos) |
| Sensibilidad (JSON) | `resultados/07_capacidad/sensibilidad/sensibilidad_secciones.json` |
| Verificación RC (JSON) | `resultados/08_verificacion/verificacion_rc.json` |
| Demanda-capacidad (JSON/PNG) | `resultados/09_demanda_capacidad/` |
| Validación PM | `docs/validacion_pm/` |
| Tests superposición | `tests/test_superposicion.py` |

## Lecciones aprendidas

- La masa sísmica `W = G + 0.5Q` excluye la fundación (Subterráneo) porque no hay diafragma rígido en z=0.
- La fuerza sísmica se aplica en el CM real (no en el master), con momento correctivo `Mz` para equivalentar la traslación.
- La superposición lineal es exacta en modelos elásticos lineales: la verificación directa vs explícita da error ≤ 7e-09 (tol 1e-6).
- El barrido automático de demanda-capacidad encontró que las columnas 70×70 más solicitadas superaban la capacidad nominal (máx. radio 1.612 en la columna id=70 con la enfierradura perimetral 16 φ28 en todo el edificio).
- El plano estructural usa **dos configuraciones de enfierradura** para las columnas 70×70: la perimetral 16 φ28 (interior) y la del **pórtico extremo** (4 φ28 esquinas + 16 φ36 intermedias, A_s = 187.5 cm²). Asignar cada columna a su curva real (flag `borde`) recuperó 11 de las 12 columnas críticas: el radio máximo baja de 1.612 a **1.031** (id=70, única que queda ~3 % por encima del criterio nominal, sin factores φ).
- La verificación independiente (bloque rectangular ACI/NCh) muestra concordancia ≤ 2.3% en flexión pura y hasta 10% en el balanceado del muro con el modelo de fibras.

## Próximos pasos (Semana 4)

- Revisar la columna id=70 (radio 1.031 con la enfierradura real del pórtico extremo; +3.1 % sobre el criterio nominal sin factores φ).
- Considerar redistribución plástica o ajuste de idealización para esa única columna con utilización > 100%.
- Completar verificación con factores phi de diseño (ACI 318 / NCh430): con φ ≈ 0.65-0.9 el radio subiría y la id=70 quedaría claramente fuera de la curva de diseño.
- Documentar sensibilidad de la discretización de fibras (ya auditada en `sensibilidad_secciones.json`).
- Preparar visualización interactiva de curvas P-M en el visor 3D (la curva `columna_borde` ya se exporta y el visor la usa para los elementos marcados con `borde`).
