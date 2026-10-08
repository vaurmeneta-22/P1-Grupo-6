# Informe final - Proyecto 01

**Laboratorio Estructural Digital del Edificio de Ingeniería**

| Dato | Información del informe fuente |
|---|---|
| Universidad | Universidad de los Andes |
| Facultad | Ingeniería y Ciencias Aplicadas |
| Curso | Métodos Computacionales en Obras Civiles |
| Profesor | José A. Abell |
| Integrantes | Antonia Espinoza, Magdalena Fernández y Vicente Urmeneta |
| Sección | 834 |
| Grupo indicado en la portada | 6 |
| Lugar y fecha | Santiago, Chile, 8 de octubre de 2026 |

**Fuente:** [Informe final en PDF](Informe_Final_Grupo6_P1_MCOMP.pdf).

Esta versión organiza en Markdown el contenido del PDF de 28 páginas. Conserva sus resultados, contribuciones, alcances y limitaciones. Las verificaciones descritas corresponden a las evidencias declaradas por ese informe; no representan nuevas ejecuciones realizadas al preparar este archivo. Las figuras se consultan en el PDF y se identifican en la sección 23.

**Identificación de entrega:** el PDF final proporcionado por el equipo indica Grupo 6, coincidiendo con el repositorio y la aplicación. Las diferencias de nomenclatura e instrucciones del informe se detallan en la sección 24.

## Resumen

El proyecto integra un modelo tridimensional elástico lineal en OpenSeesPy, el análisis de capacidad de hormigón armado mediante secciones de fibras, un visor interactivo en Unity y una aplicación móvil de realidad aumentada y visualización estereoscópica. La geometría y los resultados se intercambian mediante archivos JSON.

El contrato contiene 536 nodos, 722 objetos y 64 apoyos fijos. Tras subdividir vigas para representar las conexiones, el análisis exporta 701 elementos estructurales. Se estudian los casos G, Q, EX y EY mediante transferencia de cargas por áreas tributarias y sismo pseudoestático.

La verificación histórica de superposición obtuvo un error relativo de desplazamientos de **6,78 × 10⁻⁹**: cumple la tolerancia de **10⁻⁶**, pero no el criterio interno más estricto de **10⁻¹⁰**. La capacidad de secciones de hormigón armado se contrastó con un método independiente.

El PDF declara que la aplicación móvil v11 fue compilada, instalada y probada en un dispositivo. Distingue esa prueba funcional de la medición cuantitativa de precisión AR y de la validación física con visor Cardboard, que permanecen sin evidencia completa archivada.

## Introducción

El objetivo del Proyecto 01 fue desarrollar un modelo estructural tridimensional del Edificio de Ingeniería y vincular el análisis numérico de OpenSeesPy con su visualización en Unity. Se consideraron cargas gravitacionales y sísmicas pseudoestáticas, junto con verificaciones para evaluar la consistencia de la geometría, las conexiones y los resultados.

El trabajo incorpora capacidad de secciones de hormigón armado, relaciones demanda-capacidad, modificaciones de propiedades estructurales, herramientas de interacción y una aplicación móvil AR/VR. La separación entre análisis, intercambio de datos y visualización permite mantener la trazabilidad de cada elemento y contrastar los resultados mediante procedimientos independientes.

## 1. Edificio e idealización

El modelo global es tridimensional, elástico lineal y tiene seis grados de libertad por nodo: `ux`, `uy`, `uz`, `rx`, `ry` y `rz`. Vigas, columnas, refuerzos metálicos y muros equivalentes se representan mediante `elasticBeamColumn`.

Las losas no se modelan como elementos finitos. Su geometría se utiliza para calcular y transferir cargas hacia las vigas mediante áreas tributarias. La compatibilidad horizontal se representa con diafragmas rígidos por nivel activo, que vinculan `ux`, `uy` y `rz`. La capacidad no lineal se analiza aparte, a nivel de sección.

Las hipótesis principales son:

- Materiales elásticos lineales en el análisis global.
- Transformaciones geométricas lineales y pequeñas deformaciones.
- Conexiones viga-columna y viga-muro según las reglas de conectividad del repositorio.
- Empotramientos en fundaciones y apoyos verticales auxiliares para representar el sostén de las losas no modeladas.
- Masa sísmica concentrada por piso y fuerzas laterales aplicadas en el centro de masa, con fuerza y momento equivalente en el nodo maestro.
- Coordenadas geométricas de entrada en centímetros y conversión a unidades de análisis; resultados expresados con sus unidades.

El camino de carga considerado es **losa → vigas → columnas/muros → fundación**. Los apoyos auxiliares con restricciones `uz`, `rx` y `ry` en nodos sin columna o muro debajo forman parte de la idealización; no representan fundaciones físicas adicionales.

## 2. Geometría y datos

La geometría se define en `Edificio.json`. Los identificadores de los elementos permiten relacionar tipo, sección, nodos extremos y resultados. Los muros también incorporan coordenadas de su geometría.

**Tabla 1. Entidades del modelo 3D.**

