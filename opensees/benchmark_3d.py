# -*- coding: utf-8 -*-
"""
Benchmark 3D - Marco con viga central (2 paños de losa)
Grupo 6 - Semana 1 - LAB

Geometria:
  1000 cm x 890 cm (a ejes)
  4 columnas 70x70 cm en las esquinas, altura eje viga = 356 cm
  7 vigas 60x80 cm (perimetrales + viga central en Y en x = 5.00 m)
  Apoyos empotrados en las 4 esquinas
  Losa dividida en 2 paños: 104 (5.00 x 8.90) y 105 (5.00 x 8.90)
  La viga central NO tiene columnas (nodos centrales solo de conexion)

Materiales:
  f'c = 35 MPa, E = 27.8 GPa
  Fy = 420 MPa

Cargas:
  PP losa = 375 kg/m2
  Pmad = 260 kg/m2
  SC = 300 kg/m2
"""

import openseespy.opensees as ops
import json
import os

# ============================================================
# 1. CONFIGURACION
# ============================================================

Lx = 10.0        # vano en X (m)
Ly = 8.9         # vano en Y (m)
H_eje = 3.56     # altura del eje de viga (m) = 396 - 40 cm

Lx_mid = Lx / 2.0   # x = 5.00 m: ubicacion de la viga central en Y

b_col = 0.70     # columna ancho (m)
h_col = 0.70     # columna alto (m)
b_vig = 0.60     # viga ancho (m)
h_vig = 0.80     # viga alto (m)

E = 27.8e6       # kN/m2 (27.8 GPa)
nu = 0.2
G = E / (2 * (1 + nu))  # kN/m2

q_pp = 375 * 9.81 / 1000   # 3.68 kN/m2
q_pmad = 260 * 9.81 / 1000 # 2.55 kN/m2
q_sc = 300 * 9.81 / 1000   # 2.94 kN/m2
q_G = q_pp + q_pmad +q_sc        

print("=" * 60)
print("BENCHMARK 3D - MARCO CON VIGA CENTRAL (2 PAÑOS DE LOSA)")
print("=" * 60)
print(f"Geometria: {Lx*100:.0f} cm x {Ly*100:.0f} cm")
print(f"Altura eje viga: {H_eje*100:.0f} cm")
print(f"Columna: {b_col*100:.0f}x{h_col*100:.0f} cm")
print(f"Viga: {b_vig*100:.0f}x{h_vig*100:.0f} cm")
print(f"E = {E/1e6:.1f} GPa, G = {G/1e6:.1f} GPa")
print(f"q_G = {q_G:.2f} kN/m2, q_SC = {q_sc:.2f} kN/m2")

# ============================================================
# 2. PROPIEDADES DE SECCIONES
# ============================================================

A_col = b_col * h_col
Iy_col = b_col * h_col**3 / 12
Iz_col = h_col * b_col**3 / 12
J_col = 0.208 * b_col * h_col**3

A_vig = b_vig * h_vig
Iy_vig = b_vig * h_vig**3 / 12
Iz_vig = h_vig * b_vig**3 / 12
J_vig = 0.208 * b_vig * h_vig**3

print(f"\nSeccion columna: A={A_col:.4f} m2, Iy={Iy_col:.6f} m4, Iz={Iz_col:.6f} m4, J={J_col:.6f} m4")
print(f"Seccion viga:    A={A_vig:.4f} m2, Iy={Iy_vig:.6f} m4, Iz={Iz_vig:.6f} m4, J={J_vig:.6f} m4")

# ============================================================
# 3. MODELO OPENSEES
# ============================================================

ops.wipe()
ops.model('basic', '-ndm', 3, '-ndf', 6)

# ============================================================
# 4. NODOS
# ============================================================

# Base (z=0)
ops.node(1, 0.0,  0.0,  0.0)
ops.node(2, Lx,   0.0,  0.0)
ops.node(3, 0.0,  Ly,   0.0)
ops.node(4, Lx,   Ly,   0.0)

