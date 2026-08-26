"""
Benchmark 3D — Marco 1 vano × 1 vano
Grupo 6 — Semana 1 — LAB

Geometría:
  1000 cm × 890 cm (a ejes)
  4 columnas 70×70 cm, altura eje viga = 356 cm
  4 vigas 60×80 cm
  Apoyos empotrados en las 4 esquinas
  Losa 15 cm descargada sobre vigas

Materiales:
  f'c = 35 MPa, E = 27.8 GPa
  Fy = 420 MPa

Cargas:
  PP losa = 375 kg/m²
  Pmad = 260 kg/m²
  SC = 300 kg/m²
"""

import openseespy.opensees as ops
import json
import os
import math

# ============================================================
# 1. CONFIGURACIÓN
# ============================================================

# Geometría (m)
Lx = 10.0        # vano en X
Ly = 8.9         # vano en Y
H_eje = 3.56     # altura del eje de viga (396 - 40 cm)

# Secciones
b_col = 0.70     # columna ancho
h_col = 0.70     # columna alto
b_vig = 0.60     # viga ancho
h_vig = 0.80     # viga alto

# Materiales
E = 27.8e6       # kN/m² (27.8 GPa)
G = E / (2 * (1 + 0.2))  # kN/m² (aproximación ν = 0.2)

# Cargas (kN/m²)
q_pp = 375 * 9.81 / 1000   # PP losa: 3.68 kN/m²
q_pmad = 260 * 9.81 / 1000 # Pmad: 2.55 kN/m²
q_sc = 300 * 9.81 / 1000   # SC: 2.94 kN/m²
q_G = q_pp + q_pmad         # Carga muerta total: 6.23 kN/m²

print("=" * 60)
print("BENCHMARK 3D — MARCO 1V × 1V")
print("=" * 60)
print(f"\nGeometría: {Lx*100:.0f} cm × {Ly*100:.0f} cm")
print(f"Altura eje viga: {H_eje*100:.0f} cm")
print(f"Columna: {b_col*100:.0f}×{h_col*100:.0f} cm")
print(f"Viga: {b_vig*100:.0f}×{h_vig*100:.0f} cm")
print(f"\nMateriales:")
print(f"  E = {E/1e6:.1f} GPa")
print(f"  G = {G/1e6:.1f} GPa")
print(f"\nCargas:")
print(f"  q_PP = {q_pp:.2f} kN/m²")
print(f"  q_Pmad = {q_pmad:.2f} kN/m²")
print(f"  q_G = {q_G:.2f} kN/m²")
print(f"  q_SC = {q_sc:.2f} kN/m²")

# ============================================================
# 2. PROPIEDADES DE SECCIONES
# ============================================================

# Columna 70×70 cm
A_col = b_col * h_col
Iy_col = b_col * h_col**3 / 12
Iz_col = h_col * b_col**3 / 12
J_col = 0.208 * b_col * h_col**3  # Aproximación para sección cuadrada

# Viga 60×80 cm
A_vig = b_vig * h_vig
Iy_vig = b_vig * h_vig**3 / 12   # flexión fuerte
Iz_vig = h_vig * b_vig**3 / 12   # flexión débil
J_vig = 0.208 * b_vig * h_vig**3

print(f"\nPropiedades de sección:")
print(f"  Columna: A={A_col:.4f} m², Iy={Iy_col:.6f} m⁴, Iz={Iz_col:.6f} m⁴")
print(f"  Viga:    A={A_vig:.4f} m², Iy={Iy_vig:.6f} m⁴, Iz={Iz_vig:.6f} m⁴")

# ============================================================
# 3. MODELO OPENSEES
# ============================================================

ops.wipe()
ops.model('basic', '-ndm', 3, '-ndf', 6)
print("\nModelo creado: 3D, 6 GDL por nodo")

# ============================================================
# 4. NODOS
# ============================================================

# Nodos base (z = 0)
ops.node(1, 0.0,  0.0,  0.0)
ops.node(2, Lx,   0.0,  0.0)
ops.node(3, 0.0,  Ly,   0.0)
ops.node(4, Lx,   Ly,   0.0)

# Nodos cabeza (z = H_eje)
ops.node(5, 0.0,  0.0,  H_eje)
ops.node(6, Lx,   0.0,  H_eje)
ops.node(7, 0.0,  Ly,   H_eje)
ops.node(8, Lx,   Ly,   H_eje)