| Entidad | Cantidad |
|---|---:|
| Nodos del contrato | 536 |
| Columnas de hormigón | 118 |
| Vigas X | 141 |
| Vigas Y | 165 |
| Muros equivalentes | 79 |
| Losas, sin elementos finitos | 199 |
| Columnas metálicas | 10 |
| Vigas metálicas | 10 |
| Objetos totales | 722 |
| Apoyos fijos del contrato | 64 |

Las propiedades materiales se centralizan en `data/materials.json` y las secciones en `data/sections.json` y el contrato. El PDF registra para el hormigón `f'c = 35 MPa`, `Ec = 27,8 GPa` y densidad de `2400 kg/m³`; para el acero de refuerzo, `fy = 420 MPa`, `Es = 200 GPa` y densidad de `7850 kg/m³`.

La correspondencia con el visor se conserva en `resultados/11_mapa_visor/analysis_map.json`. El cierre de Semana 6 registró 722 objetos en el contrato y 722 en el mapa, sin identificadores duplicados ni registros del mapa ausentes en el contrato. Este conteo de objetos no debe confundirse con los 701 elementos estructurales exportados por el modelo FE.

## 3. Cargas gravitacionales y áreas tributarias

La carga superficial permanente de cada losa incluye peso propio y terminaciones:

```text
qG,i = γc · ti + qterminaciones
γc = 23,544 kN/m³
qterminaciones = 2,0 kN/m²
```

Se consideran 191 losas de 15 cm y 8 losas de 12 cm:

| Espesor | Carga superficial permanente |
|---|---:|
| 15 cm | 5,5316 kN/m² |
| 12 cm | 4,8253 kN/m² |

El peso propio de vigas, columnas, muros y elementos metálicos se incorpora directamente al modelo. El resumen del caso G registra:

| Componente | Peso [kN] |
|---|---:|
| Peso propio estructural | 42 213,64 |
| Carga permanente transferida desde las losas | 31 274,39 |
| Total G | 73 488,03 |

Las áreas tributarias se distribuyen geométricamente a 45°. Para una contribución `Atrib` sobre una viga de longitud `L`, la carga lineal equivalente es `w = qG,i · Atrib / L`. Como existen distintos espesores, el total transferido se calcula sumando `qG,i · Atrib,i` para cada contribución.

El informe registra un área tributaria transferida de **5674,3915 m²**, **0,31 m²** de huecos explícitos y **2,256 m²** asociados a cuatro losas aisladas. Permanecen reportados nueve huecos geométricos.

Los errores relativos de conservación de área y carga son cero a la precisión almacenada en los JSON. Las pruebas incluyen vigas contiguas, solapes y bordes sin receptor. La losa 698 se usa como ejemplo de reparto a dos vigas sin discontinuidades artificiales.

## 4. Carga viva

El caso Q utiliza la misma geometría tributaria que G, con intensidad **qQ = 4,0 kN/m²**. La carga total transferida es **22 697,57 kN** y la conservación se comprueba mediante `ΣWQ,i = qQ · ΣAtrib,i`, con error exportado igual a cero.

Q no incluye el peso propio estructural. Para el peso sísmico se incorpora el 50 % de Q.

La herramienta SQ4 permite aplicar una carga localizada sobre una losa y visualizar su reparto entre las vigas receptoras. Es una demostración de transferencia de carga; no ejecuta un nuevo análisis de OpenSees ni calcula la respuesta estructural exacta de esa carga móvil.

## 5. Sismo pseudoestático

El peso sísmico y la fuerza horizontal equivalente se definen como:

```text
Ws = G + 0,50 · Q
Fs = α · Ws
α = 0,20
```

El coeficiente α es una hipótesis pseudoestática del proyecto. Los resultados no sustituyen un análisis sísmico normativo completo.

El peso sísmico total es **84 836,81 kN**. Se excluyen **1582,85 kN** de fundación/subterráneo sin participación lateral; el peso efectivo es **83 253,97 kN** y el corte basal es **16 650,79 kN** en EX y en EY.

**Tabla 2. Distribución pseudoestática por nivel.**

| Nivel | G [kN] | Q [kN] | Ws [kN] | F = 0,2 Ws [kN] |
|---|---:|---:|---:|---:|
| Piso 1 | 9711,90 | 2503,59 | 10 963,70 | 2192,74 |
| Piso 2 | 14 921,67 | 4565,03 | 17 204,18 | 3440,84 |
| Piso 3 | 15 325,41 | 4986,43 | 17 818,63 | 3563,73 |
| Piso 4 | 16 584,42 | 5274,04 | 19 221,44 | 3844,29 |
| Techo | 15 361,78 | 5368,48 | 18 046,02 | 3609,20 |
| Total efectivo | 71 905,18 | 22 697,57 | 83 253,97 | 16 650,79 |

Cada fuerza se aplica en el centro de masa del piso. Cuando este no coincide con el nodo maestro, se considera el momento torsional equivalente por la excentricidad.

La suma de fuerzas aplicadas se contrasta con el corte basal esperado. Se obtienen desplazamientos de techo de **7,54 mm en X** y **26,91 mm en Y**, mostrando mayor flexibilidad lateral del modelo en Y.

## 6. Superposición

El modelo lineal permite combinar las respuestas de los casos independientes:

```text
R = λG RG + λQ RQ + λEX REX + λEY REY
```