# Cabeza (z=H_eje)
ops.node(5, 0.0,  0.0,  H_eje)
ops.node(6, Lx,   0.0,  H_eje)
ops.node(7, 0.0,  Ly,   H_eje)
ops.node(8, Lx,   Ly,   H_eje)

# Nodos centrales a nivel de viga (x = Lx_mid = 5.00 m)
# Solo conexion entre vigas. NO llevan columna.
ops.node(9,  Lx_mid, 0.0, H_eje)
ops.node(10, Lx_mid, Ly,  H_eje)

for i in range(1, 11):
    x, y, z = ops.nodeCoord(i)
    print(f"  Nodo {i}: ({x:.2f}, {y:.2f}, {z:.2f})")

# ============================================================
# 5. APOYOS (EMPOTRADOS)
# ============================================================

for i in [1, 2, 3, 4]:
    ops.fix(i, 1, 1, 1, 1, 1, 1)

print("\nApoyos empotrados: nodos 1, 2, 3, 4")

# ============================================================
# 6. TRANSFORMACIONES GEOMETRICAS
# ============================================================

# Columnas: local_x = +Z global (vertical), vecxz = (1,0,0)
# local x = (0,0,1), local z = (1,0,0), local y = (0,-1,0)
ops.geomTransf('Linear', 1, 1, 0, 0)

# Vigas: local_x a lo largo de X o Y, vecxz = (0,0,1)
# local z = (0,0,1) = global Z (vertical)
ops.geomTransf('Linear', 2, 0, 0, 1)

print("\nTransformaciones:")
print("  T1 (columnas): vecxz=(1,0,0) -> local_z = global_X")
print("  T2 (vigas):    vecxz=(0,0,1) -> local_z = global_Z")

# ============================================================
# 7. SECCIONES ELASTICAS
# ============================================================

ops.section('Elastic', 1, E, A_col, Iy_col, Iz_col, G, J_col)
ops.section('Elastic', 2, E, A_vig, Iy_vig, Iz_vig, G, J_vig)

# ============================================================
# 8. ELEMENTOS
# ============================================================

# Columnas (base -> cabeza)
ops.element('elasticBeamColumn', 1, 1, 5, A_col, E, G, J_col, Iy_col, Iz_col, 1)
ops.element('elasticBeamColumn', 2, 2, 6, A_col, E, G, J_col, Iy_col, Iz_col, 1)
ops.element('elasticBeamColumn', 3, 3, 7, A_col, E, G, J_col, Iy_col, Iz_col, 1)
ops.element('elasticBeamColumn', 4, 4, 8, A_col, E, G, J_col, Iy_col, Iz_col, 1)

# Vigas (elementos 5 a 11). Las vigas de 10.00 m se dividen en dos de 5.00 m
# por la viga central (x = Lx_mid).

# Vigas inferiores (y = 0.00 m)
ops.element('elasticBeamColumn', 5, 5, 9,  A_vig, E, G, J_vig, Iy_vig, Iz_vig, 2)  # inf izq (0->5)
ops.element('elasticBeamColumn', 6, 9, 6,  A_vig, E, G, J_vig, Iy_vig, Iz_vig, 2)  # inf der (5->10)

# Vigas superiores (y = 8.90 m)
ops.element('elasticBeamColumn', 7, 7, 10, A_vig, E, G, J_vig, Iy_vig, Iz_vig, 2)  # sup izq (0->5)
ops.element('elasticBeamColumn', 8, 10, 8, A_vig, E, G, J_vig, Iy_vig, Iz_vig, 2)  # sup der (5->10)

# Vigas laterales (en Y, x = 0 y x = 10)
ops.element('elasticBeamColumn', 9, 5, 7,  A_vig, E, G, J_vig, Iy_vig, Iz_vig, 2)  # lateral izq
ops.element('elasticBeamColumn', 10, 6, 8, A_vig, E, G, J_vig, Iy_vig, Iz_vig, 2)  # lateral der

# Viga central (en Y, x = Lx_mid = 5.00 m)
ops.element('elasticBeamColumn', 11, 9, 10, A_vig, E, G, J_vig, Iy_vig, Iz_vig, 2)

print("\n11 elementos definidos: 4 columnas + 7 vigas")

