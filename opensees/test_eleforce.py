# -*- coding: utf-8 -*-
"""
Prueba: verificar si eleForce retorna coordenadas GLOBALES o LOCALES.
Aplica carga asimetrica en nodo 5 con componentes Fx y Fz.
"""

import openseespy.opensees as ops

ops.wipe()
ops.model('basic', '-ndm', 3, '-ndf', 6)

# 2 nodos: base fijo, cabeza libre
ops.node(1, 0.0, 0.0, 0.0)
ops.node(2, 0.0, 0.0, 3.56)
ops.fix(1, 1, 1, 1, 1, 1, 1)

# Transformacion: vecxz=(1,0,0)
# local_x = (0,0,1) = global Z
# local_z = (1,0,0) = global X
# local_y = (0,-1,0) = -global Y
ops.geomTransf('Linear', 1, 1, 0, 0)

E = 27.8e6
A = 0.49
Iy = 0.020008
Iz = 0.020008
G = E / (2 * 1.2)
J = 0.05

ops.element('elasticBeamColumn', 1, 1, 2, E, A, Iy, Iz, G, J, 1)

# Carga: Fx=50 kN, Fz=-100 kN en nodo 2
ops.timeSeries('Linear', 1)
ops.pattern('Plain', 1, 1)
ops.load(2, 50.0, 0.0, -100.0, 0.0, 0.0, 0.0)

ops.system('BandSPD')
ops.numberer('RCM')
ops.constraints('Plain')
ops.integrator('LoadControl', 1.0)
ops.algorithm('Linear')
ops.analysis('Static')
ok = ops.analyze(1)
ops.reactions()

print("Nodo 1 coord: (0, 0, 0)")
print("Nodo 2 coord: (0, 0, 3.56)")
print("Carga en nodo 2: Fx=50, Fy=0, Fz=-100")
print("Transformacion: vecxz=(1,0,0)")
print("  local_x = global_Z = (0,0,1)")
print("  local_y = -global_Y = (0,-1,0)")
print("  local_z = global_X = (1,0,0)")
print()

# Reacciones
r = ops.nodeReaction(1)
print("Reaccion nodo 1 (global):")
print(f"  Fx={r[0]:.2f}, Fy={r[1]:.2f}, Fz={r[2]:.2f}")
print()

# Fuerza del elemento
f = ops.eleForce(1)
print("eleForce(1):")
print(f"  f[0]={f[0]:.2f}")
print(f"  f[1]={f[1]:.2f}")
print(f"  f[2]={f[2]:.2f}")
print(f"  f[3]={f[3]:.2f}")
print(f"  f[4]={f[4]:.2f}")
print(f"  f[5]={f[5]:.2f}")
print()

# Analisis manual
print("--- ANALISIS ---")
print("Si eleForce es GLOBAL: f = [Fx, Fy, Fz, Mx, My, Mz]")
print(f"  Esperado: f = [50.00, 0.00, 100.00, 0, 0, 0]")
print(f"  Real:     f = [{f[0]:.2f}, {f[1]:.2f}, {f[2]:.2f}, {f[3]:.2f}, {f[4]:.2f}, {f[5]:.2f}]")
print()
print("Si eleForce es LOCAL: f = [P, V2, V3, T, M2, M3]")
print("  P (local_x=global_Z) = 100.00 (compresion)")
print("  V2 (local_y=-global_Y) = 0.00")
print("  V3 (local_z=global_X) = 50.00 (cortante)")
print(f"  Esperado: f = [100.00, 0.00, 50.00, 0, 0, 0]")
print(f"  Real:     f = [{f[0]:.2f}, {f[1]:.2f}, {f[2]:.2f}, {f[3]:.2f}, {f[4]:.2f}, {f[5]:.2f}]")

ops.wipe()