La combinación principal de estudio usa los factores **(1,2; 1,0; 1,4; 1,4)** para G, Q, EX y EY. El informe no la presenta como una combinación normativa LRFD, porque no declara una referencia que justifique esos factores ni la simultaneidad EX+EY. También se verificaron las combinaciones `(1,1,1,1)` y `(1,0,1,0)`.

**Tabla 3. Comparación de superposición y corrida conjunta.**

| Magnitud | Error relativo | Registros evaluados |
|---|---:|---:|
| Desplazamientos | 6,78 × 10⁻⁹ | 516 nodos |
| Reacciones | 2,28 × 10⁻¹⁴ | 99 |
| Fuerzas internas | 4,88 × 10⁻¹² | 701 elementos |

Las diferencias son pequeñas. Reacciones y fuerzas satisfacen 10⁻¹⁰; los desplazamientos satisfacen 10⁻⁶, pero no 10⁻¹⁰. Se mantiene explícita esa observación.

Unity incorpora comprobaciones para detectar datos faltantes o incompatibles y verificar la combinación de fuerzas, momentos y desplazamientos. Estas pruebas del motor del visor son diferentes del contraste entre corridas estructurales.

## 7. Análisis global y verificaciones

Cada caso G, Q, EX y EY se construye desde cero con `ops.wipe`. Se definen restricciones y cargas, se ejecuta un análisis estático y se exportan desplazamientos, reacciones, fuerzas globales, ejes locales y metadatos.

Las verificaciones incluyen:

- Equilibrio global: `ΣFaplicada + ΣR = 0`.
- Conservación tributaria: `ΣWi = Σqi Ai`.
- Compatibilidad cinemática de diafragmas rígidos.
- Corte basal y fuerza por piso.
- Camino de carga hasta fundación.
- Consistencia de identificadores, unidades y ejes locales.

El informe declara que los casos individuales cumplieron las verificaciones automáticas implementadas y que los movimientos de los nodos de piso fueron compatibles con el nodo maestro. Pruebas específicas permitieron detectar y corregir problemas en la definición de rigideces y en la interpretación de fuerzas internas.

## 8. Secciones de fibras

La capacidad de columnas y muros de hormigón armado se calcula mediante fibras de hormigón y acero. El hormigón usa `Concrete02` y el refuerzo usa `Steel01`.

| Sección de referencia | Disposición descrita |
|---|---|
| Columna base 700 × 700 mm | 16 barras Ø28, recubrimiento al centro de barra de 64 mm y discretización de referencia 24 × 8 fibras de hormigón |
| Columna de borde | Cuatro barras Ø28 en esquinas y 16 barras Ø36 intermedias |
| Muro de referencia 300 × 3560 mm | Barras Ø40 en bordes y malla central doble Ø10 cada 200 mm |

El estudio de sensibilidad reporta un momento último invariante para la columna entre 48 y 3072 fibras. Para el muro, la variación máxima es aproximadamente **0,16 %** entre 80 y 960 fibras.

## 9. Momento-curvatura M-φ

La curva de la columna 70 × 70 cm se obtiene mediante un modelo en voladizo con rotación aplicada progresivamente. Para P = 0, la curvatura se calcula como `φ = θ / L`.

| Resultado | Valor reportado |
|---|---:|
| Pasos convergidos | 4795 |
| Momento máximo | 1232,70 kN·m |
| Curvatura en el máximo | 0,024498 m⁻¹ |
| Momento al término | 1223,46 kN·m |
| Deformación límite del hormigón comprimido | εcu = 0,0035 |
| Rigidez inicial estimada | 671 533 kN·m² |

El análisis se detiene cuando la fibra extrema comprimida alcanza la deformación límite indicada. La Figura 3 del PDF presenta la curva obtenida.

## 10. Interacción P-M de columna y muro

El diagrama P-M representa las combinaciones de fuerza axial y momento flector que puede resistir una sección según el modelo de capacidad. Se construye con las propiedades del hormigón y la disposición de las barras descritas en el análisis de fibras.

| Sección identificada en el apartado de resultados del PDF | Momento en flexión pura [kN·m] | Momento máximo [kN·m] |
|---|---:|---:|
| Columna 70 × 70 cm | 1232,70 | 2058,65 |
| Columna de borde | 2127,30 | 2673,70 |
| Muro identificado como 25 × 356 cm | 19 970,90 | 31 263,19 |

El apartado de fibras del PDF describe un muro de referencia de **30 × 356 cm**, mientras que este apartado y la Figura 5 identifican uno de **25 × 356 cm**. Se conserva la identificación de cada apartado sin atribuir automáticamente los resultados a la misma sección.

El contraste independiente mediante bloque rectangular registra diferencias cercanas a **1,5 %** para la columna de referencia, **2,50 %** para la columna de borde en el punto balanceado y **2,43 % a 7,14 %** para el muro. La diferencia de 7,14 % corresponde a flexión pura según la matriz de QA.

Estas comparaciones evalúan la consistencia entre métodos; no implican que los modelos sean idénticos ni constituyen por sí mismas una verificación normativa completa.

## 11. Demanda-capacidad

Las solicitaciones del modelo global se comparan con las capacidades de sección. Para columnas y muros de hormigón armado se emplean envolventes P-M de fibras. Los elementos metálicos utilizan un procedimiento específico de capacidad de acero.

