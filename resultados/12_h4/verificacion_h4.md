H4 — Verificación de reanálisis OpenSees

Fecha: 2026-10-06T01:53:36-03:00
Modelo: Caso B · Apoyo articulado en nodo 1

| Requisito | Estado | Evidencia |
|---|---|---|
| Modelo válido | APROBADO | El edificio tiene 536 nodos y 722 elementos; el apoyo del nodo 1 está articulado. También se comprobó que rechace una entrada estructural inválida. |
| Errores controlados | APROBADO | Se provocaron dos errores de prueba y ambos fueron detectados. El código 1 significa que se rechazó correctamente el archivo faltante; no es un fallo del análisis. |
| Backend preparó resultados | APROBADO | Python/OpenSees calculó los cinco escenarios para Caso B · Apoyo articulado en nodo 1 y preparó el modelo y el mapa para Unity. |
| Mismos resultados | APROBADO | Se comparó cada escenario con OpenSees ejecutado directamente. La mayor diferencia encontrada fue 0; dentro del límite aceptado. |
| Cálculo repetible | APROBADO | Se repitió el análisis con los mismos datos. La mayor diferencia fue 0; las corridas coinciden dentro del límite aceptado. |

Comparación numérica entre campos exportados por OpenSees: fuerzas de elementos, desplazamientos, reacciones, resumen y verificaciones.
Tolerancia: abs ≤ 1.0e-08 + rel ≤ 1.0e-09 × escala.

OpenSees se ejecutó en el backend local y se comparó con corridas directas.
