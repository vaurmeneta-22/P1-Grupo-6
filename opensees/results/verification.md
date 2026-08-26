# Verificación — Benchmark 3D

## Datos del modelo

| Parámetro | Valor |
|-----------|-------|
| Vano X | 1000 cm |
| Vano Y | 890 cm |
| Altura eje viga | 356 cm |
| Columna | 70×70 cm |
| Viga | 60×80 cm |
| E | 27.8 GPa |
| f'c | 35 MPa |
| Fy | 420 MPa |

## Cálculo de cargas

### Carga muerta (G)

| Componente | Valor |
|-----------|-------|
| PP losa | 375 kg/m² = 3.68 kN/m² |
| Pmad | 260 kg/m² = 2.55 kN/m² |
| **q_G total** | **6.23 kN/m²** |

### Áreas tributarias

| Viga | Dirección | Ancho tributario | Carga lineal |
|------|-----------|-----------------|--------------|
| 5 (5→6) | X | 8.9/2 = 4.45 m | 27.72 kN/m |
| 6 (7→8) | X | 8.9/2 = 4.45 m | 27.72 kN/m |
| 7 (5→7) | Y | 10.0/2 = 5.00 m | 31.15 kN/m |
| 8 (6→8) | Y | 10.0/2 = 5.00 m | 31.15 kN/m |

### Carga total

```
F_total = q_G × Lx × Ly = 6.23 × 10.0 × 8.9 = 554.47 kN
```

## Verificaciones

### 1. Equilibrio: ΣR = ΣF

| Reacción | Valor |
|----------|-------|
| R_z nodo 1 | ? kN |
| R_z nodo 2 | ? kN |
| R_z nodo 3 | ? kN |
| R_z nodo 4 | ? kN |
| **ΣR** | **? kN** |
| **ΣF** | **554.47 kN** |
| **Error** | **? %** |

### 2. Desplazamientos

| Nodo | uy (mm) | uz (mm) |
|------|---------|---------|
| 5 | ? | ? |
| 6 | ? | ? |
| 7 | ? | ? |
| 8 | ? | ? |

### 3. Fuerzas en columnas

| Columna | Axial (kN) | My (kN·m) | Mz (kN·m) |
|---------|-----------|-----------|-----------|
| 1 (1→5) | ? | ? | ? |
| 2 (2→6) | ? | ? | ? |
| 3 (3→7) | ? | ? | ? |
| 4 (4→8) | ? | ? | ? |

### 4. Fuerzas en vigas

| Viga | Axial (kN) | Shear (kN) | My (kN·m) | Mz (kN·m) |
|------|-----------|-----------|-----------|-----------|
| 5 (5→6) | ? | ? | ? | ? |
| 6 (7→8) | ? | ? | ? | ? |
| 7 (5→7) | ? | ? | ? | ? |
| 8 (6→8) | ? | ? | ? | ? |

## Comparación con estimación manual

### Reacción por simetría

Por simetría, cada apoyo debería recibir aproximadamente:

```
R_aprox = F_total / 4 = 554.47 / 4 = 138.62 kN
```

### Momento en viga empotrada

Para una viga empotrada con carga uniforme:

```
M_max = w × L² / 12

Viga en X: M = 27.72 × 10² / 12 = 231.0 kN·m
Viga en Y: M = 31.15 × 8.9² / 12 = 204.4 kN·m
```

## Conclusión

[Completar después de ejecutar el benchmark]