**Tabla 4. Evaluación nominal reportada.**

| Familia | Elementos revisados | Fuera de capacidad | Razón máxima | Elemento crítico |
|---|---:|---:|---:|---|
| Columnas, incluidas 10 metálicas | 128 | 0 | 0,894 | ID 1, 70 × 70 cm |
| Muros | 79 | 0 | 0,679 | ID 473, 30 × 310 cm |

La configuración inicial de armadura de muros tenía 24 elementos fuera de sus envolventes. Tras incorporar barras longitudinales Ø40 en los bordes y repetir la evaluación, los 79 muros quedaron dentro de sus capacidades nominales consideradas.

La evaluación es nominal y utiliza curvas uniaxiales. No representa necesariamente la interacción completa entre fuerza axial y flexión en dos direcciones, especialmente para muros con capacidades distintas por eje. Para una verificación de diseño completa faltarían combinaciones normativas, factores de reducción de resistencia y otros mecanismos de falla.

## 12. Unity como pre/postprocesador

Unity permite seleccionar elementos, consultar propiedades y representar deformaciones, fuerzas, reacciones, áreas tributarias y relaciones demanda-capacidad.

Los factores de G, Q, EX y EY pueden modificarse para explorar combinaciones de resultados ya calculados. El análisis estructural pertenece a OpenSeesPy; Unity utiliza los datos para visualización y postprocesamiento.

El intercambio JSON relaciona geometría y resultados por identificadores y mantiene separados el cálculo estructural y la representación del modelo.

## 13. Apoyos, cargas, ejes y diagramas

El visor representa columnas, vigas, muros, losas y diafragmas, con capas de nodos, ejes, apoyos y resultados. Las fundaciones se distinguen en morado. Los ejes locales exportados permiten transformar las fuerzas globales sin suponer orientaciones.

Cuando una viga está subdividida en elementos FE, sus resultados se integran para mostrar el diagrama de la viga completa. Para los tramos con carga uniforme, el PDF presenta:

```text
N(x) = Ni
Vz(x) = Vz,i - qx
My(x) = My,i + Vz,i x - qx² / 2
```

Se verificó la correspondencia de los diagramas con las fuerzas de OpenSeesPy, con diferencias despreciables en los casos analizados según el informe. La Figura 6 muestra la viga 147 seleccionada y sus propiedades y diagramas.

## 14. Modificación del modelo

Las variantes se generan independientemente desde la base y se identifican mediante etiquetas para evitar mezclar resultados.

**Tabla 5. Modificaciones consideradas.**

| Caso | Elemento | Cambio | Efectos por evaluar |
|---|---|---|---|
| A | Viga 147 | 60 × 80 → 50 × 75 cm | Rigidez, peso propio, esfuerzos y desplazamientos |
| B | Apoyo del nodo 1 | Empotrado → articulado; restricciones `[1,1,1,0,0,0]` | Reacciones y redistribución de esfuerzos |
| C | Columna 66 | 70 × 70 → 40 × 40 cm | Rigidez, solicitaciones y demanda-capacidad |

Cambiar secciones o restricciones requiere reconstruir el modelo y ejecutar G, Q, EX, EY y COMBO. Cambiar solamente los factores λ permite recombinar casos lineales existentes sin reanálisis.

Honor Track 4 permite elegir la variante en Unity, conectar el backend local, validar los datos, ejecutar OpenSeesPy y recibir resultados actualizados.

La evidencia completa archivada que declara el PDF corresponde al **Caso B**: los cinco casos se compararon con una corrida directa y una repetición, cumpliendo la tolerancia reportada. A y C superaron la validación de sus contratos, pero el informe no les atribuye una ejecución completa archivada. Una comparación cuantitativa entre base y variantes requiere disponer de los resultados de ambas configuraciones.

## 15. Realidad aumentada y aplicación móvil

La app se desarrolla con Unity, AR Foundation 6.6.2 y ARCore 6.6.2. El elemento de prueba es la **viga 185**, de **10,00 m** de longitud, sección **0,60 × 0,80 m**, nodos **60 y 70** y área tributaria **20,56 m²**.

La colocación utiliza detección de planos, ajuste manual de posición y orientación y fijación mediante un `anchor`. Se consultan G, Q, EX, EY y COMBO desde los archivos incluidos en la aplicación. El teléfono no ejecuta OpenSeesPy: representa resultados precalculados.

La geometría se muestra a escala 1:1 y los diagramas y desplazamientos pueden amplificarse visualmente. La interfaz estereoscópica permite explorar el interior del edificio y cambiar de piso mediante controles de navegación; es independiente de la colocación AR.

Las pruebas iniciales verificaron colocación v2 y diagramas de momento/corte v3 en un Xiaomi Redmi Note 12 Pro. El PDF declara prueba funcional en dispositivo de la versión final v11. No aporta mediciones cuantitativas de alineamiento o deriva ni evidencia archivada de prueba con visor Cardboard.

El PDF denomina al ejecutable `P1_Grupo6_AR_Resultados_v11.apk`. El constructor AR+VR del repositorio utiliza `P1_Grupo6_AR_VR_v11.apk`; esa diferencia se documenta en la sección 24.

## 16. Sidequests implementados