# ============================================================
# MUROS ESTRUCTURALES (preparacion - desactivados por defecto)
# ============================================================
# Se modelan como elementos 'equivalent wall' (elasticBeamColumn con seccion
# de muro: rectangulo de L_f x t), segun la convencion del proyecto
# (AGENTS.md). Son verticales (transf 1, igual que las columnas) y conectan
# piso a piso entre dos nodos del eje del muro.
#
# Para activar un muro completo WALLS con un dict, por ejemplo:
#   WALLS = [
#       {"id": 20, "nodes": (9, 10), "L_f": 5.0, "t": 0.20,
#        "E": 27.8e6, "nu": 0.2},
#   ]
# Los nodos ("nodes") DEBEN existir (uno por piso a lo largo del muro).
# Mientras WALLS este vacio no se crea ningun muro y no hay conflicto de tags.
WALLS = [
    # {"id": 20, "nodes": (9, 10), "L_f": 5.0, "t": 0.20, "E": 27.8e6, "nu": 0.2},
]

for w in WALLS:
    sec_id = 100 + w["id"]                     # tags de seccion de muro (evita conflictos)
    A_w  = w["L_f"] * w["t"]
    Iy_w = w["t"] * w["L_f"]**3 / 12.0         # flexion fuerte (en el plano del muro)
    Iz_w = w["L_f"] * w["t"]**3 / 12.0         # flexion debil (fuera del plano)
    G_w  = w["E"] / (2.0 * (1.0 + w["nu"]))
    J_w  = 0.208 * w["t"] * w["L_f"]**3
    ops.section('Elastic', sec_id, w["E"], A_w, Iy_w, Iz_w, G_w, J_w)
    ops.element('elasticBeamColumn', w["id"], w["nodes"][0], w["nodes"][1],
                A_w, w["E"], G_w, J_w, Iy_w, Iz_w, 1)

# ============================================================
# 9. DIAFRAGMA RIGIDO DEL PISO
# ============================================================
# Un diafragma rigido por piso. Constriñe en el plano (ux, uy, rz) de todos los
# nodos del piso al nodo maestro. La direccion perpendicular al plano del
# diafragma es Z (dirn=3). Se deja libre uz, rx, ry (flexion vertical).
#
# El nodo maestro debe ser un nodo ESTRUCTURAL (con rigidez propia): se usa el
# nodo 9 (union central inferior, conectado a las vigas 5, 6 y 11). Un nodo
# maestro "flotante" (sin elementos) deja DOF singulares y el analisis falla.
MASTER = 9
master_x, master_y, _ = ops.nodeCoord(MASTER)
ops.rigidDiaphragm(3, MASTER, 5, 6, 7, 8, 10)
print(f"\nDiafragma rigido en z={H_eje:.2f} m: master nodo {MASTER} "
      f"({master_x:.2f}, {master_y:.2f}), esclavos 5,6,7,8,10")

# ============================================================
# 10. CARGAS - Patron G (carga muerta)
# ============================================================

# Losa bidireccional dividida en 2 paños (104 y 105), reparto a 45 grados.
# Cada paño mide Sx x Sy = 5.00 x 8.90 m (Sx = Lx/2, Sy = Ly).
# La viga central (x = 5.00 m) es borde de ambos paños y recibe de los dos lados.
Sx = Lx / 2.0       # vano corto del paño (dimension X) = 5.00 m
Sy = Ly             # vano largo del paño (dimension Y) = 8.90 m
h_trib = Sx / 2.0   # reparto a 45 grados: mitad del vano menor del paño = 2.50 m

# Vigas que corren en X (superior/inferior, 4 elementos de 5.00 m): carga TRIANGULAR
Lx_elem = Sx                    # 5.00 m
tri_area_x = Lx_elem * h_trib / 2.0          # area por elemento = 6.25 m2
F_viga_x = q_G * tri_area_x                  # carga total por elemento X
w_eq_x = F_viga_x / Lx_elem                  # carga uniforme equivalente (kN/m)