print(f"\nNodos definidos:")
for i in range(1, 9):
    x, y, z = ops.nodeCoord(i)
    print(f"  Nodo {i}: ({x:.2f}, {y:.2f}, {z:.2f}) m")

# ============================================================
# 5. APOYOS (EMPOTRADOS)
# ============================================================

for i in [1, 2, 3, 4]:
    ops.fix(i, 1, 1, 1, 1, 1, 1)

print("\nApoyos: empotrados en nodos 1, 2, 3, 4")

# ============================================================
# 6. TRANSFORMACIONES GEOMÉTRICAS
# ============================================================

# Columnas: eje local Y vertical, vecxz = (1,0,0)
ops.geomTransf('Linear', 1, 1, 0, 0)

# Vigas: eje local Y a lo largo de X, vecxz = (0,0,1)
ops.geomTransf('Linear', 2, 0, 0, 1)

print("\nTransformaciones:")
print("  T1 (columnas): Linear, vecxz = (1,0,0) → eje Y vertical")
print("  T2 (vigas):    Linear, vecxz = (0,0,1) → eje Y horizontal")

# ============================================================
# 7. SECCIONES ELÁSTICAS
# ============================================================

# Sección 1: Columna
ops.section('Elastic', 1, E, A_col, Iy_col, Iz_col, G, J_col)

# Sección 2: Viga
ops.section('Elastic', 2, E, A_vig, Iy_vig, Iz_vig, G, J_vig)

print("\nSecciones definidas:")
print("  Sección 1: Columna 70×70 cm")
print("  Sección 2: Viga 60×80 cm")

# ============================================================
# 8. ELEMENTOS
# ============================================================

# Columnas: base → cabeza
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

print("\nElementos definidos:")
print("  Columnas: 1(1→5), 2(2→6), 3(3→7), 4(4→8)")
print("  Vigas X:  5(5→6), 6(7→8)")
print("  Vigas Y:  7(5→7), 8(6→8)")

# ============================================================
# 9. DIAFRAGMA RÍGIDO
# ============================================================

ops.rigidDiaphragm(3, 5, 6, 7, 8)
print("\nDiafragma rígido en el plano de cabezas (nodos 5,6,7,8)")

# ============================================================
# 10. CARGAS
# ============================================================

# --- Carga muerta (G) ---
# Descarga de losa sobre vigas por áreas tributarias
# Viga en X (dirección Y): tributaria = Ly/2 de cada lado
# Viga en Y (dirección X): tributaria = Lx/2 de cada lado

trib_x = Ly / 2  # 4.45 m (ancho tributario para vigas en X)
trib_y = Lx / 2  # 5.00 m (ancho tributario para vigas en Y)

w_G_x = q_G * trib_x  # kN/m sobre vigas en X
w_G_y = q_G * trib_y  # kN/m sobre vigas en Y

print(f"\nCargas gravitacionales:")
print(f"  q_G = {q_G:.2f} kN/m²")
print(f"  Ancho tributario vigas X: {trib_x:.2f} m")
print(f"  Ancho tributario vigas Y: {trib_y:.2f} m")
print(f"  Carga lineal vigas X: {w_G_x:.2f} kN/m")
print(f"  Carga lineal vigas Y: {w_G_y:.2f} kN/m")

# Patrón de carga G
ops.timeSeries('Linear', 1)
ops.pattern('Plain', 1, 1)

# Carga distribuida en vigas (dirección Y local = vertical global)
# Viga 5 (5→6): carga en -Y global
ops.eleLoad('-ele', 5, '-type', '-beamUniform', -w_G_x, 0, 0)
# Viga 6 (7→8): carga en -Y global
ops.eleLoad('-ele', 6, '-type', '-beamUniform', -w_G_x, 0, 0)
# Viga 7 (5→7): carga en -Y global (viga en Y, pero carga es vertical)
ops.eleLoad('-ele', 7, '-type', '-beamUniform', -w_G_y, 0, 0)
# Viga 8 (6→8): carga en -Y global
ops.eleLoad('-ele', 8, '-type', '-beamUniform', -w_G_y, 0, 0)

print("\nCargas G aplicadas sobre las 4 vigas")

