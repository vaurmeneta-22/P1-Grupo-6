# Verificacion — Benchmark 3D

## Datos del modelo

| Parametro | Valor |
|-----------|-------|
| Vano X | 1000 cm |
| Vano Y | 890 cm |
| Altura eje viga | 356 cm |
| Columna | 70x70 cm |
| Viga | 60x80 cm |
| E | 27.8 GPa |
| f'c | 35 MPa |
| Fy | 420 MPa |

## Calculo de cargas

### Carga muerta (G)

| Componente | Valor |
|-----------|-------|
| PP losa | 375 kg/m2 = 3.68 kN/m2 |
| Pmad | 260 kg/m2 = 2.55 kN/m2 |
| **q_G total** | **6.23 kN/m2** |

### Carga sobrecarga (SC)

| Componente | Valor |
|-----------|-------|
| SC | 300 kg/m2 = 2.94 kN/m2 |

### Areas tributarias

Losa unidireccional en Y, apoyada en vigas X.

| Viga | Direccion | Ancho tributario | Carga lineal |
|------|-----------|-----------------|--------------|
| 5 (5->6) | X | 8.9/2 = 4.45 m | 27.72 kN/m |
| 6 (7->8) | X | 8.9/2 = 4.45 m | 27.72 kN/m |
| 7 (5->7) | Y | No recibe carga de losa | 0 kN/m |
| 8 (6->8) | Y | No recibe carga de losa | 0 kN/m |

### Carga total

```
F_total = q_G x Lx x Ly = 6.23 x 10.0 x 8.9 = 554.41 kN
```

### Aplicacion de cargas

Cargas distribuidas via `eleLoad -beamUniform` en elementos 5 y 6.
Transformacion T2: vecxz=(0,0,1), local_z = global_Z.

```
ops.eleLoad('-ele', 5, '-type', '-beamUniform', 0.0, -w_G)
ops.eleLoad('-ele', 6, '-type', '-beamUniform', 0.0, -w_G)
```

## Resultados del analisis

### 1. Equilibrio: SigmaR = SigmaF

| Reaccion | Fx (kN) | Fy (kN) | Fz (kN) |
|----------|---------|---------|---------|
| R nodo 1 | 68.82 | 0.00 | 138.60 |
| R nodo 2 | -68.82 | 0.00 | 138.60 |
| R nodo 3 | 68.82 | 0.00 | 138.60 |
| R nodo 4 | -68.82 | 0.00 | 138.60 |
| **Sigma R** | **0.00** | **0.00** | **554.41** |
| **Sigma F** | | | **554.41** |
| **Error** | | | **1.14e-13 kN** |

EQUILIBRIO VERIFICADO.

### 2. Desplazamientos

| Nodo | ux (mm) | uy (mm) | uz (mm) |
|------|---------|---------|---------|
| 5 | 0.0258 | 0.0000 | -0.0362 |
| 6 | -0.0258 | 0.0000 | -0.0362 |
| 7 | 0.0258 | 0.0000 | -0.0362 |
| 8 | -0.0258 | 0.0000 | -0.0362 |

- Desplazamiento vertical uniforme: uz = -0.0362 mm
- Desplazamiento horizontal: ux = +/-0.0258 mm (apertura del marco)
- Simetria verificada: cargas y geometria simetricas

### 3. Fuerzas en columnas (coordenadas locales)

Convencion local:
- local_x = eje de la columna (vertical)
- local_y = -Y global
- local_z = X global

| Col | P axial (kN) | V2 cortante (kN) | V3 cortante (kN) | M2 momento (kN*m) |
|-----|-------------|------------------|------------------|-------------------|
| 1 (1->5) | 138.60 | 0.00 | 68.82 | -58.57 |
| 2 (2->6) | 138.60 | 0.00 | -68.82 | 58.57 |
| 3 (3->7) | 138.60 | 0.00 | 68.82 | -58.57 |
| 4 (4->8) | 138.60 | 0.00 | -68.82 | 58.57 |

- Axial: cada columna recibe 138.60 kN (compresion) = 554.41/4
- Cortante V3: +/-68.82 kN por accion de marco
- Momento M2: +/-58.57 kN*m en base de columna

### 4. Fuerzas en vigas (coordenadas locales)

Convencion local:
- local_x = eje de la viga
- local_y = Y global (o -Y segun sentido)
- local_z = Z global

| Viga | P axial (kN) | V2 cortante (kN) | V3 cortante (kN) | M2 momento (kN*m) |
|------|-------------|------------------|------------------|-------------------|
| 5 (5->6) | 68.82 | 0.00 | 138.60 | -186.42 |
| 6 (7->8) | 68.82 | 0.00 | 138.60 | -186.42 |
| 7 (5->7) | 0.00 | 0.00 | 0.00 | 0.00 |
| 8 (6->8) | 0.00 | 0.00 | 0.00 | 0.00 |

- Vigas X (5,6): reciben carga de losa, tienen P, V y M
- Vigas Y (7,8): no reciben carga de losa (losa unidireccional en Y)
- Momento M2 = -186.42 kN*m (extremo de viga)

## Comparacion con estimacion manual

### Reaccion por simetria

```
R_vertical = F_total / 4 = 554.41 / 4 = 138.60 kN  [CORRECTO]
```

### Momento en viga fija-empotrada (referencia)

Para una viga empotrada en ambos extremos con carga uniforme:

```
M_emp = w x L^2 / 12 = 27.72 x 10^2 / 12 = 231.0 kN*m
```

El momento del modelo (186.42 kN*m) es menor que el de viga fija-empotrada (231.0 kN*m) porque los extremos no son perfectamente empotrados: las columnas proporcionan rigidez rotacional finita, no infinita. Esto es consistente con el comportamiento esperado de un marco.

### Cortante en viga

```
V_teoria = w x L / 2 = 27.72 x 10 / 2 = 138.60 kN  [CORRECTO]
```

El cortante en el extremo de la viga (138.60 kN) coincide exactamente con la teoria.

## Conclusion

El benchmark 3D esta verificado:
1. Equilibrio global: SigmaR = SigmaF (error < 1e-10)
2. Simetria: resultados simetricos para carga y geometria simetricas
3. Fuerzas coherentes: axial en columnas = F_total/4, cortante en vigas = wL/2
4. Momentos razonables: menor que viga fija-empotrada (comportamiento de marco)
5. Desplazamientos pequenos y simetricos

Modelo listo para semanas siguientes (combos de carga,振型 modos, etc.)