# Vigas que corren en Y (laterales y central), largo Sy = 8.90 m: carga TRAPECIAL
trap_area_y_lat = (Sy + (Sy - 2 * h_trib)) / 2.0 * h_trib   # area por lateral = 16.0 m2
trap_area_y_cen = 2.0 * trap_area_y_lat                     # central: aporte de ambos paños = 32.0 m2
F_viga_y_lat = q_G * trap_area_y_lat
w_eq_y_lat = F_viga_y_lat / Sy
F_viga_y_cen = q_G * trap_area_y_cen
w_eq_y_cen = F_viga_y_cen / Sy

# Comprobacion de conservacion de carga de las losas
W_losas = q_G * Lx * Ly                       # q_G * 89.0 m2
W_vigas = 4 * F_viga_x + 2 * F_viga_y_lat + 1 * F_viga_y_cen
diff = W_vigas - W_losas

print(f"\nCarga G - 2 losas (104 y 105), reparto 45 grados:")
print(f"  Losa 104 = 5.00 x 8.90 m ; Losa 105 = 5.00 x 8.90 m")
print(f"  q_G = {q_G:.2f} kN/m2, h_trib (por paño) = {h_trib:.2f} m")
print(f"  Viga X (4 elems 5.00 m): area triangular/elem = {tri_area_x:.2f} m2, w_eq = {w_eq_x:.2f} kN/m")
print(f"  Viga lateral Y: area trapecial = {trap_area_y_lat:.2f} m2, w_eq = {w_eq_y_lat:.2f} kN/m")
print(f"  Viga central Y: area trapecial (2 paños) = {trap_area_y_cen:.2f} m2, w_eq = {w_eq_y_cen:.2f} kN/m")
print(f"\n--- COMPROBACION DE CARGAS ---")
print(f"  Carga total teorica de las losas      : {W_losas:.4f} kN")
print(f"  Carga total distribuida entre las vigas: {W_vigas:.4f} kN")
print(f"  Diferencia                             : {diff:.4e} kN")

ops.timeSeries('Linear', 1)
ops.pattern('Plain', 1, 1)

# Carga distribuida en las 7 vigas del piso
# local_z = global_Z para vigas con vecxz=(0,0,1); wz negativo = carga hacia abajo
w_loads = {
    5: w_eq_x,        # inferior izq
    6: w_eq_x,        # inferior der
    7: w_eq_x,        # superior izq
    8: w_eq_x,        # superior der
    9: w_eq_y_lat,    # lateral izq
    10: w_eq_y_lat,   # lateral der
    11: w_eq_y_cen,   # central (doble aporte)
}
for eid, w in w_loads.items():
    ops.eleLoad('-ele', eid, '-type', '-beamUniform', 0.0, -w)

# ============================================================
# 11. ANALISIS - CARGA G
# ============================================================

ops.system('BandSPD')
ops.numberer('RCM')
# Se requiere Transformation (no Plain) para eliminar correctamente los DOF
# esclavos del diafragma rigido (ux, uy, rz de los nodos del piso).
ops.constraints('Transformation')
ops.integrator('LoadControl', 1.0)
ops.algorithm('Linear')
ops.analysis('Static')

ok = ops.analyze(1)

if ok != 0:
    print("\n[ERROR] Analisis fallo")
    exit()

ops.reactions()
print("\n[OK] Analisis completado")

# ============================================================
# 12. EJES LOCALES (para transformar eleForce global -> local)
# ============================================================

def compute_local_axes(i_node, j_node, vecxz):
    import math
    xi, yi, zi = ops.nodeCoord(i_node)
    xj, yj, zj = ops.nodeCoord(j_node)
    dx = xj - xi
    dy = yj - yi
    dz = zj - zi
    L = math.sqrt(dx*dx + dy*dy + dz*dz)
    local_x = (dx/L, dy/L, dz/L)
    vx, vy, vz = vecxz
    dot = vx*local_x[0] + vy*local_x[1] + vz*local_x[2]
    lz = (vx - dot*local_x[0], vy - dot*local_x[1], vz - dot*local_x[2])
    lz_mag = math.sqrt(lz[0]**2 + lz[1]**2 + lz[2]**2)
    local_z = (lz[0]/lz_mag, lz[1]/lz_mag, lz[2]/lz_mag)
    local_y = (local_z[1]*local_x[2] - local_z[2]*local_x[1],
               local_z[2]*local_x[0] - local_z[0]*local_x[2],
               local_z[0]*local_x[1] - local_z[1]*local_x[0])
    return local_x, local_y, local_z

