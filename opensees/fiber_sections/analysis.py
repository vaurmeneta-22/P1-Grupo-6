"""
Analisis inelasticos de seccion - Parte D  (Grupo 6)

Modelo estandar OpenSees "momento-curvatura":
  - una viga cantilever corta dispBeamColumn (1 elemento, 5 ptos Lobatto)
    con la seccion de fibras,
  - nodo base empotrado, nodo punta con rotacion controlada,
  - carga axial P constante aplicada en la punta,
  - DisplacementControl sobre la rotacion de punta: curvatura = theta / L.

Se obtienen:
  - M-phi : Momento (kN*m) vs curvatura (1/m) barriendo la rotacion.
  - P-M   : para una grilla de cargas axiales P se resuelve M-phi y se toma el
            momento maximo (capacidad) -- la envolvente dibuja la interaccion.

Unidades internas OpenSees: N, mm, MPa. Salida en kN, kN*m, 1/rad*? (1/m).
"""

import json
import math
import os
import sys

import openseespy.opensees as ops

from . import sections
from .materials import Materials, EPS_CU_UTIL

L_ELEM = 100.0        # mm, longitud del modelo mom-curvatura
NPTS = 5              # puntos Lobatto
MAX_STEPS = 10000
TOL_TEST = 1e-8


def _h_elem(section):
    """Altura en la direccion de flexion (mm) usada para la fibra extrema."""
    if section["tipo"] in ("columna", "columna_borde", "columna_id70"):
        return section["h"]
    return section["Lw"]


def _modelo_fibra(section, sec_tag=100):
    """Crea el modelo cantilever de 1 elemento dispBeamColumn con la seccion
    de fibras (mismo setup que mom_curv). Devuelve el tag del nodo libre (2)."""
    ops.wipe()
    ops.model("basic", "-ndm", 2, "-ndf", 3)
    Materials().build()
    sections.build(section, 1, 2, sec_tag)     # mats 1 (concat) y 2 (acero)

    ops.node(1, 0.0, 0.0)
    ops.node(2, L_ELEM, 0.0)
    ops.fix(1, 1, 1, 1)

    ops.geomTransf("Linear", 1)
    ops.beamIntegration("Lobatto", 1, sec_tag, NPTS)
    ops.element("dispBeamColumn", 1, 1, 2, 1, 1)
    return 2


def _axial_pura_comp(section, dStep=0.001, max_steps=6000):
    """Capacidad axial pura (compresion +, kN) de la seccion de fibras.

    Aplica desplazamiento axial creciente (control de desplazamiento sobre el
    nodo libre en la direccion del eje) y registra N vs eps_centro hasta bien
    pasada la deformacion ultima de compresion. Devuelve el PICO (maximo N),
    que es el punto de cierre superior de la interaccion P-M (M -> 0).
    Referencia de carga axial 1 N para inicializar el DisplacementControl."""
    nodo = _modelo_fibra(section)
    ops.timeSeries("Constant", 1)
    ops.pattern("Plain", 1, 1)
    ops.load(nodo, -1.0, 0.0, 0.0)              # carga de referencia 1 N
    ops.constraints("Plain")
    ops.numberer("RCM")
    ops.system("BandGeneral")
    ops.test("NormDispIncr", TOL_TEST, 400)
    ops.algorithm("Newton")
    ops.integrator("LoadControl", 1.0, 1, 1.0, 1.0)
    ops.analysis("Static")
    try:
        ops.analyze(1)
    except ops.OpenSeesError:
        pass
    ops.loadConst("-time", 0.0)                 # congela -> carga de referencia
    ops.integrator("DisplacementControl", nodo, 1, -dStep)
    ops.analysis("Static")

    N_pico = 0.0
    for _ in range(max_steps):
        try:
            rc = ops.analyze(1)
        except ops.OpenSeesError:
            break
        if rc != 0:
            break
        fe = ops.eleResponse(1, "forces")
        bd = ops.eleResponse(1, "basicDeformation")
        try:
            eps0 = float(bd[0]) / L_ELEM
        except (TypeError, IndexError, ValueError):
            eps0 = 0.0
        N = float(fe[0]) / 1000.0               # kN (compresion +; fe[0]>0 en comp)
        N_pico = max(N_pico, N)
        if eps0 <= -1.5 * EPS_CU_UTIL:           # suficientemente pasado falla
            break
    try:
        ops.wipe()
    except Exception:
        pass
    return N_pico


