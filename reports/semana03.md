# Semana 3 — Partes A (Q) y B (EX/EY)

## Resumen
Implementación de carga viva independiente `Q` y casos sísmicos pseudoestáticos `EX`/`EY` sobre el modelo OpenSeesPy existente de la Semana 2, con auditorías automáticas e interacción modular `run_case("G"|"Q"|"EX"|"EY")`.

**Novedad principal de esta revisión:** el reparto tributario fue **reescrito por TRAMOS** (perfil 45° exacto punto a punto + partición de cada borde de losa por viga receptora), y toda la masa sísmica / CM usa **el mismo conjunto de losas y las mismas áreas transferidas** que la carga G/Q (consistencia total entre transferencia, masa, fuerzas y verificaciones).

## Correcciones aplicadas en esta revisión (8 puntos de la revisión)

1. **Reparto tributario por TRAMOS** (`areas_tributarias.py` reescrito):
   - `tramos_receptores()`: particiona el contacto `[min,max]` de cada borde en tramos **disjuntos por viga** (sweep, recorta solapes, fusiona tramos de una misma viga) y reporta los **huecos** (banda sin viga) como pendientes — nunca se inventa soporte.
   - `_perfil_45()` / `area_por_tramo_45()`: perfil de 45 grados **exacto** `w(s) = s | h | Lm−s` con meseta `h=Lc/2`, re-baselineado al inicio de cada borde (corrige el bug de tramos con **coordenadas negativas** que daban área 0). La integral se escala por `A_total/A45` → conservación de máquina por borde.
   - `_transferir()`: núcleo con **aportes por losa-borde-tramo** (trazabilidad completa: `loza, borde, tramo cm, vid, área, W, p`), bordes libres absorbidos como **extras explícitos** sobre el perfil base (voladizo y pares ambos-libres), sin redondeo en los acumuladores.
   - `verificar_areas_tributarias()` reescrito: conservación `A_trib + A_huecos = A_soportadas` y `W_vigas = W_losas − W_huecos` (tol 1e-10), con recuento de vigas cargadas, huecos y losas aisladas.

2. **Validación de borde multi-viga** (losa 698 → vigas 411/412): partición contigua en `[426.5, 725]` y `[725, 1188.5]`, suma `A = 12.385750 m²` == área del borde, sin hueco. Mismo resultado para las losas 699–702.

3. **Consistencia masa sísmica / CM con la transferencia** (`opensees_edificio_v2.py`): `G_floor`, `Q_floor`, masa sísmica y CM usan el **área transferida por losa** (`trib_area_by_loza`, derivada de los aportes). Los **huecos (0.31 m²)** y las **losas aisladas (2.256 m²)** quedan fuera de la masa del modelo (no hay elemento estructural que las lleve) y se reportan aparte. Antes el CM usaba el área geométrica completa (inconsistente con la transferencia).

4. **CM ponderado G + 0.50·Q con carga equivalente** (`v2`): CM por piso = masa estructural (nodos con `W/2`) + losa (área transferida). La fuerza se aplica en el **master** del diafragma como `Fx, Fy + Mz = (xCM − xM)·Fy − (yCM − yM)·Fx`. Se exporta el movimiento del **master** y transformado al **CM** (`Ux_master_m/Uy_master_m`, `Ux_CM_m/Uy_CM_m`; Rz en rad, desplazamientos en m).

5. **Verificaciones estrictas** (`v2`):
   - Equilibrio y conservación en tol **1e-10** (antes 1e-6).
   - `F_esperada = α·W_efectivo` calculada de forma **INDEPENDIENTE** (desde `G_floor`/`Q_floor`, sin reutilizar la lista aplicada) y con exigencia de **participación** de todos los pisos con masa (excepto Subterráneo).
   - **Corte basal con signo**: `F_aplicada + R_base = 0` (no `|R| − F`).
   - `W_CM == W_F` por piso (`err_W_cm`), incluye el peso estructural de nodos cuya `z` cae en la banda del piso aunque no sea la `z` exacta del diafragma (corrige el desvío de −246 kN detectado en Piso 1).
   - Bandera `todas_ok` = `ok_eq ∧ ok_areas ∧ ok_dia ∧ ok_q ∧ ok_mass ∧ okFe ∧ okV`.
   - Signo de deformada verificado en **todos** los pisos (no solo el primero).

6. **Diagnóstico de pisos** (`v2`): detección de **diafragmas duplicados** por piso y de **pisos con masa sin master** (avisos, no sobrescritura silenciosa).

7. **Unidades / documentación**: `masa_kg = 1000·W/g` por piso; `aportes` por viga en `tributary_by_viga`; Q calculada **una vez** (antes se recalcularon las cargas Q por viga en cada iteración); docstring de cabecera actualizado (se retiraron los comentarios "pendiente en próximas versiones" que ya eran falsos).

8. **Tests automatizados** (`tests/test_areas_tributarias.py`, 10 tests nuevos, sin abrir OpenSees): conservación del perfil 45°, re-baseline con coordenadas negativas, reglas del sweep (contiguas / solape / viga parcial / sin viga), conservación global del contrato real (<1e-10), borde multi-viga de la losa 698, aisladas (649/653/657/661) y 9 huecos.

## Resultados