**Tabla 6. Implementación y alcance.**

| ID | Implementación | Verificación y alcance declarados |
|---|---|---|
| SQ1 | Inspector de áreas tributarias por piso, viga y losa, con área, intensidad, carga y receptores | Conservación mediante tests y JSON. La edición gráfica completa de vértices no es el foco de la versión final. |
| SQ2 | Explorador de combinaciones con sliders λG, λQ, λEX y λEY | 147 945 comprobaciones C# reportadas y contraste histórico con corridas explícitas. |
| SQ3 | Explorador de capacidad M-φ y P-M con punto de demanda | Curvas contrastadas con bloque rectangular y demanda dinámica en escritorio. P-M no se incluye en la interfaz AR. |
| SQ4 | Carga móvil sobre losa con vigas receptoras, flechas y conservación | Prototipo didáctico: conserva Puser, pero no reanaliza ni calcula respuesta estructural exacta. |

## 17. QA y tests

**Tabla 7. Matriz de aseguramiento de calidad del PDF.**

| Comprobación | Estado declarado | Evidencia y alcance |
|---|---|---|
| Equilibrio G y Q | OK | Error exportado 0,0 y verificaciones `ok=true`. |
| Conservación tributaria | OK | Errores exportados 0,0 y pruebas de bordes, solapes, huecos y losa 698. |
| Corte basal EX/EY | OK | Fuerza esperada y aplicada de 16 650,7931 kN; error exportado 0,0. |
| Diafragmas | OK | Error máximo exportado de 0,0 m. |
| Superposición FE | Con observación | Reacciones y fuerzas cumplen 10⁻¹⁰; desplazamientos históricos 6,78 × 10⁻⁹ cumplen 10⁻⁶, no 10⁻¹⁰. |
| Motor C# del visor | OK | El informe registra 147 945 comprobaciones aprobadas durante su auditoría. |
| Suite Python | OK histórico | Semana 5 registra 35 tests con OpenSeesPy 3.8.0.0. En la redacción del PDF, Python no estaba disponible en PATH y no se declaró una corrida nueva. |
| Capacidad RC | OK con alcance | Diferencias de aproximadamente 1,5 % para columna de referencia; 2,50 % para columna de borde balanceada; 2,43 % para muro balanceado y 7,14 % en flexión pura. |
| Identificadores | OK en datos | 722 registros en contrato y mapa, sin duplicados ni faltantes en el cierre registrado. |
| Compilación móvil v11 | OK | El informe declara compilación de la versión final. Véase la diferencia de nombre del ejecutable en la sección 24. |
| APK de entrega | OK funcional | El informe declara instalación y prueba en dispositivo. |
| AR física | OK funcional | Funcionamiento confirmado según el PDF, sin medición cuantitativa de precisión y estabilidad. |
| H4 | OK con alcance | Caso B archivado con cinco casos, corrida directa y repetición. A/C sin reportes completos archivados según el informe. |
| H1 / Cardboard | OK digital | Pruebas digitales documentadas; pendiente evidencia física archivada con visor Cardboard. |

La suite Python cubre equilibrio, conservación, áreas tributarias, superposición, camino de carga, empalmes viga-viga y secciones de fibras. Las verificaciones adicionales incluyen el voladizo de prueba de ejes, auditoría de `eleForce`, sensibilidad de fibras, bloque rectangular, demanda-capacidad y cierre de diagramas.

Las capturas documentan la visualización y los resultados, pero no sustituyen una medición física. El informe entiende QA como evidencia reproducible y declara las limitaciones de cada comprobación.

## 18. Limitaciones

1. El modelo global es elástico lineal y de pequeñas deformaciones; no representa fisuración, fluencia, plastificación global, P-Delta ni falla progresiva.
2. Las losas no son FE y se emplean apoyos verticales de idealización.
3. El sismo pseudoestático con α = 0,20 no reemplaza un análisis sísmico normativo.
4. Los factores de COMBO y la simultaneidad EX+EY son hipótesis de estudio.
5. La demanda-capacidad es nominal y uniaxial; no incorpora interacción biaxial completa, factores φ, corte, confinamiento detallado ni todos los estados límite.
6. La flexión pura del muro presenta una diferencia de 7,14 % entre fibras y bloque rectangular.
7. Permanecen nueve huecos geométricos reportados y cuatro losas aisladas.
8. La superposición de desplazamientos no cumple el criterio interno de 10⁻¹⁰, aunque sí 10⁻⁶.
9. La unicidad de IDs se comprobó en datos; todos los GameObjects no se reauditaron en Play Mode durante el último cierre descrito.
10. SQ4 conserva la carga, pero no calcula la respuesta exacta de una carga móvil.
11. AR representa una viga fija y no reconoce automáticamente cualquier elemento físico.
12. La geometría AR es real; diagramas y desplazamientos se amplifican visualmente.
13. La prueba funcional AR v11 no incluye mediciones de precisión, alineamiento, deriva ni repetibilidad. Las anclas no persisten entre sesiones.
14. H1 cuenta con validación digital y no con evidencia física archivada de visor Cardboard. H4 tiene evidencia numérica completa archivada solo para B según el PDF.
15. El APK depende de la compatibilidad del dispositivo, ARCore, iluminación y textura del entorno.