def global_to_local(f_global, local_x, local_y, local_z):
    R = [local_x, local_y, local_z]
    f_local = [0.0]*6
    for i in range(3):
        for j in range(3):
            f_local[i] += R[i][j] * f_global[j]
            f_local[i+3] += R[i][j] * f_global[j+3]
    return f_local

# Definir ejes locales por elemento
elem_data = {
    1: {"nodes": (1, 5), "vecxz": (1,0,0), "label": "Col 1"},
    2: {"nodes": (2, 6), "vecxz": (1,0,0), "label": "Col 2"},
    3: {"nodes": (3, 7), "vecxz": (1,0,0), "label": "Col 3"},
    4: {"nodes": (4, 8), "vecxz": (1,0,0), "label": "Col 4"},
    5:  {"nodes": (5, 9),  "vecxz": (0,0,1), "label": "Viga Inferior Izq (5->9)"},
    6:  {"nodes": (9, 6),  "vecxz": (0,0,1), "label": "Viga Inferior Der (9->6)"},
    7:  {"nodes": (7, 10), "vecxz": (0,0,1), "label": "Viga Superior Izq (7->10)"},
    8:  {"nodes": (10, 8), "vecxz": (0,0,1), "label": "Viga Superior Der (10->8)"},
    9:  {"nodes": (5, 7),  "vecxz": (0,0,1), "label": "Viga Lateral Izq (5->7)"},
    10: {"nodes": (6, 8),  "vecxz": (0,0,1), "label": "Viga Lateral Der (6->8)"},
    11: {"nodes": (9, 10), "vecxz": (0,0,1), "label": "Viga Central Y (9->10)"},
}

local_axes = {}
for eid, ed in elem_data.items():
    lx, ly, lz = compute_local_axes(ed["nodes"][0], ed["nodes"][1], ed["vecxz"])
    local_axes[eid] = (lx, ly, lz)

# ============================================================
# 13. RESULTADOS — CARGA G
# ============================================================

print("\n--- DESPLAZAMIENTOS ---")
disp = {}
for i in range(1, 11):
    d = ops.nodeDisp(i)
    disp[i] = d
    if i >= 5:
        print(f"  Nodo {i}: ux={d[0]*1000:.4f} mm, uy={d[1]*1000:.4f} mm, uz={d[2]*1000:.4f} mm")

print("\n--- FUERZAS COLUMNAS (locales) ---")
col_forces = {}
for i in [1, 2, 3, 4]:
    f_global = list(ops.eleForce(i))
    lx, ly, lz = local_axes[i]
    f_local = global_to_local(f_global, lx, ly, lz)
    col_forces[i] = f_local
    P, V2, V3, T, M2, M3 = f_local
    print(f"  Col {i}: P={P:.2f}, V2={V2:.2f}, V3={V3:.2f}, T={T:.2f}, M2={M2:.2f}, M3={M3:.2f}")

print("\n--- FUERZAS VIGAS (locales) ---")
beam_forces = {}
for i in [5, 6, 7, 8, 9, 10, 11]:
    f_global = list(ops.eleForce(i))
    lx, ly, lz = local_axes[i]
    f_local = global_to_local(f_global, lx, ly, lz)
    beam_forces[i] = f_local
    P, V2, V3, T, M2, M3 = f_local
    print(f"  Viga {i}: P={P:.2f}, V2={V2:.2f}, V3={V3:.2f}, T={T:.2f}, M2={M2:.2f}, M3={M3:.2f}")

print("\n--- REACCIONES ---")
R_total = 0
for i in [1, 2, 3, 4]:
    r = ops.nodeReaction(i)
    R_total += r[2]
    print(f"  R nodo {i}: Fx={r[0]:.2f}, Fy={r[1]:.2f}, Fz={r[2]:.2f}")

