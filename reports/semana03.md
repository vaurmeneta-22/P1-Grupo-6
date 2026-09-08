# Semana 3 — Partes A (Q) y B (EX/EY)

## Resumen
Implementación de carga viva independiente `Q` y casos sísmicos pseudoestáticos `EX`/`EY` sobre el modelo OpenSeesPy existente de la Semana 2.

## Resultados

### Caso G (referencia, sin cambios)
- Peso propio: 41967.86 kN
- Losa tributaria: 31276.11 kN
- Total: 73243.97 kN
- Equilibrio: OK (err=1.589e-15)

### Caso Q (carga viva)
- Carga transferida a vigas: 11349.40 kN (301 vigas)
- q_Q = 2.00 kN/m², A_total = 5676.96 m²
- Q teórica = 11353.91 kN
- Error de conservación: 0.04% (REVISAR --redondeo tributario)
- Equilibrio: OK (err=3.205e-16)

### Casos Sísmicos (EX/EY)
- α_sismo = 0.20, fracción Q = 50%, g = 9.81 m/s²

| Piso | G (kN) | Q (kN) | W_sismico (kN) | masa (t) | F (kN) | master |
|------|--------|--------|----------------|----------|--------|--------|
| 1 | 6541.68 | 1253.07 | 7168.21 | 730.7 | 1433.64 | 186 |
| 2 | 10460.19 | 2283.79 | 11602.09 | 1182.7 | 2320.42 | 29 |
| 3 | 11100.54 | 2494.49 | 12347.78 | 1258.7 | 2469.56 | 78 |
| 4 | 22587.26 | 5322.57 | 25248.55 | 2573.8 | 5049.71 | 146 |

**F_total = 11273.33 kN** (suma de fuerzas por piso)

#### EX (carga en +X)
- Corte basal medido: -11273.33 kN (OK, err=3.2e-15)
- Desplazamiento CM por piso: 0.13, 0.70, 1.56, 3.52 mm (+X)
- Rotación Rz: 1.35e-5, 4.09e-5, 7.87e-5, 1.50e-4 rad

#### EY (carga en +Y)
- Corte basal medido: -11273.33 kN (OK, err=2.2e-14)
- Desplazamiento CM por piso: 1.60, 4.21, 10.36, 22.46 mm (+Y)
- Rotación Rz: -3.52e-6, -1.88e-5, -8.62e-5, -2.54e-4 rad

## Auditorías

### Q (Parte A)
| Verificación | Resultado |
|-------------|-----------|
| Conservación ΣQ = q_Q·A | 0.04% error (REVISAR) |
| Equilibrio vertical | OK |
| Diafragma rígido | OK |

### Sismo EX/EY (Parte B)
| Verificación | EX | EY |
|-------------|-----|-----|
| ΣF = F_lateral | OK | OK |
| Corte basal = -F | OK | OK |
| Deformada sentido correcto (+X/+Y) | OK | OK |
| Torsión Rz (esperada por asimetría) | Presente | Presente |

## Parámetros a confirmar con profesor
1. **α_sismo = 0.20** — valor asumido, pendiente de confirmación
2. **q_Q = 2.00 kN/m²** — Sobrecarga uniforme del contrato
3. **Fracción de carga viva en masa sísmica = 50%** — valor estándar ACI/NSR-10
4. **Error de conservación Q = 0.04%** — debido a redondeo en áreas tributarias (aceptable < 1%)

## Archivos modificados
- `opensees/opensees_edificio_v2.py` — casos G/Q/EX/EY, auditorías, masa sísmica
- `reports/semana03.md` — este reporte

## Comando de ejecución
```bash
# Todos los casos
python opensees_edificio_v2.py

# Caso individual
python opensees_edificio_v2.py --case G
python opensees_edificio_v2.py --case Q
python opensees_edificio_v2.py --case EX
python opensees_edificio_v2.py --case EY
```

## Pendiente (Semana 3, Partes C y D)
- Parte C: Superposición R = λ_G·R_G + λ_Q·R_Q + λ_EX·R_EX + λ_EY·R_EY
- Parte D: Fiber sections para M-φ y P-M (análisis de capacidad RC)