## 19. Uso de IA

Se utilizó un agente de IA como apoyo de implementación, auditoría y documentación. El equipo mantuvo la responsabilidad sobre las decisiones estructurales y la aceptación de los resultados.

Las tareas de apoyo incluyen scripts de modificación y reanálisis por etiqueta, exportación del mapa, motor C# de superposición y sus pruebas, interfaces y navegación de Unity, preparación móvil y consolidación de reportes.

El informe registra errores o propuestas que fueron detectados y corregidos:

- Orden incorrecto de argumentos de `elasticBeamColumn`, detectado con un voladizo analítico.
- Interpretación incorrecta de `eleForce` como fuerzas locales, refutada mediante un modelo mínimo y corregida a fuerzas globales.
- Diagramas iniciales con signos o extremos incompatibles, corregidos mediante cierre de equilibrio por tramo.
- Estrategia AR basada en marcador, reemplazada después de una prueba física insatisfactoria.
- Afirmaciones excesivas sobre superposición y AR, precisadas al distinguir tolerancias, compilación, prueba visual y medición física.

El agente produjo código y documentación candidatos y ejecutó las comprobaciones disponibles. No sustituyó la revisión técnica ni la validación física del equipo. Las evidencias se identifican como históricas o actuales según el informe, sin atribuir corridas que no tienen respaldo.

## 20. Contribución individual

**Tabla 8. Contribuciones declaradas por el equipo.**

| Integrante | Contribuciones y módulos revisados | Problema identificado | Aprendizaje |
|---|---|---|---|
| Magdalena Fernández | OpenSeesPy; cargas gravitacionales y vivas, áreas tributarias, sismo pseudoestático, conexiones y diagramas. Contraste con Unity/Excel y presentación. | Vigas sin conexión adecuada con la estructura, descritas como “vigas volando”; se revisó y corrigió su conectividad. | La geometría no garantiza conectividad. Es necesario verificar camino de cargas, conservación tributaria y distribución sísmica por piso. |
| Antonia Espinoza | Análisis global, superposición, verificaciones numéricas, secciones de fibras, M-φ, P-M, demanda-capacidad, QA, reproducibilidad e informe final. | El error de desplazamientos de superposición cumplía 10⁻⁶, pero no 10⁻¹⁰; se precisó el criterio de aceptación. | Las diferencias requieren tolerancias explícitas. Demanda global y capacidad de sección son análisis distintos y necesitan contrastes independientes. |
| Vicente Urmeneta | Evolución del visor HTML, exportación JSON e integración Unity; visualización, interacción, modificaciones, reanálisis, sidequests, Honors Track, AR/VR y compilaciones móviles. | El alineamiento inicial por marcadores no entregó resultados satisfactorios; se reemplazó por planos, colocación manual y anclaje. | Compilar no garantiza colocación física precisa. La trazabilidad exige IDs y transformaciones de coordenadas coherentes. |

## 21. Honors Track

### H4 - Reanálisis OpenSees desde Unity

El backend local recibe A/B/C, valida el contrato, ejecuta G/Q/EX/EY/COMBO y devuelve resultados. El servicio corre en el mismo computador que Unity; no es un backend remoto para el teléfono.

El PDF declara evidencia completa archivada para B, con comparación directa y repetición dentro de la tolerancia. A/C están disponibles y tienen validación de entradas, sin atribuirles una ejecución completa archivada.

### H1 - Google Cardboard VR

La implementación documentada en Semana 7 permite recorrer pisos 1 a 4, seguir la orientación de cabeza/teléfono, seleccionar elementos y consultar resultados precalculados. El desarrollo incluye representación estereoscópica, locomoción e interacción con diagramas/capacidad, descritas en [H1_Cardboard_VR.md](H1_Cardboard_VR.md).

Se registran pruebas digitales de locomoción, selección y datos. La validación física con visor Cardboard no está archivada según el informe y debe distinguirse de la prueba funcional del APK en un teléfono. El recorrido VR no ejecuta OpenSees durante la navegación.

## 22. Reproducibilidad y producto ejecutable

Las siguientes instrucciones adaptan las del PDF a las rutas que existen en el repositorio. No se crea un entorno, no se ejecutan análisis ni se compila un APK al preparar este Markdown.

### 22.1. Entorno

| Componente | Versión registrada |
|---|---|
| Python | 3.12, según `.python-version` |
| OpenSeesPy | 3.8.0.0 |
| NumPy | 2.5.2, valor histórico citado por el PDF; no bloqueado en el repositorio |
| Unity Editor | 6000.6.0f1 |
| URP | 17.6.0 |
| AR Foundation / ARCore | 6.6.2 / 6.6.2 |

El PDF propone un entorno virtual y `requirements.txt`, pero ese archivo no está presente en el repositorio consultado. Para Windows, el [README](../README.md) proporciona instalación explícita con Python 3.12 de 64 bits:

```powershell
python --version
python -m pip install "openseespy==3.8.0.0" "openseespywin==3.8.0.0" matplotlib pytest
python -m pip check
python -c "import sys; import openseespy.opensees as ops; import matplotlib; import pytest; print(sys.executable); print('OpenSees:', ops.version())"
```