### Áreas y conservación (verificador tributario, contrato real)
- Área de losas **soportadas**: **5674.70 m²**; transferida a vigas: **5674.39 m²**; huecos pendientes: **0.310 m²** (9 bordes con viga parcial); losas aisladas: **2.256 m²** (4 losas 649/653/657/661, antepecho sin viga).
- `A_trib + A_huecos = A_soportadas` (rel. 0.000e+00) y `W_vigas = W_losas − W_huecos` (rel. 1.16e-16). **Coherencia: OK.**
- 301 vigas cargadas; rango de carga p ≈ 1.7–19.4 kN/m.

### Caso G (referencia)
- Peso propio estructural: 41967.86 kN; losa tributaria (transferida): 31274.39 kN; **total: 73242.256 kN**.
- Equilibrio: **OK** (err=9.9e-16).
- Nota: el total baja 1.7 kN respecto del reporte anterior porque los **huecos** (banda sin viga) ya no se transfieren ni se inventan.

### Caso Q (carga viva)
- q_Q = 2.0 kN/m². Área **transferible** = soportada − huecos = **5674.39 m²** → **Q transferida = 11 348.78 kN** (301 vigas).
- Excluidas y reportadas aparte: losas aisladas 2.256 m² y huecos 0.310 m².
- Conservación con la referencia: **OK** (err=1.1e-15). Equilibrio: **OK** (err=3.2e-16).

### Casos Sísmicos (EX/EY)
α = 0.20, fracción Q = 0.50, g = 9.81 m/s². Masa sísmica y fuerza **por nivel**:

| Nivel | G (kN) | Q (kN) | W (kN) | masa (t) | F (kN) | master | CM (x, y) |
|-------|--------|--------|--------|----------|--------|--------|-----------|
| Piso 1 | 9711.90 | 1251.80 | 10337.80 | 1053.80 | 2067.56 | 186 | (8.373, 8.040) |
| Piso 2 | 14894.56 | 2282.51 | 16035.82 | 1634.64 | 3207.16 | 29  | (−4.602, 7.756) |
| Piso 3 | 15298.31 | 2493.21 | 16544.91 | 1686.54 | 3308.98 | 78  | (−5.741, 7.633) |
| Piso 4 | 16488.64 | 2637.02 | 17807.15 | 1815.20 | 3561.43 | 111 | (−7.755, 7.788) |
| Techo  | 15266.00 | 2684.24 | 16608.12 | 1692.98 | 3321.62 | 146 | (−8.259, 7.843) |

**W_efectivo = 77333.80 kN** (5 pisos con diafragma; fundación/subterráneo = 1582.85 kN excluida y documentada). **F_total = 15466.76 kN = α·W_efectivo**.

| Verificación | EX | EY |
|-------------|-----|-----|
| F aplicada = F esperada (independiente) | **OK** (err 0.0) | **OK** (err 0.0) |
| Corte basal con signo (F + R_base = 0) | **OK** (4.7e-15) | **OK** (2.3e-14) |
| Equilibrio (ΣF + ΣR_base = 0) | **OK** (3.5e-15) | **OK** (2.3e-14) |
| W_CM == W_F en los 5 pisos | **OK** (err 0.0) | **OK** |
| Signo de deformada en todos los pisos | **OK** | **OK** |
| Torsión Rz (asimetría CM vs centro de rigidez) | reportada | reportada |

Desplazamientos del CM por nivel (EX, eje X; m → mm):

| Nivel | Ux_CM (mm) | Rz (rad) |
|-------|------------|----------|
| Piso 1 | 0.157 | 1.8e-06 |
| Piso 2 | 0.502 | 6.7e-06 |
| Piso 3 | 1.229 | 7.7e-06 |
| Piso 4 | 2.045 | 8.6e-06 |
| Techo | 2.717 | 8.8e-06 |

## Parámetros a confirmar con profesor
1. **α_sismo = 0.20** — valor del ejemplo del enunciado, pendiente de confirmación.
2. **q_Q = 2.00 kN/m²** — sobrecarga uniforme del contrato.
3. **Fracción de carga viva en masa sísmica = 50%** — valor estándar.
4. **Huecos de cobertura (0.31 m², 9 bordes con viga parcial)** y **losas aisladas (2.256 m²)**: se reportan como pendientes y quedan fuera de la masa del modelo (no hay viga que los reciba). Justificado y auditable.

## Archivos modificados
- `opensees/areas_tributarias.py` — reparto tributario por TRAMOS (perfil 45° exacto, huecos, aportes, verificador).
- `opensees/opensees_edificio_v2.py` — consistencia masa/CM (áreas transferidas), verificaciones estrictas (1e-10, F independiente, corte con signo, W_CM==W_F), diagnóstico de pisos, `portes`/`masa_kg`, Q calculada una vez, docstring.
- `tests/test_areas_tributarias.py` — **nuevo**: 10 tests de la transferencia por tramos.
- `reports/semana03.md` — este reporte.

## Comando de ejecución
```bash
# Todos los casos
python opensees_edificio_v2.py

# Caso individual
python opensees_edificio_v2.py --case G
python opensees_edificio_v2.py --case Q
python opensees_edificio_v2.py --case EX
python opensees_edificio_v2.py --case EY

# Tests
python -m pytest tests/
```

## Pendiente (Semana 3, Partes C y D)
- Parte C: Superposición R = λ_G·R_G + λ_Q·R_Q + λ_EX·R_EX + λ_EY·R_EY.
- Parte D: Fiber sections para M-φ y P-M (análisis de capacidad RC).