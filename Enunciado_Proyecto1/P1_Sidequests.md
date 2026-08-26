# P1 - Sidequests

## Sidequests del proyecto

Los sidequests son funcionalidades acotadas que pueden desarrollarse en paralelo y luego incorporarse al producto final.

No deben distraer del hito estructural principal de cada semana.

## SQ1 — Tributary Area Inspector

### Objetivo

Visualizar y editar áreas tributarias sobre una planta.

### Funciones deseables

- Elegir piso
- Mostrar vigas y columnas
- Seleccionar viga
- Crear polígono
- Editar vértices
- Mostrar área
- Asociar `q_G` o `q_Q`
- Calcular `q*A`
- Convertir a carga lineal
- Mostrar flechas/carga
- Exportar JSON

### Verificación

La carga transferida debe conservar la carga superficial total.

## SQ2 — Load Combination Explorer

### Objetivo

Explorar visualmente superposición.

### Controles

- `lambda_G`
- `lambda_Q`
- `lambda_EX`
- `lambda_EY`

### Resultados

- Deformada
- Reacciones
- Diagramas
- Demanda `P-M`

### Verificación

Comparar al menos una combinación arbitraria con una corrida OpenSees explícita.

## SQ3 — Section Capacity Explorer

### Objetivo

Visualizar capacidad no lineal y demanda.

### Debe mostrar

- Sección
- Refuerzo
- `M-phi`
- `P-M`
- Punto de demanda

## SQ4 — Carga móvil asociada al usuario

### Idea

Mientras el usuario se desplaza virtualmente por un piso, su posición representa una carga viva localizada idealizada.

```
posición del usuario
        |
        v
 panel / región tributaria
        |
        v
 vigas receptoras
        |
        v
 carga adicional
        |
        v
 respuesta estructural
```

### Alcance

El grupo debe definir una regla de transferencia simple y explícita.

Ejemplos:

- Toda la carga al sistema de vigas asociado a la región tributaria
- Reparto entre vigas del panel proporcional a distancias
- Otra regla defendible

### Qué se debe ver

- Posición del usuario
- Panel activo
- Vigas que reciben carga
- Magnitud asignada a cada viga
- Cambio de diagramas o valores de fuerzas

### Limitación

No corresponde a un análisis FE de losa. Es una herramienta didáctica de camino de carga idealizado.
