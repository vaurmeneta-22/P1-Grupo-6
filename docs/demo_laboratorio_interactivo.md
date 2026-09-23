# Demostración del laboratorio interactivo

## Estado de este avance

El viewer principal es Unity. Se añadieron cuatro sliders G, Q, EX, EY en
ANÁLISIS. Modifican COMBO en memoria, conservando los casos base del JSON.
La deformada, fuerzas de extremo, reacciones, diagramas y punto P-M se calculan
con la misma combinación. El visor HTML todavía no incorpora estos sliders.

La implementación C# compila con las referencias del proyecto Unity 6000.6.0f1.
La prueba `tests/test_viewer_combination.ps1` ejecuta el parser y motor C# reales
con el mapa exportado: siete combinaciones, incluyendo cero, cada caso aislado
y sismo negativo; tolerancia absoluta 1e-10 en componentes exportadas.
También comprueba que los desplazamientos base no cambian y que un caso ausente
no publica resultados parciales. Esto verifica la combinación en el viewer;
no reemplaza el contraste con un análisis OpenSees independiente.

Resultado en esta sesión: **147 945 comprobaciones C# aprobadas por mapa**,
tanto para la línea base como para StreamingAssets (Mod A). Compilación completa
de scripts aprobada; queda una advertencia previa sobre `FindObjectsOfType`.
La suite Python se re-ejecutó en el cierre: `python -m pytest tests -q` →
**35 passed** (OpenSeesPy 3.8.0.0 disponible). El reanálisis OpenSees no se
re-ejecutó; permanecen las corridas de semanas anteriores en `resultados/`.
El harness compila los fuentes C# reales con el compilador de .NET disponible en
la máquina (`Add-Type` de PowerShell 5.1), por lo que el parser `MiniJson.cs` y
el motor `AnalysisMapCombination.cs` evitan sintaxis posterior a C# 5; Unity los
compila igual con su compilador moderno.

**Pendiente de validación humana:** Play Mode, tiempo de respuesta al arrastrar,
legibilidad del panel con scroll y demostración en el dispositivo final.
SQ4 sigue como propuesta; no se presenta como implementado.

## Guion en vivo (6–8 minutos)

1. Abrir el proyecto `Unity` y entrar a Play. Orbitar, hacer zoom y seleccionar
   una viga. Identificar tag, sección y nodos. Encender/apagar capas.
2. Entrar a ANÁLISIS, vista DEF. Mostrar G, Q, EX, EY y COMBO.
3. Pulsar **Cero**: desplazamientos, fuerzas y demanda deben ser cero.
   La geometría sigue visible. La curva de capacidad no cambia.
4. Dejar G=1 y los otros factores en cero. Comparar con el botón de caso G.
   Repetir con EX=1 y después EX=-1: se invierten las componentes firmadas.
5. Pulsar **G + Q**. Abrir una viga con doble clic y arrastrar Q.
   La tabla del elemento debe actualizarse sin cerrar la ficha.
6. Abrir una columna o muro de hormigón con doble clic. Mover EX/EY y observar
   el punto de demanda P-M. La capacidad se mantiene porque no cambió la sección.
   El visor conserva su criterio existente de demanda y curva: explicar sus
   convenciones y no interpretar esta visualización como verificación biaxial completa.
7. Cambiar a M/N/V y activar reacciones. En DATOS, elegir COMBO para consultar
   diagramas y reacciones de los sliders (las pestañas tienen selector propio).
8. Demostrar las dos modificaciones siguientes y explicar por qué requieren
   reanálisis. Comparar el elemento 147 para sección y nodo 1 para apoyo.

## Dos modificaciones reproducibles ya disponibles

Ejecutar desde la raíz del repositorio con Python y OpenSeesPy instalados.
Detener Play antes de sincronizar archivos; volver a Play después de cada variante.

```powershell
python scripts/generar_modificaciones.py
python scripts/ejecutar_modificacion.py --tag modA --json Edificio_mod_A.json --element 147 --all-cases --combo-lambdas 1.2,1.0,1.4,1.4 --unity
python scripts/ejecutar_modificacion.py --tag modB --json Edificio_mod_B.json --element 1 --all-cases --combo-lambdas 1.2,1.0,1.4,1.4 --unity
python scripts/ejecutar_modificacion.py --restore
```

- **Mod A:** sección de viga 147, 60×80 a 50×75 cm. Cambian rigidez y peso propio.
- **Mod B:** nodo 1, empotramiento a articulación. Cambian condiciones de borde.

Ambas regeneran resultados etiquetados y sincronizan contrato y mapa del mismo
modelo. La copia de StreamingAssets encontrada al iniciar este avance era Mod A.
El comando `--restore` recupera los archivos base; no se ejecutó automáticamente.
No mezclar G de una variante con Q/EX/EY de otra.

| Cambio | ¿Reanálisis? | Explicación |
|---|---|---|
| Factores λ sobre casos existentes | No | Misma rigidez y patrones; suma lineal de respuestas |
| Intensidad de un patrón idéntico y masa fija | No, puede escalarse | Válido sólo bajo las hipótesis lineales del modelo |
| G/Q físico que cambia masa sísmica | Sí para actualizar EX/EY | La masa depende de G + 0.50 Q |
| Sección, apoyo, material, conectividad | Sí | Cambia el sistema estructural |
| Área tributaria o carga móvil localizada | Sí, o casos de influencia previamente calculados | Cambia el patrón espacial |

Los sliders son coeficientes adimensionales. Se suman componentes con signo
antes de calcular magnitudes, máximos o demanda P-M. Un porcentaje de utilización
no se suma entre casos. Las unidades de resultados se conservan del mapa.
No son combinaciones normativas prescritas.

## Verificación y entrega

```powershell
./tests/test_viewer_combination.ps1
./tests/test_viewer_combination.ps1 -Map resultados/11_mapa_visor/analysis_map.json
python -m pytest tests -q
git rev-parse HEAD
```

Además del motor, revisar equilibrio, conservación tributaria, correspondencia
de IDs y ejes locales. El informe histórico registra un error relativo de
desplazamiento de 6.78e-9 frente al COMBO independiente: **no cumple 1e-10**.
No confundirlo con la prueba de suma del viewer ni reportarlo como aprobado.

Para Canvas: enlace al repositorio, hash del commit que realmente incluya este
avance y enlace permanente al informe `reports/semana05.md` en ese commit.
No usar el hash anterior a guardar los cambios. Este avance se cierra con
commit + push en `main` (23-09); el hash y el enlace del informe se entregan
con él.

Los tres integrantes deben ensayar el guion completo. Cada uno debe poder explicar
el contrato JSON, la suma lineal, cuándo se reanaliza, la diferencia entre demanda
y capacidad, y la transferencia de cargas tributarias. Se puede repartir la
presentación, pero no el conocimiento del sistema.
