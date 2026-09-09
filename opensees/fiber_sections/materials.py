"""
Materiales de la Parte D - Fiber Sections  (Grupo 6)

Valores tomados de data/materials.json del proyecto:
  concreto  f'c = 35 MPa,  E = 27800 MPa
  acero     fy  = 420 MPa, E = 200000 MPa

Todos los esfuerzos y modulos en MPa (N/mm2), longitudes en mm, fuerzas en N,
momentos en N*mm (se convierten a kN-m en la capa de resultados).
"""

import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(REPO, "data", "materials.json")


def _load():
    with open(DATA, "r", encoding="utf-8") as f:
        return json.load(f)


class Materials:
    """Define los materiales OpenSees en MPa (negativos en compresion).

    Convenios OpenSees:
      Concrete02(tag, fpc, epsc0, fpcu, epsU, lambda, ft, Ets)
        fpc<0 pico compresion, epsc0<0 deformacion pico,
        fpcu<0 resistencia residual, epsU<0 deformacion ultima.
      Steel01(tag, fy, E, b)  ->  respuesta bilineal con beta de endurecimiento.
    """

    def __init__(self):
        raw = _load()
        self.f_c = raw["concrete"]["f_c"]          # 35 MPa
        self.E_c = raw["concrete"]["E"]            # 27800 MPa
        self.fy = raw["steel"]["fy"]               # 420 MPa
        self.E_s = raw["steel"]["E"]               # 200000 MPa

        # parametros de forma del concreto (ACI / NCh)
        self.eps_c0 = -0.002                       # deformacion en f'c
        self.eps_cu = -0.0035                      # deformacion ultima (concreto sin confinar)
        self.residual = 0.2                        # fraccion de fpc que conserva (post-pico)
        self.ft = 2.9                              # resist. a traccion (MPa), aproximada
        self.Ets = 0.1 * self.E_c                  # pendiente softening traccion

        # acero
        self.beta_steel = 0.005                    # endurecimiento post-fluencia

    def fc(self):
        """Crea el material de concreto en el modelo. Tag fijo 1."""
        import openseespy.opensees as ops
        fpc = -self.f_c
        fpcu = -self.residual * self.f_c
        ops.uniaxialMaterial("Concrete02", 1,
                             fpc, self.eps_c0, fpcu, self.eps_cu,
                             0.8, self.ft, self.Ets)

    def steel(self):
        """Crea el material de acero en el modelo. Tag fijo 2."""
        import openseespy.opensees as ops
        ops.uniaxialMaterial("Steel01", 2,
                             self.fy, self.E_s, self.beta_steel)

    def build(self):
        """Crea ambos materiales en el modelo (tags 1 y 2)."""
        self.fc()
        self.steel()


# deformacion de falla por compresion del concreto (magnitud, positiva).
# igual a eps_cu en valor absoluto: la fibra extrema comprimida se agota.
EPS_CU_UTIL = 0.0035


MAT_COL = 1   # concreto
MAT_AC = 2    # acero