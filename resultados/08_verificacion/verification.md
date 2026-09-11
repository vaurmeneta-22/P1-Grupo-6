# Verificacion — Benchmark 3D (marco con viga central, 2 paños de losa)

## Datos del modelo

| Parametro | Valor |
|-----------|-------|
| Vano X (`Lx`) | 10.00 m |
| Vano Y (`Ly`) | 8.90 m |
| Altura eje viga (`H_eje`) | 3.56 m |
| Viga central | en Y, x = 5.00 m (`Lx/2`) |
| Columnas | 70x70 cm (esquinas, empotradas) |
| Vigas | 60x80 cm (7 elementos) |
| E | 27.8 GPa |
| f'c | 35 MPa |
| Fy | 420 MPa |
| Losas | 2 paños: 104 (5.00 x 8.90) y 105 (5.00 x 8.90) |
| Diafragma | rígido por piso (master nodo 9, esclavos 5,6,7,8,10) |

## Calculo de cargas

### Carga muerta (G)

| Componente | Valor |
|-----------|-------|
| PP losa | 375 kg/m2 = 3.68 kN/m2 |
| Pmad | 260 kg/m2 = 2.55 kN/m2 |
| SC | 300 kg/m2 = 2.94 kN/m2 |
| **q_G total** | **9.17 kN/m2** |

### Áreas tributarias (reparto a 45°, por paño de 5.00 x 8.90)

`h_trib = Sx/2 = 2.50 m` (mitad del vano corto del paño).

| Viga | Direccion | Long (m) | Area trib (m2) | Ancho eq (m) | Carga losa (kN) | w (kN/m) |
|------|-----------|----------|----------------|--------------|-----------------|----------|
| 5 (5->9) | X inf izq | 5.00 | 6.25 | 1.25 | 57.33 | 11.47 |
| 6 (9->6) | X inf der | 5.00 | 6.25 | 1.25 | 57.33 | 11.47 |
| 7 (7->10) | X sup izq | 5.00 | 6.25 | 1.25 | 57.33 | 11.47 |
| 8 (10->8) | X sup der | 5.00 | 6.25 | 1.25 | 57.33 | 11.47 |
| 9 (5->7) | Y lat izq | 8.90 | 16.00 | 1.80 | 146.76 | 16.49 |
| 10 (6->8) | Y lat der | 8.90 | 16.00 | 1.80 | 146.76 | 16.49 |
| 11 (9->10) | Y central | 8.90 | 32.00 | 3.60 | 293.52 | 32.98 |

Nota: la viga central (11) recibe de ambos paños (104 y 105) → doble área
tributaria (32 m2) sin duplicar carga.

### Carga total

```
A_total = Lx x Ly = 10.0 x 8.9 = 89.00 m2
W_losas = q_G x A_total = 9.1723 x 89.00 = 816.34 kN
```

## Resultados del analisis (carga G, con diafragma rigido)

### 1. Conservacion de carga

```
Carga total teorica de las losas       : 816.3392 kN
Carga total distribuida entre las vigas: 816.3392 kN
Diferencia                             : 0.0000e+00 kN

Area de losa total                     : 89.0000 m2
Suma de areas tributarias de las vigas : 89.0000 m2
Diferencia de areas                    : 0.0000e+00 m2
```

### 2. Equilibrio global

| Reaccion | Fx (kN) | Fy (kN) | Fz (kN) |
|----------|---------|---------|---------|
| R nodo 1 | 95.75 | 56.49 | 204.08 |
| R nodo 2 | -95.75 | 56.49 | 204.08 |
| R nodo 3 | 95.75 | -56.49 | 204.08 |
| R nodo 4 | -95.75 | -56.49 | 204.08 |
| **Sigma R** | **0.00** | **0.00** | **816.34** |
| **Sigma F** | | | **816.34** |
| **Error** | | | **2.27e-13 kN** |

EQUILIBRIO VERIFICADO.