NumPy se resuelve como dependencia de Matplotlib. Las dependencias auxiliares no tienen un lock completo; no se atribuye al comando anterior la reproducción exacta de todas las versiones del PDF. Unity utiliza el comando `python` del entorno heredado, por lo que el intérprete debe estar en PATH y contener las dependencias. Si se usa un entorno virtual, Unity debe heredar ese entorno.

### 22.2. Análisis y resultados

Desde la raíz del repositorio:

```powershell
python opensees/opensees_edificio_v2.py --case G
python opensees/opensees_edificio_v2.py --case Q
python opensees/opensees_edificio_v2.py --case EX
python opensees/opensees_edificio_v2.py --case EY
python opensees/opensees_edificio_v2.py --case COMBO --lambda-g 1.2 --lambda-q 1.0 --lambda-ex 1.4 --lambda-ey 1.4
```

Para regenerar capacidad y resultados derivados:

```powershell
python scripts/parte_d_fiber.py
python scripts/parte_d_muros.py
python scripts/sensibilidad_secciones.py
python scripts/comparacion_rc.py
python scripts/demanda_capacidad.py
python opensees/exportar_resultados_csv.py
python opensees/exportar_analysis_map.py
```

Se coloca la exportación del mapa después de generar la capacidad para incluir las curvas actualizadas. El exportador CSV lee el caso G. Estos scripts escriben en las carpetas correspondientes de `resultados/` y pueden sobrescribir resultados previos; las variantes deben mantenerse identificadas y separadas.

Con Play Mode detenido, sincronizar el contrato y el mapa:

```powershell
Copy-Item -LiteralPath .\Edificio.json -Destination .\Unity\Assets\StreamingAssets\Edificio.json -Force
Copy-Item -LiteralPath .\resultados\11_mapa_visor\analysis_map.json -Destination .\Unity\Assets\StreamingAssets\analysis_map.json -Force
```

### 22.3. Viewer y tests

Abrir la carpeta `Unity/` con **Unity Editor 6000.6.0f1** mediante Unity Hub. Esperar la resolución de paquetes, abrir `Assets/Scenes/SampleScene.unity` y pulsar Play.

Desde la raíz, ejecutar:

```powershell
python -m pytest tests -q
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tests\test_viewer_combination.ps1 -Map .\resultados\11_mapa_visor\analysis_map.json
```

El segundo comando comprueba el motor C# contra el mapa especificado. La prueba de H4 se realiza desde **Modificaciones → Honor Track 4**, conectando el backend y ejecutando la verificación del escenario elegido.

### 22.4. Compilación móvil

Instalar Android Build Support, Android SDK/NDK Tools y OpenJDK para Unity 6000.6.0f1 mediante Hub. El proyecto utiliza las herramientas Android incluidas con ese editor. Git debe estar en PATH para resolver Cardboard.

