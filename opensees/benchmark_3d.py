# -*- coding: utf-8 -*-
"""
Benchmark 3D - Marco 1 vano x 1 vano
Grupo 6 - Semana 1 - LAB

Geometria:
  1000 cm x 890 cm (a ejes)
  4 columnas 70x70 cm, altura eje viga = 356 cm
  4 vigas 60x80 cm
  Apoyos empotrados en las 4 esquinas
  Losa 15 cm descargada sobre vigas en X

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
print("BENCHMARK 3D - MARCO 1V x 1V")
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

for i in range(1, 9):
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
ops.element('elasticBeamColumn', 1, 1, 5, E, A_col, Iy_col, Iz_col, G, J_col, 1)
ops.element('elasticBeamColumn', 2, 2, 6, E, A_col, Iy_col, Iz_col, G, J_col, 1)
ops.element('elasticBeamColumn', 3, 3, 7, E, A_col, Iy_col, Iz_col, G, J_col, 1)
ops.element('elasticBeamColumn', 4, 4, 8, E, A_col, Iy_col, Iz_col, G, J_col, 1)

# Vigas en X
ops.element('elasticBeamColumn', 5, 5, 6, E, A_vig, Iy_vig, Iz_vig, G, J_vig, 2)
ops.element('elasticBeamColumn', 6, 7, 8, E, A_vig, Iy_vig, Iz_vig, G, J_vig, 2)

# Vigas en Y
ops.element('elasticBeamColumn', 7, 5, 7, E, A_vig, Iy_vig, Iz_vig, G, J_vig, 2)
ops.element('elasticBeamColumn', 8, 6, 8, E, A_vig, Iy_vig, Iz_vig, G, J_vig, 2)

print("\n8 elementos definidos: 4 columnas + 4 vigas")

# ============================================================
# 9. CARGAS - Patron G (carga muerta)
# ============================================================

# Losa bidireccional, reparto a 45 grados a las 4 vigas perimetrales
# h = mitad del vano menor = Ly/2 = 4.45 m
h_trib = min(Lx, Ly) / 2  # 4.45 m

# Viga X (elems 5, 6): carga trapecial
# Area trapecial = (Lx + (Lx - 2*h)) / 2 * h
trap_area_x = (Lx + (Lx - 2 * h_trib)) / 2 * h_trib
F_viga_x = q_G * trap_area_x  # carga total por viga X
w_eq_x = F_viga_x / Lx  # carga uniforme equivalente

# Viga Y (elems 7, 8): carga triangular
# Area triangular = Ly * h / 2
tri_area_y = Ly * h_trib / 2
F_viga_y = q_G * tri_area_y  # carga total por viga Y
w_eq_y = F_viga_y / Ly  # carga uniforme equivalente

# Verificacion: suma total debe ser q_G * Lx * Ly
F_total_check = 2 * F_viga_x + 2 * F_viga_y

print(f"\nCarga G - Losa bidireccional (reparto 45 grados):")
print(f"  q_G = {q_G:.2f} kN/m2")
print(f"  h_trib = {h_trib:.2f} m (mitad del vano menor)")
print(f"  Viga X: area trapecial = {trap_area_x:.2f} m2, F = {F_viga_x:.2f} kN, w_eq = {w_eq_x:.2f} kN/m")
print(f"  Viga Y: area triangular = {tri_area_y:.2f} m2, F = {F_viga_y:.2f} kN, w_eq = {w_eq_y:.2f} kN/m")
print(f"  Verificacion total: {F_total_check:.2f} kN = q_G x Lx x Ly = {q_G * Lx * Ly:.2f} kN")

ops.timeSeries('Linear', 1)
ops.pattern('Plain', 1, 1)

# Carga distribuida en las 4 vigas perimetrales
# local_z = global_Z para vigas con vecxz=(0,0,1)
# wz negativo = carga hacia abajo (-Z global)
ops.eleLoad('-ele', 5, '-type', '-beamUniform', 0.0, -w_eq_x)
ops.eleLoad('-ele', 6, '-type', '-beamUniform', 0.0, -w_eq_x)
ops.eleLoad('-ele', 7, '-type', '-beamUniform', 0.0, -w_eq_y)
ops.eleLoad('-ele', 8, '-type', '-beamUniform', 0.0, -w_eq_y)

# ============================================================
# 10. ANALISIS - CARGA G
# ============================================================

ops.system('BandSPD')
ops.numberer('RCM')
ops.constraints('Plain')
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
# 11. EJES LOCALES (para transformar eleForce global -> local)
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
    5: {"nodes": (5, 6), "vecxz": (0,0,1), "label": "Viga 5(5->6)"},
    6: {"nodes": (7, 8), "vecxz": (0,0,1), "label": "Viga 6(7->8)"},
    7: {"nodes": (5, 7), "vecxz": (0,0,1), "label": "Viga 7(5->7)"},
    8: {"nodes": (6, 8), "vecxz": (0,0,1), "label": "Viga 8(6->8)"},
}

local_axes = {}
for eid, ed in elem_data.items():
    lx, ly, lz = compute_local_axes(ed["nodes"][0], ed["nodes"][1], ed["vecxz"])
    local_axes[eid] = (lx, ly, lz)

# ============================================================
# 12. RESULTADOS — CARGA G
# ============================================================

print("\n--- DESPLAZAMIENTOS ---")
disp = {}
for i in range(1, 9):
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
for i in [5, 6, 7, 8]:
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
# 13. VERIFICACION DE EQUILIBRIO
# ============================================================

F_total = q_G * Lx * Ly

print("\n" + "=" * 60)
print("VERIFICACION DE EQUILIBRIO")
print("=" * 60)
print(f"Carga aplicada: q_G x Lx x Ly = {q_G:.2f} x {Lx:.1f} x {Ly:.1f} = {F_total:.2f} kN")
print(f"  Vigas X: 2 x {F_viga_x:.2f} = {2*F_viga_x:.2f} kN")
print(f"  Vigas Y: 2 x {F_viga_y:.2f} = {2*F_viga_y:.2f} kN")
print(f"Suma reacciones: {R_total:.2f} kN")
print(f"Error: {abs(R_total - F_total):.2e} kN")

tol = 1e-6
if abs(R_total - F_total) / F_total < tol:
    print("[OK] EQUILIBRIO VERIFICADO")
else:
    print("[ERROR] EQUILIBRIO NO VERIFICADO")

# ============================================================
# 14. EXPORTAR
# ============================================================

output = {
    "model": {
        "description": "Benchmark 3D - Marco 1v x 1v",
        "ndm": 3,
        "ndf": 6,
        "units": {"length": "m", "force": "kN", "moment": "kN*m"}
    },
    "geometry": {
        "Lx": Lx, "Ly": Ly, "H_eje": H_eje,
        "column": {"b": b_col, "h": h_col},
        "beam": {"b": b_vig, "h": h_vig}
    },
    "materials": {"E": E, "G": G, "fck": 35e3, "fy": 420e3},
    "loads": {
        "q_G": round(q_G, 4), "q_SC": round(q_sc, 4),
        "h_trib": h_trib,
        "w_eq_x": round(w_eq_x, 4), "w_eq_y": round(w_eq_y, 4),
        "type": "bidirectional 45deg, equivalent uniform (eleLoad beamUniform)"
    },
    "nodes": {},
    "elements": {},
    "results_G": {
        "displacements": {},
        "reactions": {},
        "element_forces_local": {}
    }
}

for i in range(1, 9):
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