# ============================================================
# 14. VERIFICACION DE COMPATIBILIDAD DEL DIAFRAGMA
# ============================================================
# El diafragma rigido impone que todos los nodos del piso se muevan en planta
# como un disco rigido con el movimiento del nodo maestro (ux_m, uy_m, rz_m):
#   ux_i = ux_m - rz_m*(y_i - y_m)
#   uy_i = uy_m + rz_m*(x_i - x_m)
# Se comparan los desplazamientos reales de cada nodo esclavo contra esa
# prediccion rigida; deben coincidir (error ~ maquina).

print("\n" + "=" * 60)
print("VERIFICACION DE COMPATIBILIDAD DEL DIAFRAGMA")
print("=" * 60)
d_m = ops.nodeDisp(MASTER)
ux_m, uy_m, rz_m = d_m[0], d_m[1], d_m[5]
master_x, master_y, _ = ops.nodeCoord(MASTER)
print(f"  Master nodo {MASTER} (x={master_x:.2f}, y={master_y:.2f}): "
      f"ux={ux_m*1000:.5f} mm, uy={uy_m*1000:.5f} mm, rz={rz_m:.3e} rad")

max_err = 0.0
for n in [5, 6, 7, 8, 10]:
    x, y, _ = ops.nodeCoord(n)
    d = ops.nodeDisp(n)
    ux_pred = ux_m - rz_m * (y - master_y)
    uy_pred = uy_m + rz_m * (x - master_x)
    errx = d[0] - ux_pred
    erry = d[1] - uy_pred
    err = max(abs(errx), abs(erry))
    max_err = max(max_err, err)
    print(f"  Nodo {n}: ux={d[0]*1000:.5f} mm (pred {ux_pred*1000:.5f}), "
          f"uy={d[1]*1000:.5f} mm (pred {uy_pred*1000:.5f}), err={err:.3e} m")

if max_err < 1e-9:
    print("[OK] DIAFRAGMA COMPATIBLE: todos los nodos del piso se mueven como un disco rigido")
else:
    print("[ERROR] DIAFRAGMA INCOMPATIBLE")

# ============================================================
# 15. VERIFICACION DE EQUILIBRIO
# ============================================================

F_total = q_G * Lx * Ly

print("\n" + "=" * 60)
print("VERIFICACION DE EQUILIBRIO")
print("=" * 60)
print(f"Carga aplicada: q_G x Lx x Ly = {q_G:.2f} x {Lx:.1f} x {Ly:.1f} = {F_total:.2f} kN")
print(f"  Vigas (7 elems): 4 x {F_viga_x:.2f} + 2 x {F_viga_y_lat:.2f} + 1 x {F_viga_y_cen:.2f} = {W_vigas:.2f} kN")
print(f"Suma reacciones: {R_total:.2f} kN")
print(f"Error: {abs(R_total - F_total):.2e} kN")

tol = 1e-6
if abs(R_total - F_total) / F_total < tol:
    print("[OK] EQUILIBRIO VERIFICADO")
else:
    print("[ERROR] EQUILIBRIO NO VERIFICADO")

# ============================================================
# 16. EXPORTAR
# ============================================================

output = {
    "model": {
        "description": "Benchmark 3D - Marco con viga central (2 paños de losa)",
        "ndm": 3,
        "ndf": 6,
        "units": {"length": "m", "force": "kN", "moment": "kN*m"}
    },
    "geometry": {
        "Lx": Lx, "Ly": Ly, "H_eje": H_eje,
        "column": {"b": b_col, "h": h_col},
        "beam": {"b": b_vig, "h": h_vig},
        "slabs": {"104": {"Lx": Lx/2, "Ly": Ly}, "105": {"Lx": Lx/2, "Ly": Ly}},
        "central_beam_x": Lx_mid
    },
    "materials": {"E": E, "G": G, "fck": 35e3, "fy": 420e3},
    "loads": {
        "q_G": round(q_G, 4), "q_SC": round(q_sc, 4),
        "h_trib": round(h_trib, 4),
        "w_eq_x": round(w_eq_x, 4),
        "w_eq_y_lateral": round(w_eq_y_lat, 4),
        "w_eq_y_central": round(w_eq_y_cen, 4),
        "W_losas": round(W_losas, 4),
        "W_vigas": round(W_vigas, 4),
        "type": "bidirectional 45deg, 2 paños (104/105), equivalent uniform (eleLoad beamUniform)"
    },
    "nodes": {},
    "elements": {},
    "results_G": {
        "displacements": {},
        "reactions": {},
        "element_forces_local": {}
    }
}