# --- Carga viva (Q) ---
trib_x_Q = Ly / 2
trib_y_Q = Lx / 2

w_Q_x = q_sc * trib_x_Q
w_Q_y = q_sc * trib_y_Q

ops.timeSeries('Linear', 2)
ops.pattern('Plain', 2, 2)

ops.eleLoad('-ele', 5, '-type', '-beamUniform', -w_Q_x, 0, 0)
ops.eleLoad('-ele', 6, '-type', '-beamUniform', -w_Q_x, 0, 0)
ops.eleLoad('-ele', 7, '-type', '-beamUniform', -w_Q_y, 0, 0)
ops.eleLoad('-ele', 8, '-type', '-beamUniform', -w_Q_y, 0, 0)

print(f"\nCargas Q aplicadas:")
print(f"  q_SC = {q_sc:.2f} kN/m²")
print(f"  Carga lineal vigas X: {w_Q_x:.2f} kN/m")
print(f"  Carga lineal vigas Y: {w_Q_y:.2f} kN/m")

# ============================================================
# 11. ANÁLISIS — CARGA G
# ============================================================

ops.system('BandSPD')
ops.numberer('RCM')
ops.constraints('Plain')
ops.integrator('LoadControl', 1.0)
ops.algorithm('Linear')
ops.analysis('Static')

ok = ops.analyze(1)
if ok == 0:
    print("\n✓ Análisis G completado exitosamente")
else:
    print("\n✗ Análisis G falló")

ops.loadConst('-time', 0.0)

# ============================================================
# 12. RESULTADOS — CARGA G
# ============================================================

results_G = {}

# Desplazamientos
results_G["displacements"] = {}
for i in range(1, 9):
    d = ops.nodeDisp(i)
    results_G["displacements"][str(i)] = {
        "ux": round(d[0], 12),
        "uy": round(d[1], 12),
        "uz": round(d[2], 12),
        "rx": round(d[3], 12),
        "ry": round(d[4], 12),
        "rz": round(d[5], 12)
    }

# Reacciones
results_G["reactions"] = {}
for i in [1, 2, 3, 4]:
    r = ops.nodeReaction(i)
    results_G["reactions"][str(i)] = {
        "Fx": round(r[0], 10),
        "Fy": round(r[1], 10),
        "Fz": round(r[2], 10),
        "Mx": round(r[3], 10),
        "My": round(r[4], 10),
        "Mz": round(r[5], 10)
    }

# Fuerzas internas
results_G["element_forces"] = {}
for i in range(1, 9):
    f = ops.eleForce(i)
    results_G["element_forces"][str(i)] = {
        "axial": round(f[0], 10),
        "shear_y": round(f[1], 10),
        "shear_z": round(f[2], 10),
        "torque": round(f[3], 10),
        "moment_y": round(f[4], 10),
        "moment_z": round(f[5], 10)
    }

# ============================================================
# 13. VERIFICACIÓN DE EQUILIBRIO
# ============================================================

print("\n" + "=" * 60)
print("VERIFICACIÓN DE EQUILIBRIO — CARGA G")
print("=" * 60)

# Carga total aplicada
F_total = q_G * Lx * Ly
print(f"\nCarga total aplicada (q_G × A): {F_total:.2f} kN")
print(f"  q_G = {q_G:.2f} kN/m²")
print(f"  A = {Lx:.1f} × {Ly:.1f} = {Lx*Ly:.2f} m²")

# Suma de reacciones
R_total = 0
for i in [1, 2, 3, 4]:
    r = ops.nodeReaction(i)
    R_total += r[2]  # Fz
    print(f"  R_z nodo {i} = {r[2]:.2f} kN")

print(f"\nSuma de reacciones: {R_total:.2f} kN")
print(f"Carga total:        {F_total:.2f} kN")
print(f"Diferencia:         {abs(R_total - F_total):.2e} kN")

tolerance = 1e-6
if abs(R_total - F_total) / F_total < tolerance:
    print("✓ EQUILIBRIO VERIFICADO: ΣR = ΣF")
else:
    print("✗ ERROR DE EQUILIBRIO")

# ============================================================
# 14. DESPLAZAMIENTOS MÁXIMOS
# ============================================================

print("\n" + "=" * 60)
print("DESPLAZAMIENTOS — NODOS DE CABEZA")
print("=" * 60)