def axial_pura(section):
    """Capacidades axiales puras de la seccion de fibras:
       (P_comp_kN, P_trac_kN)

    P_comp: pico de compresion pura (cierra la interaccion en su punta
    superior, M -> 0), del modelo de fibras.
    P_trac: punto de traccion (toda el acero longitudinal fluyendo, concreto
    fisurado), = fy * As_total (kN); cierra la punta inferior de la curva.
    """
    P_comp = _axial_pura_comp(section)
    Pt = Materials().fy * sections.area_acero(section) / 1000.0  # kN
    return P_comp, Pt


def mom_curv(section, P=0.0, dPhi=6e-7, max_steps=MAX_STEPS):
    """Curva M-phi de una seccion con carga axial P (N, compresion +).

    Detiene el analisis cuando la fibra extrema comprimida de concreto alcanza
    eps_cu (falla por compresion, seccion plana: eps = eps_centro + phi*y).
    Devuelve (phi_list[1/m], M_list[kN*m], n_ok).

    Si la carga axial P no se puede sostener (P > capacidad pura de la seccion)
    la carga no converge y se devuelve una curva VACIA: la interaccion P-M
    descarta ese nivel de P en vez de reportar un momento espurio.
    """
    phi, M = [], []
    sec_tag = 100
    h = _h_elem(section)
    nodo = _modelo_fibra(section, sec_tag)

    # Paso 1: carga axial P (patron constante), el resto queda sin cargar.
    ops.timeSeries("Constant", 1)
    ops.pattern("Plain", 1, 1)
    # referencia minima para no quedar en cero si P==0
    P_apl = max(P, 1.0)
    ops.load(nodo, -P_apl, 0.0, 0.0)
    ops.constraints("Plain")
    ops.numberer("RCM")
    ops.system("BandGeneral")
    ops.test("NormDispIncr", TOL_TEST, 200)
    ops.algorithm("Newton")
    ops.integrator("LoadControl", 1.0, 1, 1.0, 1.0)
    ops.analysis("Static")
    try:
        rc_axial = ops.analyze(1)
    except ops.OpenSeesError:
        rc_axial = -99
    if rc_axial != 0:
        # P insostenible (compresion pura superada): sin curva valida.
        try:
            ops.wipe()
        except Exception:
            pass
        return [], [], 0
    # congelar la carga axial; el momento pasa a ser el patron de referencia
    ops.loadConst("-time", 0.0)
    ops.timeSeries("Linear", 2)
    ops.pattern("Plain", 2, 2)
    ops.load(nodo, 0.0, 0.0, 1.0)          # momento unitario de referencia

    ops.integrator("DisplacementControl", nodo, 3, dPhi)
    ops.analysis("Static")

    n_ok = 0
    for _ in range(max_steps):
        try:
            rc = ops.analyze(1)
        except ops.OpenSeesError:
            break
        if rc != 0:
            break
        n_ok += 1
        theta = ops.nodeDisp(nodo, 3)                  # rad
        fe = ops.eleResponse(1, "forces")
        M_base = float(fe[2])                       # momento en nodo 1 (N*mm)
        # deformacion axial de la seccion en el c.g.: bd[0] es la elongacion
        # axial del elemento (mm), eps0 = bd[0] / L
        bd = ops.eleResponse(1, "basicDeformation")
        try:
            eps0 = float(bd[0]) / L_ELEM
        except (TypeError, IndexError, ValueError):
            eps0 = 0.0
        # curvatura de la seccion (lineal): phi = theta / L   [1/mm]
        cur = theta / L_ELEM
        # fibra mas comprimida: y = -h/2 en direccion de la curvatura
        eps_ext = eps0 - cur * (h / 2.0)
        phi.append(theta * 1000.0 / L_ELEM)         # . rad/mm -> 1/m
        M.append(-M_base / 1e6)                     # kN*m
        if eps_ext <= -EPS_CU_UTIL:                 # falla por concreto
            break
    try:
        ops.wipe()
    except Exception:
        pass
    return phi, M, n_ok