for i in range(1, 11):
    x, y, z = ops.nodeCoord(i)
    fix = [1,1,1,1,1,1] if i <= 4 else [0,0,0,0,0,0]
    d = disp[i]
    output["nodes"][str(i)] = {"x": x, "y": y, "z": z, "fixity": fix}
    output["results_G"]["displacements"][str(i)] = {
        "ux": round(d[0], 12), "uy": round(d[1], 12), "uz": round(d[2], 12),
        "rx": round(d[3], 12), "ry": round(d[4], 12), "rz": round(d[5], 12)
    }

for i in [1, 2, 3, 4]:
    r = ops.nodeReaction(i)
    output["results_G"]["reactions"][str(i)] = {
        "Fx": round(r[0], 10), "Fy": round(r[1], 10), "Fz": round(r[2], 10),
        "Mx": round(r[3], 10), "My": round(r[4], 10), "Mz": round(r[5], 10)
    }

for eid, ed in elem_data.items():
    lx, ly, lz = local_axes[eid]
    output["elements"][str(eid)] = {
        "type": ed["label"].split()[0].lower(),
        "nodes": list(ed["nodes"]),
        "local_x": [round(v, 8) for v in lx],
        "local_y": [round(v, 8) for v in ly],
        "local_z": [round(v, 8) for v in lz]
    }
    f = col_forces[eid] if eid <= 4 else beam_forces[eid]
    output["results_G"]["element_forces_local"][str(eid)] = {
        "P": round(f[0], 10), "V2": round(f[1], 10), "V3": round(f[2], 10),
        "T": round(f[3], 10), "M2": round(f[4], 10), "M3": round(f[5], 10)
    }

results_dir = os.path.join(os.path.dirname(__file__), 'results')
os.makedirs(results_dir, exist_ok=True)
json_path = os.path.join(results_dir, 'benchmark_3d.json')

with open(json_path, 'w') as f:
    json.dump(output, f, indent=2)

print(f"\n[OK] JSON exportado a: {json_path}")
print(f"\n{'='*60}")
print("RESUMEN")
print(f"{'='*60}")
print(f"Carga total: {F_total:.2f} kN")
print(f"Reacciones:  {R_total:.2f} kN")
print(f"Desplaz max: uz = {disp[5][2]*1000:.4f} mm")

# ============================================================
# 17. TABLA RESUMEN DE LAS 7 VIGAS DEL PISO
# ============================================================
beam_labels = {
    5: "Viga inferior izq",  6: "Viga inferior der",
    7: "Viga superior izq",  8: "Viga superior der",
    9: "Viga lateral izq",  10: "Viga lateral der",
    11: "Viga central Y",
}
print("\n" + "=" * 78)
print("TABLA DE VIGAS DEL PISO (carga uniforme aplicada por elemento)")
print("=" * 78)
print(f"{'Elem':<6}{'Tipo':<24}{'Nod ini':<9}{'Nod fin':<9}{'Long (m)':<10}{'Carga (kN/m)':<14}")
for eid in [5, 6, 7, 8, 9, 10, 11]:
    n0, n1 = elem_data[eid]["nodes"]
    xi, yi, zi = ops.nodeCoord(n0); xj, yj, zj = ops.nodeCoord(n1)
    import math
    L = math.sqrt((xj-xi)**2 + (yj-yi)**2 + (zj-zi)**2)
    w = w_loads[eid]
    print(f"{eid:<6}{beam_labels[eid]:<24}{n0:<9}{n1:<9}{L:<10.3f}{w:<14.4f}")
