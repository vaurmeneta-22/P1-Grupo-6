# PLAN — Empalmes viga-viga (vigas "volando" en la deformada)

## 1. Problema (confirmado, sin tocar código)

En la deformada, las vigas secundarias que descargan sobre vigas continuas
"quedan flotando" mientras las que terminan en columnas se ven bien.

**Verificación realizada sobre el contrato:**

- 120 extremos de viga "colgando": su nodo no tiene columna **ni comparte con
  ningún otro elemento** (115 vigas distintas).
  - 100 de ellos caen geométricamente ENCIMA de una viga continua que pasa por
    esa coordenada **sin nodo intermedio** (la viga primaria nunca se subdivide).
  - 20 restantes NO tienen viga pasante (líneas de borde x=60 y vigas de la zona
    de muros inclinados x=3205) → requieren revisión estructural aparte.
- **Causa raíz más amplia:** existen **143 nodos estructurales del contrato que son
  interiores de otra viga** (cruces T y cruces en X, ej. el nodo 456 de las
  beam_y 439/440 está sobre la beam_x 381 que pasa de 1080→2080 sin nodo).
  Ninguno de esos cruces se materializa en la malla: las dos vigas NO comparten
  nodo → en el análisis la unión no existe.

**Física del FE:** el análisis converge igual (el diafragma rígido ata in-plane
los nodos flotantes al master del piso), pero la conexión vertical/rotacional de
la T queda rota → la viga secundaria se deforma como elemento independiente y el
viewer la muestra desconectada.

**Origen en código:** `opensees/conexiones.py`, sección 4 de `_build_plan` solo
procesa **nodos de MURO** (`for tagW in wall_tags`) para crear splits (regla B).
No existe ninguna regla que subdivida una viga en los puntos donde **otra viga**
aterriza o la cruza sin columna.

## 2. Objetivo

Que todo cruce/empalme viga↔viga quede **conectado por nodo compartido** en el
FE, de forma que la deformada de las vigas secundarias sea coherente con las
primarias y las columnas. Sin cambiar geometría, secciones, ni tags del contrato.

## 3. Estrategia (aprobación requerida de idealización estructural)

### Regla F — Empalme viga-viga (nueva, en `conexiones.py`)

Para cada viga `B` (beam_x/beam_y) y cada **nodo estructural del contrato** que
**no sea columna** y **no sea extremo propio de B**:
- si el nodo yace INTERIOR al segmento de `B` (misma cota z, `0.005 < t < 0.995`,
  tol posicional 2.5 cm) → marcar **split point** en `B` **REUSANDO el tag del
  nodo existente** (NO crear nodo 200000+).

Efecto en malla:
- La viga continua se subdivide en fracciones elasticBeamColumn; la 1ª fracción
  conserva el tag del contrato (viewer 1:1 intacto); las siguientes reciben tags
  300000+ (mismo mecanismo que ya usa la regla B para muros).
- La viga secundaria que aportó el nodo comparte ese nodo con las fracciones de
  la primaria → conexión real (6 DOF).

Coexistencia con la regla B (muros):
- Unificar el bucket `beam_split_pts[vid][key_pt]` para admitir dos orígenes:
  (a) pie de muro → crear nodo 200000+ (lógica actual), (b) empalme viga-viga →
  REUTILIZAR nodo del contrato. Si en un mismo punto confluyen ambos, se prioriza
  el reuse del nodo del contrato (nunca duplicar).
- Mantener el orden por `t` y el arranque del pool de tags igual que hoy.

### Casos especiales (20 extremos sin viga pasante)

