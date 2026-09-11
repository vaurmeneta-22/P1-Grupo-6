# Informe de Avance — Semana 1

| Campo | Valor |
|---|---|
| **Proyecto** | P1 — Laboratorio Estructural Digital (Edificio de Ingeniería) |
| **Curso** | Métodos Computacionales (8vo semestre) |
| **Grupo** | 6 |
| **Período** | 24 – 28 de agosto de 2026 |
| **Entregable** | Verificación cuantitativa del benchmark, interpretación, errores y arquitectura inicial |
| **Repositorio** | `https://github.com/vaurmeneta-22/P1-Grupo-6` (rama `main`) |

---

## 1. Objetivo de la semana

Implementar y verificar un **benchmark 3D en OpenSees** (marco de un vano por un vano) cuantitativamente: grados de libertad, ejes locales, apoyos, cargas de gravedad, reacciones y fuerzas internas. Se busca confirmar que los resultados son físicamente correctos antes de extrapolarlos al edificio completo (Semana 2).

## 2. Modelo del benchmark

| Parámetro | Valor |
|---|---|
| Vano X (`Lx`) | 10.0 m |
| Vano Y (`Ly`) | 8.9 m |
| Altura de eje de viga (`H_eje`) | 3.56 m |
| Columnas | 0.70 × 0.70 m (A=0.49 m², I=0.020008 m⁴, J=0.0714 m⁴) |
| Vigas | 0.60 × 0.80 m (A=0.48 m², Iy=0.0256 m⁴, Iz=0.0144 m⁴, J=0.0998 m⁴) |
| Material | f'c = 35 MPa; E = 27.8 GPa; ν = 0.2; G = E/[2(1+ν)] = 11.58 GPa; fy = 420 MPa |
| Nodos | 1–4 base (z=0), 5–8 cabeza (z=3.56) |
| Grados de libertad | 6 DOF por nodo (ux, uy, uz, rx, ry, rz) |
| Apoyos | Empotrados en nodos 1, 2, 3 y 4 (fix todos los DOF) |
| Elementos | `elasticBeamColumn` (4 columnas + 4 vigas), `geomTransf Linear` |
| Carga G | Bidireccional 45°, losa → vigas por área tributaria (equivalente uniforme `eleLoad -beamUniform`) |

**Cargas (G):**

- PP losa (15 cm) = 375 kg/m² → 3.68 kN/m²
- PMAD = 260 kg/m² → 2.55 kN/m²
- SC = 300 kg/m² → 2.94 kN/m²
- `q_G = 9.1723 kN/m²` ; `q_SC = 2.943 kN/m²`
- Tributaria: `h_trib = 4.45 m`; vigas X `w_eq_x = 22.653 kN/m`; vigas Y `w_eq_y = 20.409 kN/m`
- Carga total: `F = q_G · Lx · Ly = 816.335 kN`

## 3. Resultados cuantitativos (caso G)

### 3.1 Reacciones en la base (kN y kN·m)

| Nodo | Fx | Fy | Fz | Mx | My |
|---|---|---|---|---|---|
| 1 | +63.419 | +44.315 | 204.085 | −51.290 | +73.171 |
| 2 | −63.419 | +44.315 | 204.085 | −51.290 | −73.171 |
| 3 | +63.419 | −44.315 | 204.085 | +51.290 | +73.171 |
| 4 | −63.419 | −44.315 | 204.085 | +51.290 | −73.171 |
| **Σ** | **0.000** | **0.000** | **816.340** | — | — |

Interpretación: las componentes horizontales se cancelan por pares (el marco es símetrico y la carga es uniforme), y cada apoyo recibe un cuarto de la carga total (`816.335/4 = 204.084 kN`), como es esperable por simetría.

### 3.2 Desplazamientos nodos superiores (5–8)

| Nodo | ux (mm) | uy (mm) | uz (mm) | rx (rad) | ry (rad) |
|---|---|---|---|---|---|
| 5 | +0.0238 | +0.0148 | −0.0533 | −0.000177 | +0.000254 |
| 6 | −0.0238 | +0.0148 | −0.0533 | −0.000177 | −0.000254 |
| 7 | +0.0238 | −0.0148 | −0.0533 | +0.000177 | +0.000254 |
| 8 | −0.0238 | −0.0148 | −0.0533 | +0.000177 | −0.000254 |

Interpretación: el techo desciende 0.053 mm (valor del orden esperado para un marco de hormigón de ~Ø10 m con carga de servicio). Los nodos 5 y 7 se alejan hacia +X y los 6 y 8 hacia −X (el marco se "abre" en la planta); en Y, los nodos de la línea y=0 bajan hacia +Y y los de y=17.8 hacia −Y.

### 3.3 Fuerzas internas (locales, en el extremo i del elemento)

| Elemento | Tipo | P (kN) | V2 (kN) | V3 (kN) | T (kN·m) | M2 (kN·m) | M3 (kN·m) |
|---|---|---|---|---|---|---|---|
| 1 | Columna | 204.085 | −44.315 | 63.419 | 0.0 | −73.171 | −51.290 |
| 2 | Columna | 204.085 | −44.315 | −63.419 | 0.0 | 73.171 | −51.290 |
| 3 | Columna | 204.085 | +44.315 | 63.419 | 0.0 | −73.171 | 51.290 |
| 4 | Columna | 204.085 | +44.315 | −63.419 | 0.0 | 73.171 | 51.290 |
| 5 | Viga X | 63.419 | 0.0 | 113.267 | 0.0 | **−152.600** | 0.0 |
| 6 | Viga X | 63.419 | 0.0 | 113.267 | 0.0 | **−152.600** | 0.0 |
| 7 | Viga Y | 44.315 | 0.0 | 90.818 | 0.0 | −106.472 | 0.0 |
| 8 | Viga Y | 44.315 | 0.0 | 90.818 | 0.0 | −106.472 | 0.0 |