def pm_interaction(section, P_grid, dPhi=5e-7, max_steps=MAX_STEPS,
                   verbose=False):
    """Curva P-M: para cada P de la grilla (kN, compresion +) resuelve M-phi y
    toma el momento de falla (fibra extrema en eps_cu). Devuelve (P_kN, M_kNm)."""
    P_kN, M_kNm = [], []
    for Pc in P_grid:
        phi, M, n_ok = mom_curv(section, P=Pc * 1000.0, dPhi=dPhi,
                                max_steps=max_steps)
        if not M:
            if verbose:
                print(f"  P={Pc:9.1f} kN: sin convergencia")
            continue
        # Capacidad a flexion para este P = maximo de la curva M-phi (pico de la
        # seccion ya plastificada), acumulado hasta el corte por concreto.
        Mf = abs(max(M, key=abs))
        P_kN.append(Pc)
        M_kNm.append(Mf)
        if verbose:
            print(f"  P={Pc:9.1f} kN -> Mfalla={Mf:10.2f} kN*m  "
                  f"(n={n_ok})")
    return P_kN, M_kNm


def pm_completa(section, fracs=None, dPhi=5e-7, max_steps=MAX_STEPS,
                verbose=False):
    """Curva P-M COMPLETA de una seccion (lonjas, puntas cerradas):
       [(-Pt,0), ..., P_max(fibra), (Pcap_comp,0)]

    - Calcula la capacidad axial pura de compresion de la SECCION DE FIBRAS
      (pico de la curva N-eps del modelo, no el ACI 0.85*f'c*Ag que subestima).
    - Grilla proporcional a esa capacidad hasta ~0.98*Pcap (los puntos no
      sostenibles los descarta mom_curv devolviendo curva vacia).
    - Cierra la punta inferior en (-Pt, 0), con Pt = fy * As_total.
    - Cierra la punta superior en (Pcap_comp, 0).

    Devuelve (P_kN, M_kNm) con P en kN (compresion +), M en kN*m.
    """
    Pcap, Pt = axial_pura(section)
    if fracs is None:
        fracs = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8,
                 0.85, 0.9, 0.93, 0.95, 0.97, 0.98, 0.99]
    grid = [Pcap * f for f in fracs]
    P, M = pm_interaction(section, grid, dPhi=dPhi, max_steps=max_steps,
                          verbose=verbose)
    P_out = [-round(Pt, 1)] + list(P)
    M_out = [0.0] + list(M)
    if P_out and P_out[-1] < Pcap:
        P_out = P_out + [round(Pcap, 1)]
        M_out = M_out + [0.0]
    return P_out, M_out


def esfuerzos_mom_curv(section, P=0.0, dPhi=5e-7, max_steps=MAX_STEPS):
    """Wrapper que ademas devuelve la columna de esfuerzos (para graficos)."""
    phi, M, n = mom_curv(section, P, dPhi, max_steps)
    return phi, M


def guardar(section, P, M, raiz="figures", nombre="curva"):
    """Guarda P-M o M-phi en un JSON bajo la raiz dada."""
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "..", "figures") if raiz == "figures" else raiz
    out = os.path.abspath(out)
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, f"{section['nombre']}_{nombre}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"section": section["nombre"],
                   "P_kN": P, "M_kNm": M,
                   "codigo": "Parte D - fiber_sections (OpenSees)"}, f, indent=1)
    return path