Para la app conjunta AR+VR, cerrar el editor y ejecutar desde la raíz:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_mobile_vr.ps1
```

El script actual genera `Unity/Builds/P1_Grupo6_AR_VR_v11.apk`, versión 0.6.1, código Android 11, y el log `Unity/Builds/AR_VR_v11_build.log`. Si Unity no está en la ruta estándar de Windows, ajustar `unityExe` o utilizar **Lab → Móvil → Compilar APK AR + Cardboard VR** en el editor.

El PDF indica `build_ar_results.ps1`, pero ese script genera el APK AR v4; no es el constructor de la app combinada v11. Esta adaptación corrige la instrucción de ejecución sin modificar el PDF.

### 22.5. Estado de release y producto

El PDF declara un producto móvil ejecutable compilado y probado. Para una entrega trazable se debe asociar el archivo definitivo con su hash SHA-256 y el commit correspondiente.

La entrega final se identifica con el tag **`v1.0.0`**. El commit asociado, los archivos ejecutables y su estado de publicación se consultan en la [Release final de GitHub](https://github.com/vaurmeneta-22/P1-Grupo-6/releases/tag/v1.0.0). Los APK de `Unity/Builds/` se generan localmente y se distribuyen como adjuntos de Release, sin incorporarlos al historial Git. El ejecutable comprobado corresponde a la versión Android 0.6.1, código 11; la numeración del tag identifica la entrega completa del proyecto.

### 22.6. Preparación local del ejecutable de entrega

El 8 de octubre de 2026 se comprobó el APK existente `Unity/Builds/P1_Grupo6_AR_VR_v11.apk`, sin recompilarlo ni publicar una Release. Esta comprobación técnica del archivo es adicional a las evidencias narradas en el PDF y no equivale a una nueva prueba física.

| Comprobación | Resultado |
|---|---|
| Tamaño del APK | 46 663 432 bytes |
| Versión Android | 0.6.1, código 11 |
| Identificador de paquete | `com.grupo6.p1.arplacement` |
| Android mínimo / objetivo | API 29 / API 36 |
| Arquitectura nativa | ARM64 |
| Integridad del ZIP/APK | Correcta |
| Firma | Verificada con APK Signature Scheme v2; certificado Android Debug |
| Proveedores nativos | ARCore y Cardboard presentes |
| Geometría incluida | 536 nodos, 722 objetos, IDs de elementos únicos |
| Columna 66 en el APK | Sección base 70 × 70 cm |
| Casos incorporados | G, Q, EX, EY y COMBO |
| Correspondencia de datos | Geometría equivalente a `Edificio.json`; mapa idéntico semánticamente al mapa versionado en el commit `5fe4c82` |

SHA-256 del APK comprobado:

```text
FDE4437DF2779EE690E6B336D94F677F27938BD73A1514C8707A17A5179F0508
```

Los registros existentes contienen `H1 MOBILE BUILD: Succeeded` y `H1 PLAY CHECK: PASS` para pisos 1 a 4, cambios de piso, juntas, selección, casos/vistas y pausa de locomoción. Se revisaron esos registros; no se atribuye una nueva ejecución de Play Mode.

El mapa actualmente presente en `Unity/Assets/StreamingAssets/analysis_map.json` contiene resultados de una variante y difiere del modelo base del APK. Antes de recompilar una entrega base, utilizar **Restaurar Base** y verificar que contrato y mapa correspondan a la misma configuración. Los resultados locales de variantes se conservaron.

Las notas de publicación están en [release_final.md](release_final.md). Esta sección registra la comprobación local previa a la publicación; el estado posterior de la entrega se consulta en GitHub mediante el enlace de la sección 22.5.

## 23. Figuras del documento fuente

Las imágenes originales permanecen en el PDF. Los enlaces usan el número físico de página del archivo, que incluye la portada.

| Figura | Contenido | Página del PDF |
|---|---|---|
| 1 | Vista general del modelo estructural tridimensional | [7](Informe_Final_Grupo6_P1_MCOMP.pdf#page=7) |
| 2 | Esquema de fuerzas pseudoestáticas por nivel en EX | [10](Informe_Final_Grupo6_P1_MCOMP.pdf#page=10) |
| 3 | Curva momento-curvatura de columna 70 × 70 cm | [13](Informe_Final_Grupo6_P1_MCOMP.pdf#page=13) |
| 4 | Interacción P-M de columna 70 × 70 cm | [14](Informe_Final_Grupo6_P1_MCOMP.pdf#page=14) |
| 5 | Interacción P-M del muro identificado como 25 × 356 cm | [14](Informe_Final_Grupo6_P1_MCOMP.pdf#page=14) |
| 6 | Viga 147 y consulta de propiedades y diagramas | [17](Informe_Final_Grupo6_P1_MCOMP.pdf#page=17) |
| 7 | Interfaz estereoscópica y controles de navegación/pisos | [19](Informe_Final_Grupo6_P1_MCOMP.pdf#page=19) |

## 24. Observaciones al trasladar el PDF a Markdown

| Punto | Documento fuente | Tratamiento en esta versión |
|---|---|---|
| Identificación del grupo | El equipo proporcionó la portada final con Grupo 6 | Se actualiza el enlace al PDF final y se conserva su contenido sin editarlo. |
| Sección del muro | Fibras: 30 × 356 cm; resultados/Figura 5: 25 × 356 cm | Se mantienen ambas identificaciones; no se atribuyen los valores a una única sección sin revisar los datos de origen. |
| Dependencias Python | Indica `requirements.txt` | Se advierte que el archivo no existe y se remite a la instalación explícita del README. |
| Orden de generación | Exporta el mapa antes de generar la capacidad | Se deja el mapa al final para incluir las curvas regeneradas. |
| Nombre y constructor del APK | `P1_Grupo6_AR_Resultados_v11.apk` y `build_ar_results.ps1` | El constructor disponible para AR+VR v11 es `build_mobile_vr.ps1`, con salida `P1_Grupo6_AR_VR_v11.apk`. |
| Validación física | Declara funcionamiento móvil v11; no presenta mediciones AR ni evidencia física archivada con Cardboard | Se mantiene la diferencia entre prueba funcional, medición cuantitativa y validación con visor. |
| Evidencias numéricas | Suite Python histórica; H4 completo archivado para B | Se preserva el alcance declarado, sin presentar nuevas corridas. |

Estas observaciones corresponden a la preparación documental y no alteran geometría, resultados, código, PDF original ni archivos existentes del proyecto.

## Conclusión

El proyecto integra definición geométrica, análisis estructural lineal, capacidad nominal de secciones y visualización interactiva. OpenSeesPy calcula desplazamientos, reacciones y esfuerzos, mientras que el contrato JSON permite relacionarlos con los elementos del visor Unity y de la aplicación móvil.

Las verificaciones de equilibrio, transferencia de cargas, superposición y capacidad aportan evidencia de consistencia, con tolerancias y alcances explícitos. La modificación del apoyo del nodo 1 cuenta con evidencia completa de reanálisis y reproducibilidad según el PDF; las otras variantes requieren mantener la distinción entre implementación y registros archivados.

La app móvil añade colocación AR y exploración estereoscópica. El informe declara funcionamiento en dispositivo para v11, pero reconoce que faltan mediciones cuantitativas AR y evidencia archivada con visor Cardboard.

El aporte central del trabajo es la trazabilidad entre modelo, cálculo y representación, junto con la posibilidad de contrastar resultados mediante comprobaciones independientes. Las idealizaciones, la interacción nominal uniaxial, las tolerancias de superposición y las pruebas físicas pendientes delimitan el alcance del producto y las tareas de una etapa posterior.