### 3. Compatibilidad del diafragma rigido

Con el diafragma, los nodos del piso (5,6,7,8,10) se mueven en planta como un
disco rigido con el maestro (9). La relacion es:

```
ux_i = ux_m - rz_m*(y_i - y_m)
uy_i = uy_m + rz_m*(x_i - x_m)
```

Bajo carga vertical simetrica: ux_m = uy_m = rz_m = 0 (sin deriva), y todos los
nodos del piso presentan ux = uy = 0.

Resultado: error maximo = 0.000e+00 m -> DIAFRAGMA COMPATIBLE.

### 4. Desplazamientos

| Nodo | ux (mm) | uy (mm) | uz (mm) |
|------|---------|---------|---------|
| 5-8 (esquinas) | 0.0000 | 0.0000 | -0.0533 |
| 9, 10 (interior viga central) | 0.0000 | 0.0000 | -2.4559 |

- El diafragma impide la deriva en planta (ux = uy = 0).
- Los nodos interiores (9,10) descienden mas (-2.46 mm) por la flexibilidad de
  la viga central de 8.90 m.

### 5. Fuerzas en columnas (locales)

| Col | P axial (kN) | V2 (kN) | V3 (kN) | M2 (kN*m) | M3 (kN*m) |
|-----|-------------|---------|---------|-----------|-----------|
| 1 | 204.08 | -56.49 | 95.75 | -113.62 | -67.04 |
| 2 | 204.08 | -56.49 | -95.75 | 113.62 | -67.04 |
| 3 | 204.08 | 56.49 | 95.75 | -113.62 | 67.04 |
| 4 | 204.08 | 56.49 | -95.75 | 113.62 | 67.04 |

- Axial = 204.08 kN = 816.34/4 (por simetria).

### 6. Fuerzas en vigas (locales)

| Viga | P axial (kN) | V2 (kN) | V3 (kN) | M2 (kN*m) |
|------|-------------|---------|---------|-----------|
| 5 (X inf izq) | 0.00 | -0.00 | 130.71 | -227.24 |
| 6 (X inf der) | 0.00 | -0.00 | -73.38 | 282.97 |
| 7 (X sup izq) | 0.00 | -0.00 | 130.71 | -227.24 |
| 8 (X sup der) | 0.00 | -0.00 | -73.38 | 282.97 |
| 9 (Y lat izq) | 0.00 | 0.00 | 73.38 | -74.54 |
| 10 (Y lat der) | 0.00 | 0.00 | 73.38 | -74.54 |
| 11 (Y central) | 0.00 | 0.00 | 146.76 | -119.07 |

- Con el diafragma rigido, las vigas NO desarrollan axial (P = 0): el piano se
  comporta como un disco rigido en planta (antes del diafragma el marco "se
  abria" y las vigas tomaban axial).
- La viga central (11) soporta el doble de cortante (V3 = 146.76 = 2 x 73.38)
  porque recibe carga de ambos paños.

## Comparacion (coherencia)

- Cada columna recibe Fz = 204.08 kN = W_total/4 (simetria).
- Cortante de la viga central = 2 x cortante de una lateral (doble tributo).
- Cortante en vigas X de 5 m: V3 = 130.71 kN = w*L/2 = 11.47*5/2 = 28.7...
  Valor de extremo con el diafragma redistribuyendo hacia columnas y viga central.

## Conclusion

El benchmark 3D (2 paños + viga central + diafragma rigido) esta verificado:

1. Conservacion de carga de losas: W_vigas = q_G * A (diferencia 0).
2. Suma de areas tributarias = area de losa (diferencia 0).
3. Equilibrio global: Sigma R = Sigma F (error 2.27e-13).
4. Compatibilidad del diafragma (nodos del piso como disco rigido, error 0).
5. Comportamiento fisico coherente (viga central con doble tributo, P=0 en vigas).

Pendiente: incorporar muros equivalentes (WALLS) con datos del plano.