- **Resueltos por Regla G (implementado)** — beam_x 335–344 (x=60, borde este):
  nodos 167–180 conectados a la muralla 315–319 (muro de fachada x=57.5, panel
  25×795 en planta). Regla G (sección `4c` de `conexiones.py`) une cada extremo
  a su nodo de muro del mismo nivel (9033→167/168 … 9037→179/180) con rigidLink
  `beam`, maestro = nodo de muro. Los nodos APOYADOS en el muro quedan fuera de
  `casos_especiales` y dejan el suelo vertical artificial (u_z ya no es 0, baja
  con el muro ~0.001–0.006 cm). Selección de muros en `regla_g_walls.json`
  (generada desde `muro_seleccion.html`).
- **Pendiente de asignar muro** — beam_y 390–394 (x=3205, zona de muros
  inclinados): nodos 398–407. Siguen en `casos_especiales` con apoyo vertical
  por losa hasta que el usuario seleccione sus muros en `muro_seleccion.html`.

## 4. Cambios de código

| Archivo | Cambio |
|---|---|
| `opensees/conexiones.py` | Nueva sección: detectar nodos estructurales interiores de cada viga y marcarlos como split points con **reuse de tag existente**. Ajustar la materialización de `beam_split_pts` para soportar reuse + creación. Estadísticas nuevas (empalmes, vigas subdivididas, fracciones). Sin cambios de tags reservados ni del contrato. |
| `opensees/verificador_camino_carga.py` | Nuevo chequeo FASE 4: **0 extremos de viga colgando** (todo extremo debe compartir nodo con ≥1 elemento/apoyo o pertenecer a la lista documentada de especiales). |
| `opensees/opensees_edificio_v2.py` | Sin cambios de lógica (consume `frame_split`). Re-correr los 5 casos. |
| `opensees/exportar_analysis_map.py` | Sin cambios de lógica (mapa 1:1 con el contrato). Re-generar. |
| `edificio_3d.html` | Sin cambios (deformada usa `D[meta.ni/nj]` con los nodos compartidos). |

## 5. Tests y verificación

- **Tests nuevos (puros, sin OpenSees)** `tests/test_empalmes_viga_viga.py`:
  - cada nodo estructural interior de una viga genera split;
  - reuse del tag del contrato (0 nodos 200000+ por empalme viga-viga);
  - orden de fracciones por `t`, 1ª fracción conserva tag;
  - cruces con pie de muro simultáneo no duplican nodo;
  - post-fix: **0 extremos de viga colgando** en el contrato real (excepto los
    20 documentados en la lista de especiales);
  - tags reservados no colisionan (mismos invariantes que el bloque actual).
- **Auditorías existentes:** 5 casos (G/Q/EX/EY/COMBO), equilibrio global
  (~1e-15), corte basal con signo, W_CM==W_F, FASE 3 (verificador de camino de
  carga), pytest completo (28 + nuevos).
- Regenerar `analysis_map.js` y abrir el viewer: las vigas 440/432/438/437 y
  similares deben deformarse **coherentes** con sus primarias (fin del "volando").
- Revisión manual de los 20 casos especiales con el usuario.

## 6. Criterios de éxito

1. 0 extremos de viga colgando (120 → 0, salvo especiales documentados).
2. 143 empalmes interiores materializados con nodo compartido.
3. Deformada coherente en viewer para las vigas reportadas.
4. Invariantes e indicadores numéricos idénticos/precisión de máquina.
5. pytest verde.

## 7. Fuera de alcance (separado, NO en este plan)

- **Muros congelados en la deformada** = bug de registro de desplazamientos de
  nodos esclavos de rigidLink (9000+) que reportan D≈0. Fix propuesto aparte:
  reconstruir D_esclavo = D_master + R×(x_slave − x_master) al exportar. No se
  toca aquí salvo solicitud del usuario.
- Idealización de los 20 casos especiales (regla G).

## 8. Comandos de ejecución

```bash
# diagnóstico/plan (solo lectura)
python conexiones.py

# análisis (5 casos)
python opensees_edificio_v2.py

# verificación de camino de carga (FASE 3 + FASE 4)
python verificador_camino_carga.py

# mapa del viewer
python exportar_analysis_map.py

# tests
python -m pytest tests/
```