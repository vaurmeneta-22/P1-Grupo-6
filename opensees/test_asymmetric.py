# -*- coding: utf-8 -*-
"""
Prueba: verificar que vigas reportan fuerzas con carga asimetrica.
Solo carga en viga X (5->6), sin carga en viga X (7->8).
"""

import openseespy.opensees as ops
import math

ops.wipe()
ops.model('basic', '-ndm', 3, '-ndf', 6)

Lx = 10.0
Ly = 8.9
H = 3.56

# Nodos
ops.node(1, 0, 0, 0)
ops.node(2, Lx, 0, 0)
ops.node(3, 0, Ly, 0)
ops.node(4, Lx, Ly, 0)
ops.node(5, 0, 0, H)
ops.node(6, Lx, 0, H)
ops.node(7, 0, Ly, H)
ops.node(8, Lx, Ly, H)

for i in [1,2,3,4]:
    ops.fix(i, 1, 1, 1, 1, 1, 1)

# Transformaciones
ops.geomTransf('Linear', 1, 1, 0, 0)
ops.geomTransf('Linear', 2, 0, 0, 1)

E = 27.8e6
A_c = 0.49; Iy_c = 0.020008; Iz_c = 0.020008; G_c = E/2.4; J_c = 0.05
A_b = 0.48; Iy_b = 0.0256; Iz_b = 0.0144; G_b = E/2.4; J_b = 0.064

# Elementos
ops.element('elasticBeamColumn', 1, 1, 5, E, A_c, Iy_c, Iz_c, G_c, J_c, 1)
ops.element('elasticBeamColumn', 2, 2, 6, E, A_c, Iy_c, Iz_c, G_c, J_c, 1)
ops.element('elasticBeamColumn', 3, 3, 7, E, A_c, Iy_c, Iz_c, G_c, J_c, 1)
ops.element('elasticBeamColumn', 4, 4, 8, E, A_c, Iy_c, Iz_c, G_c, J_c, 1)
ops.element('elasticBeamColumn', 5, 5, 6, E, A_b, Iy_b, Iz_b, G_b, J_b, 2)
ops.element('elasticBeamColumn', 6, 7, 8, E, A_b, Iy_b, Iz_b, G_b, J_b, 2)
ops.element('elasticBeamColumn', 7, 5, 7, E, A_b, Iy_b, Iz_b, G_b, J_b, 2)
ops.element('elasticBeamColumn', 8, 6, 8, E, A_b, Iy_b, Iz_b, G_b, J_b, 2)

# Carga: solo en viga X del lado Y=0 (nodos 5 y 6)
# w = 27.72 kN/m, F = 138.6 kN por nodo
F = 138.6

ops.timeSeries('Linear', 1)
ops.pattern('Plain', 1, 1)
ops.load(5, 0, 0, -F, 0, 0, 0)
ops.load(6, 0, 0, -F, 0, 0, 0)
# Sin carga en nodos 7 y 8

ops.system('BandSPD')
ops.numberer('RCM')
ops.constraints('Plain')
ops.integrator('LoadControl', 1.0)
ops.algorithm('Linear')
ops.analysis('Static')
ok = ops.analyze(1)
ops.reactions()

print("Carga asimetrica: solo en viga 5 (nodos 5,6)")
print(f"F por nodo = {F} kN")
print()

# Ejes locales para vigas
def get_local_axes(i_node, j_node, vecxz):
    xi, yi, zi = ops.nodeCoord(i_node)
    xj, yj, zj = ops.nodeCoord(j_node)
    dx, dy, dz = xj-xi, yj-yi, zj-zi
    L = math.sqrt(dx*dx+dy*dy+dz*dz)
    lx = (dx/L, dy/L, dz/L)
    vx, vy, vz = vecxz
    dot = vx*lx[0]+vy*lx[1]+vz*lx[2]
    lz = (vx-dot*lx[0], vy-dot*lx[1], vz-dot*lx[2])
    m = math.sqrt(lz[0]**2+lz[1]**2+lz[2]**2)
    lz = (lz[0]/m, lz[1]/m, lz[2]/m)
    ly = (lz[1]*lx[2]-lz[2]*lx[1], lz[2]*lx[0]-lz[0]*lx[2], lz[0]*lx[1]-lz[1]*lx[0])
    return lx, ly, lz

def g2l(fg, lx, ly, lz):
    R = [lx, ly, lz]
    fl = [0.0]*6
    for i in range(3):
        for j in range(3):
            fl[i] += R[i][j]*fg[j]
            fl[i+3] += R[i][j]*fg[j+3]
    return fl

# Vigas en X: T2, vecxz=(0,0,1)
# local_x = along X, local_y = (0,-1,0)?, local_z = (0,0,1)
for eid in [5, 6, 7, 8]:
    ed = {5:(5,6), 6:(7,8), 7:(5,7), 8:(6,8)}
    vxz = (0,0,1)
    lx, ly, lz = get_local_axes(ed[eid][0], ed[eid][1], vxz)
    fg = list(ops.eleForce(eid))
    fl = g2l(fg, lx, ly, lz)
    P,V2,V3,T,M2,M3 = fl
    print(f"Viga {eid}: P={P:.2f}, V2={V2:.2f}, V3={V3:.2f}, M2={M2:.2f}, M3={M3:.2f}")

print()
# Reacciones
R_total = 0
for i in [1,2,3,4]:
    r = ops.nodeReaction(i)
    R_total += r[2]
    print(f"R nodo {i}: Fz={r[2]:.2f}")
print(f"Suma R = {R_total:.2f}, Carga = {2*F:.2f}")

ops.wipe()