Valores extremos: `max|M2| = 152.60 kN·m` (viga X), `max|M3| = 51.29 kN·m` (columna), `max N = 204.08 kN` (columna), `max T ≈ 0` (sin excentricidad de carga).

## 4. Verificación

### 4.1 Equilibrio global

- Carga total aplicada: `F = q_G · Lx · Ly = 816.335 kN`
- Σ reacciones verticales: `ΣRz = 816.340 kN`
- Diferencia: `4.5×10⁻³ kN (≈5.4×10⁻⁴ %)`, atribuible al redondeo de `q_G` a 4 decimales en el JSON exportado
- El chequeo interno del script (precisión completa) reporta **`[OK] EQUILIBRIO VERIFICADO`** (error relativo < 1×10⁻⁶)
- `ΣFx = ΣFy = Mx = My = 0` cumplido por pares por simetría

### 4.2 Verificación analítica del orden de parámetros de `elasticBeamColumn`

Se detectó que la convención de argumentos del elemento 3D era ilegible y se verificó con un **cantiléver analítico**:

```
ux = F·H³ / (3·E·Iy)
```

| Orden probado | ux obtenido (m) | ux analítico (m) | ¿OK? |
|---|---|---|---|
| `(E, A, Iy, Iz, G, J)` | 2.6497×10⁻⁴ | 2.7038×10⁻³ | ✗ (10× menor: no flexiona) |
| `(A, E, G, J, Iy, Iz)` | 2.7038×10⁻³ | 2.7038×10⁻³ | ✓ |

La única lectura correcta para OpenSees 3D es **`elasticBeamColumn(tag, i, j, A, E, G, J, Iy, Iz, transf)`**. Con el orden viejo las vigas Y daban `M2 ≈ 0`, las columnas no flexionaban en el plano (Y, Z) y por lo tanto `Fy = 0` en los nodos 1–4 — un artefacto numérico, no un comportamiento real.

### 4.3 Simetría

Los resultados cumplen las simetrías del problema (uniform load, marco con apoyos idénticos): pares de reacciones espejadas, esfuerzos de columnas idénticos salvo signo, vigas X idénticas y vigas Y idénticas.

## 5. Errores encontrados y corregidos (Semana 1)

1. **Orden de argumentos de `elasticBeamColumn` (corregido):** se usaba `(E, A, Iy, Iz, G, J)`; el orden correcto es `(A, E, G, J, Iy, Iz)`. Impacto: deformaciones y momentos 10× menores y `Fy ≈ 0` en apoyos.
2. **`Fy = 0` en apoyos (corregido):** era consecuencia del punto anterior. Con el orden correcto `Fy = ±44.315 kN` y las vigas Y desarrollan `M2 = −106.47 kN·m`.
3. **Fallo preexistente en `pytest` (NO corregido, pendiente semana 2):** `tests/test_equilibrium.py` lanza `NameError: name 'w_G_x' is not defined`. Es un test de verificación aún no alineado con las variables del benchmark; se documenta para no "maquillar" tests.

## 6. Arquitectura inicial

```
P1-Grupo-6/
├── opensees/            # Scripts de análisis (benchmark_3d.py, tests de verificación)
│   └── resultados/      # Resultados del análisis (carpetas por tipo)
├── figures/             # (renombrada -> resultados/10_figuras) Diagramas 2D/3D
├── tests/               # Scripts de verificación (equilibrio, etc.)
├── docs/                # Documentación e informes
├── data/                # Datos compartidos (geometría, materiales, áreas tributarias)
└── Enunciado_Proyecto1/ # Pautas del proyecto
```

Decisión clave: **el JSON exportado es el contrato entre OpenSees (análisis) y Unity (visualización/interacción)**, con unidades explícitas (kN, m, kN·m) y campos documentados (AGENTS.md).

## 7. Entregables / visualización

- `opensees/benchmark_3d.py` — modelo benchmark 3D completo
- `resultados/08_verificacion/benchmark_3d.json` — resultados exportados (G)
- `resultados/10_figuras/Diagrama de Momento 2D y 3D.png`
- `resultados/10_figuras/Diagrama Esfuerzo Axial 2D y 3D.png`
- `resultados/10_figuras/Diagrama Esfuerzo de Corte 2D y 3D.png`
- `resultados/10_figuras/marco_3d_resultados.png` — deformada, desplazamientos, reacciones y cargas
- `resultados/10_figuras/marco_3d_interactivo.html` — vista 3D interactiva (girar/zoom + animación de la deformada + momentos sobre las barras)

## 8. Lecciones aprendidas

- La convención de argumentos de los elementos de OpenSees define qué eje flecta; una equivocación silenciosa revienta los resultados sin error de ejecución.
- La verificación analítica (cantiléver) es la forma más rápida de aislar errores de modelado.
- Las simetrías del modelo sirven como primer control de calidad (reacciones espejadas, pares exactos).
- Mantener el JSON como contrato separa el análisis de la visualización y facilita el QA.

## 9. Próximos pasos (Semana 2)

- Geometría estructural completa del edificio (multi-vano y multi-nivel).
- Carga de gravedad del edificio completo + áreas tributarias explícitas.
- Chequeos de conservación de carga y primer viewer 3D en Unity.
- Corregir `tests/test_equilibrium.py` y ampliar la suite de verificación.