for i in [5, 6, 7, 8]:
    d = ops.nodeDisp(i)
    print(f"  Nodo {i}: uy = {d[1]*1000:.4f} mm, uz = {d[2]*1000:.4f} mm")

# ============================================================
# 15. FUERZAS EN ELEMENTOS
# ============================================================

print("\n" + "=" * 60)
print("FUERZAS INTERNAS — COLUMNAS")
print("=" * 60)

for i in [1, 2, 3, 4]:
    f = ops.eleForce(i)
    print(f"  Columna {i}: axial = {f[0]:.2f} kN, My = {f[4]:.2f} kN·m, Mz = {f[5]:.2f} kN·m")

print("\n" + "=" * 60)
print("FUERZAS INTERNAS — VIGAS")
print("=" * 60)

for i in [5, 6, 7, 8]:
    f = ops.eleForce(i)
    print(f"  Viga {i}: axial = {f[0]:.2f} kN, shear = {f[1]:.2f} kN, My = {f[4]:.2f} kN·m, Mz = {f[5]:.2f} kN·m")

# ============================================================
# 16. EXPORTAR RESULTADOS A JSON
# ============================================================

output = {
    "model": {
        "description": "Benchmark 3D — Marco 1v × 1v",
        "ndm": 3,
        "ndf": 6,
        "units": {
            "length": "m",
            "force": "kN",
            "moment": "kN*m",
            "stress": "kN/m2"
        }
    },
    "geometry": {
        "Lx": Lx,
        "Ly": Ly,
        "H_eje": H_eje,
        "column_section": {"b": b_col, "h": h_col},
        "beam_section": {"b": b_vig, "h": h_vig}
    },
    "materials": {
        "E": E,
        "G": G,
        "fck": 35e3,
        "fy": 420e3
    },
    "loads": {
        "q_pp": round(q_pp, 4),
        "q_pmad": round(q_pmad, 4),
        "q_G": round(q_G, 4),
        "q_SC": round(q_sc, 4),
        "tributary_x": trib_x,
        "tributary_y": trib_y,
        "w_G_x": round(w_G_x, 4),
        "w_G_y": round(w_G_y, 4)
    },
    "nodes": {},
    "elements": {},
    "results_G": results_G
}

for i in range(1, 9):
    x, y, z = ops.nodeCoord(i)
    fix = [ops.nodeFix(i)[j] for j in range(6)] if i <= 4 else [0,0,0,0,0,0]
    output["nodes"][str(i)] = {"x": x, "y": y, "z": z, "fixity": fix}

output["elements"] = {
    "1": {"type": "column", "nodes": [1, 5], "section": 1},
    "2": {"type": "column", "nodes": [2, 6], "section": 1},
    "3": {"type": "column", "nodes": [3, 7], "section": 1},
    "4": {"type": "column", "nodes": [4, 8], "section": 1},
    "5": {"type": "beam_x", "nodes": [5, 6], "section": 2},
    "6": {"type": "beam_x", "nodes": [7, 8], "section": 2},
    "7": {"type": "beam_y", "nodes": [5, 7], "section": 2},
    "8": {"type": "beam_y", "nodes": [6, 8], "section": 2}
}

# Guardar JSON
results_dir = os.path.join(os.path.dirname(__file__), 'results')
os.makedirs(results_dir, exist_ok=True)
json_path = os.path.join(results_dir, 'benchmark_3d.json')

with open(json_path, 'w') as f:
    json.dump(output, f, indent=2)

print(f"\n✓ Resultados exportados a: {json_path}")

# ============================================================
# 17. RESUMEN
# ============================================================

print("\n" + "=" * 60)
print("RESUMEN DEL BENCHMARK")
print("=" * 60)
print(f"\nCarga total: {F_total:.2f} kN")
print(f"Reacciones:  {R_total:.2f} kN")
print(f"Desplazamiento nodo 5 (esquina): uy = {ops.nodeDisp(5)[1]*1000:.4f} mm")
print(f"Desplazamiento nodo 6 (esquina): uy = {ops.nodeDisp(6)[1]*1000:.4f} mm")
print(f"\nVerificación de equilibrio: {'PASÓ' if abs(R_total - F_total) / F_total < tolerance else 'FALLÓ'}")
