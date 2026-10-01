# Informe de Avance — Semana 6: validación AR y cierre técnico

| Campo | Valor |
|---|---|
| **Proyecto** | P1 — Laboratorio Estructural Digital (Edificio de Ingeniería) |
| **Curso** | Métodos Computacionales (8vo semestre) |
| **Grupo** | 6 |
| **Período** | 28 de septiembre – 2 de octubre de 2026 |
| **Fecha de corte de este informe** | 1 de octubre de 2026 |
| **Entregable** | Validación AR, trazabilidad de resultados y cierre técnico |
| **Dispositivo de prueba** | Xiaomi Redmi Note 12 Pro |
| **Elemento de demostración** | Viga 185, sección 60 × 80 cm, longitud 10 m |
| **Versión más reciente** | Viga AR v4, versión 0.4.0, código Android 4 |

## Objetivo y continuidad del proyecto

Las semanas anteriores establecieron el benchmark y sus convenciones (Semana 1),
el modelo del edificio y las áreas tributarias (Semana 2), los casos de carga y
las capacidades de secciones (Semana 3), los diagramas y su integración en Unity
(Semana 4), y el laboratorio interactivo con superposición y modificaciones
(Semana 5).

Durante la Semana 6 se llevó la visualización de una viga del edificio a una
aplicación Android de realidad aumentada. El objetivo inmediato fue representar
la viga a escala real, mantenerla en una ubicación del entorno al mover el teléfono
y permitir su alineamiento manual. Después se incorporaron los resultados
estructurales calculados previamente.

**Estado comprobado:** el usuario confirmó en el teléfono el funcionamiento de
la colocación de la versión v2 y de los diagramas de momento y corte de v3.
La versión v4 incorpora axial, desplazamientos, área tributaria y cargas; su APK
fue compilado y su firma fue verificada. La prueba física de estas nuevas vistas
de v4 permanece pendiente. No se dispone todavía de un registro fotográfico
incorporado al repositorio ni de mediciones del error de alineamiento.

---

## 1. Flujo AR

### 1.1 Flujo solicitado y primer prototipo con marker

El flujo previsto inicialmente fue:

~~~text
marker → pose → anchor → transform → elemento → resultado
~~~

| Etapa | Función |
|---|---|
| Marker | Imagen impresa asociada previamente a la viga 185. |
| Pose | Posición y orientación estimadas por AR a partir de la imagen. |
| Anchor | Referencia espacial utilizada para ubicar el contenido. |
| Transform | Corrección de posición, orientación y escala de la representación. |
| Elemento | Objeto Unity asociado al ID estructural mediante ElementTag. |
| Resultado | Consulta de fuerzas y momentos exportados desde OpenSees. |

Este prototipo se documentó en [AR_RealScale_v1.md](AR_RealScale_v1.md).
La prueba del usuario mostró problemas de ubicación, escala percibida y
estabilidad: la viga parecía acompañar al teléfono. Por tanto, ese flujo no se
considera validado físicamente.

### 1.2 Flujo vigente: colocación manual sobre un plano

Para resolver la colocación se implementó una escena independiente que sustituye
la detección del marker por la selección de una pose sobre un plano horizontal:

~~~text
plano detectado + selección manual
  → pose capturada al pulsar Colocar
  → ARAnchor
  → transform de ajuste
  → Viga 185 con ElementTag
  → resultados por caso desde analysis_map.json
~~~

La identificación actual es una asignación conocida a la viga 185. La aplicación
no reconoce automáticamente una viga física a partir de su apariencia y no
necesita un QR ni un marker para este flujo.

**Interacción implementada:**

1. AR Foundation y ARCore inician la sesión y el seguimiento de la cámara.
2. El usuario mueve lentamente el teléfono para detectar una superficie horizontal.
3. Un raycast desde la mira central busca un punto dentro del plano detectado.
   Una flecha amarilla muestra el inicio y el sentido de la viga.
4. Al pulsar **Colocar viga aquí**, se captura la pose una sola vez y se crea
   un ARAnchor. El cuerpo de la viga se construye como hijo de ese anclaje.
5. La cara inferior queda sobre el plano. La viga se extiende 10 m desde su inicio.
6. El usuario puede caminar alrededor: la cámara cambia de pose y la viga mantiene
   su referencia en el entorno.
7. **Ajustar posición** permite traslaciones y giros. Los pasos disponibles son
   5 cm/1°, 25 cm/5° y 1 m/15°.
8. **Fijar posición** crea una nueva ancla cerca del centro de la viga, conserva
   la pose visible y retira la ancla anterior.
9. Los controles muestran Momento, Corte, Axial, Desplazamientos o Cargas, con
   selección G/Q/EX/EY/COMBO. El área tributaria aparece únicamente como valor en m².

Solo la vista previa sigue la mira. La viga colocada depende del anclaje.
Cuando se pierde el seguimiento, la geometría se oculta y se bloquea el ajuste
hasta recuperarlo. Cerrar la app requiere volver a colocar la viga: no se
implementó persistencia de anclas entre sesiones.

### 1.3 Implementación y evolución

| Versión | Avance | Evidencia |
|---|---|---|
| RealScale v1 | Intento de representación 1:1 desde marker. | Compilación documentada; problemas físicos reportados por el usuario. |
| Colocación v2 | Plano horizontal, ancla, dimensiones reales y ajuste manual. | Usuario: «ok funciona!!!». |
| Diagramas v3 | Diagramas My y Vz vinculados a la viga, selección de casos y amplitud visual. | Usuario: «SUPER!! YA FUNCIONA Y MUESTRA!». |
| Resultados v4 | Axial N, desplazamientos nodales, área tributaria y cargas. | APK generado; comprobaciones de datos y firma aprobadas; ensayo físico pendiente. |

Archivos principales:

- [ARBeamPlacement.cs](../Unity/Assets/Scripts/ARBeamPlacement.cs): detección,
  colocación, ajuste, anclaje e interfaz.
- [ARBeamPlacementMath.cs](../Unity/Assets/Scripts/ARBeamPlacementMath.cs):
  dimensiones, dirección horizontal, rotación y traslación.
- [ARBeamDiagrams.cs](../Unity/Assets/Scripts/ARBeamDiagrams.cs): lectura y
  representación de resultados.
- [ARPlacementSetup.cs](../Unity/Assets/Editor/ARPlacementSetup.cs): creación
  de escena, materiales, comprobaciones y compilación Android.
- [AR_Colocacion_v2.md](AR_Colocacion_v2.md) y
  [AR_Diagramas_v3.md](AR_Diagramas_v3.md): documentación de las versiones previas.

---

## 2. Transformación entre sistemas

### 2.1 OpenSees y Unity

OpenSees utiliza X e Y en planta y Z como altura. Las coordenadas del contrato
geométrico se convierten de centímetros a metros antes de crear los nodos.
En Unity, Y representa la altura. La conversión del visor es:

~~~text
p_S = [x_S, y_S, z_S]ᵀ

p_U = C · p_S

    [−1  0  0]
C = [ 0  0  1]
    [ 0  1  0]

p_U = [−x_S, z_S, y_S]ᵀ
~~~

La inversión de X y el intercambio de Y/Z mantienen la orientación adoptada por
el visor. La transformación se implementa en
[AnalysisMap.cs](../Unity/Assets/Scripts/AnalysisMap.cs), líneas 383–386:

~~~csharp
NodeCoords[kv.Key] =
    new Vector3(-(float)c[0], (float)c[2], (float)c[1]);
~~~

La geometría se convierte en
[EdificioLoader.cs](../Unity/Assets/Scripts/EdificioLoader.cs), función
NodeToPos, líneas 435–439:

~~~csharp
return new Vector3(-n.x * scale, n.z * scale, n.y * scale);
~~~

El factor scale convierte las unidades de la geometría del contrato. Los
resultados de AnalysisMap ya utilizan metros.

### 2.2 Referencia local de la viga y ubicación AR

La viga AR se construye en un sistema local B:

- X local: longitud, desde el nodo 60 hacia el nodo 70.
- Y local: vertical, altura de la sección.
- Z local: ancho de la sección.

Para esta viga, se puede relacionar un punto estructural con la referencia local
restando la posición del nodo inicial:

~~~text
p_B = C · (p_S − p_S,60)
~~~

Por ejemplo, el nodo 60 se representa en (0,0,0) y el nodo 70 en (10,0,0).
Se elimina así la ubicación absoluta del edificio antes de colocar la viga en
el entorno reconocido por el teléfono.

El origen de la sesión AR no coincide automáticamente con el del edificio.
La pose elegida por el usuario establece la ubicación y orientación de la
representación. Usando coordenadas homogéneas:

~~~text
p_W = T_WA · T_AB · p_B

T_WB = T_WA · T_AB
~~~

Donde W es el mundo de Unity/AR, A es el anchor y B es la raíz de la viga.
T_WA contiene la pose del anchor en el mundo; T_AB contiene el ajuste local.
Si se describe la jerarquía desde el origen XR, T_WA ya incluye la transformación
del XROrigin y del anclaje. No se debe aplicar dos veces esa transformación.

Al colocar, el anchor está sobre el plano y la raíz de la viga recibe el
desplazamiento local (0,0.40,0) m. El cubo que representa el cuerpo tiene:

~~~text
posición local del centro = (5, 0, 0) m
dimensiones = (10, 0.80, 0.60) m
~~~

Así, el inicio longitudinal queda en X=0 y la cara inferior sobre el plano.
La escala del XROrigin se mantiene en uno.

### 2.3 Rotación, traslación y cambio de anchor

La orientación inicial utiliza la dirección de la cámara proyectada sobre el
plano horizontal. BeamRotation orienta el eje X local según esa dirección,
manteniendo Y vertical.

Los controles trasladan la viga respecto a la vista horizontal del teléfono:

~~~text
Δp = paso · (a · derecha_horizontal
           + b · adelante_horizontal
           + c · vertical)
~~~

El giro se aplica alrededor del centro de la viga y del eje vertical. Esto evita
que su inicio actúe como pivote y desplace excesivamente el extremo opuesto.

Al fijar un ajuste se cambia de padre conservando la transformación mundial:

~~~csharp
beamRoot.SetParent(anchor.transform, true);
~~~

Matemáticamente:

~~~text
T_A'nuevo,B = inversa(T_W,A'nuevo) · T_WB
~~~

La pose visible T_WB se conserva. El seguimiento AR puede corregir posteriormente
la pose del anchor; esto no elimina el posible error físico de tracking.

### 2.4 Escala de geometría y resultados

La viga está a escala 1:1: una unidad del espacio AR corresponde a un metro.
Las bandas amarillas están separadas 1 m.

Los diagramas mantienen la abscisa longitudinal en metros, pero amplifican sus
ordenadas para hacerlas visibles. Esa altura visual no es una dimensión física
del momento o del cortante. Los valores se muestran en kN y kN·m.

Los desplazamientos se leen en metros, se muestran numéricamente en milímetros
y se amplifican visualmente entre ×1 y ×600. Se proyectan a los ejes locales de
la viga mediante productos escalares. La representación une los desplazamientos
de los nodos 60, 63, 67 y 70 con segmentos rectos; no reconstruye una curva de
flexión continua mediante funciones de forma.

### 2.5 Qué se calcula en cada equipo

| Computador: cálculo previo | Teléfono: ejecución de la app |
|---|---|
| Modelo OpenSees del edificio y resolución G/Q/EX/EY. | Cámara, sensores, seguimiento AR y detección de planos. |
| Fuerzas y momentos de extremo, desplazamientos, rotaciones y reacciones. | Colocación, anclaje, movimientos y renderizado. |
| Geometría tributaria y cargas. | Lectura del JSON incorporado al APK. |
| Análisis de capacidad de secciones, separado del modelo global. | Reconstrucción de diagramas desde fuerzas y cargas exportadas y combinación en memoria. |

El teléfono no ejecuta OpenSees ni resuelve nuevamente el edificio. Las curvas
P-M no forman parte de la interfaz AR actual.

---

## 3. Precisión: estimación y procedimiento de medición

La confirmación de funcionamiento no equivale a una medición de precisión.
No se dispone de errores observados en centímetros ni de ensayos repetidos
contra referencias físicas. Se reemplaza la estimación genérica de 5–8 cm del
reporte anterior por un cálculo que considera la longitud real de 10 m.

### 3.1 Estimación simple

Para un error inicial de posición e₀ y un error angular θ, el error lateral
aproximado en el extremo final es:

~~~text
e_final ≲ e₀ + L · |sin(θ)| + e_deriva
~~~

Es un presupuesto simple de alineamiento, no una cota certificada del sistema.
Para pequeños ángulos, L·sin(θ) ≈ L·θ, con θ en radianes.

| Error angular supuesto | Desviación lateral por giro en 10 m |
|---|---:|
| 0.5° | 8.73 cm |
| 1° | 17.45 cm |
| 2° | 34.90 cm |

**Ejemplo ilustrativo:** suponiendo 3 cm de error inicial, 1° de error de orientación
y sin agregar deriva, el error en el extremo sería aproximadamente 20.45 cm.
Estos valores son supuestos de cálculo; no son mediciones obtenidas con el Xiaomi.

El paso más fino de la interfaz es 5 cm y 1°. Si el ajuste se hiciera solo
redondeando al paso más cercano, la resolución nominal sería ±2.5 cm por dirección
y ±0.5° de giro. Esto explica por qué una viga puede verse estable y aun mostrar
una separación apreciable en su extremo final.

### 3.2 Ensayo reproducible pendiente

1. Marcar en el entorno el inicio y el final de una línea de 10 m medida con huincha.
2. Colocar la viga y ajustar sus extremos respecto a esas referencias.
3. Registrar error de inicio y final, longitud virtual contrastada con las bandas
   de 1 m y condiciones de iluminación.
4. Caminar alrededor y volver al punto de observación inicial. Registrar la
   variación de alineamiento después de 30 y 60 segundos.
5. Repetir al menos tres colocaciones y reportar promedio y máximo.

| Medición | Estado al corte |
|---|---|
| Error de alineamiento inicial | Pendiente de medición |
| Error en el extremo a 10 m | Pendiente de medición |
| Deriva a 30/60 s | Pendiente de medición |
| Contraste de escala con huincha | Pendiente de medición |

El alcance validado es la visualización didáctica. No se declara precisión
topográfica ni se utiliza la app para medir deformaciones reales del edificio.

---

## 4. Resultados y evidencia de correspondencia

### 4.1 Elemento real del edificio representado

| Campo | Valor |
|---|---|
| Elemento del contrato del edificio | Viga 185 |
| ID del objeto AR | ElementTag.elementId = 185 |
| Tipo | beam_x |
| Sección | 60 × 80 cm |
| Nodos extremos | 60 y 70 |
| Nivel del modelo | Piso 3 |
| Coordenada nodo 60, OpenSees [m] | (−10, 0, 10.68) |
| Coordenada nodo 70, OpenSees [m] | (−20, 0, 10.68) |
| Longitud | 10.00 m |
| Área tributaria | 20.561 m²; interfaz: 20.56 m² |

Esta es una viga del modelo del edificio, no un elemento ficticio de prueba.
Su asociación en AR es explícita y fija. La coincidencia automática con una viga
física instalada en el edificio no se ha demostrado.

### 4.2 Correspondencia entre ID del contrato y tramos FE

La viga completa se divide en tres elementos de OpenSees:

| Tramo | Tag FE | Nodos | Longitud [m] |
|---|---:|---|---:|
| 1 | 185 | 60 → 63 | 5.00 |
| 2 | 300082 | 63 → 67 | 2.49 |
| 3 | 300083 | 67 → 70 | 2.51 |
| **Viga completa** | **ID 185 del contrato** | **60 → 70** | **10.00** |

La clave forces.G["185"] contiene solo las fuerzas del primer tramo FE.
Su extremo j pertenece al nodo 63 y no al final de la viga completa.
Los diagramas actuales concatenan los tres tramos mediante
ElementDiagrams.Construir(185, caso, PlanoVertical).

Esta distinción corrige el reporte anterior: los valores −84.08 kN y −277.00 kN·m
citados como extremo final correspondían al primer tramo, no al nodo 70.

### 4.3 Resultados mostrados para la viga completa

Los valores siguientes son esfuerzos de sección con la convención del motor
del visor. En el extremo final se comparan con las acciones nodales exportadas
cambiadas de signo; no deben confundirse con el vector bruto local_j.

| Caso | My(0) [kN·m] | My(10) [kN·m] | Vz(0) [kN] | Vz(10) [kN] |
|---|---:|---:|---:|---:|
| G | −285.59 | −557.30 | 140.95 | −299.91 |
| Q | −120.17 | −201.99 | 64.39 | −110.04 |
| EX | −135.06 | 132.38 | 27.66 | 28.90 |
| EY | 121.58 | 210.90 | −43.57 | 149.93 |
| COMBO | −481.75 | −390.17 | 211.26 | −219.58 |

COMBO utiliza los factores efectivos del motor de AnalysisMap, mostrados en
la interfaz: G=1.2, Q=1.0, EX=1.4, EY=1.4 para el mapa de esta entrega.

Para cada tramo de longitud x:

~~~text
N(x)  = N_i
Vz(x) = Vz_i − q·x
My(x) = My_i + Vz_i·x − q·x²/2
~~~

Se conservan los cambios de cortante en los nodos interiores. El muestreo incluye
el punto V=0 cuando corresponde para identificar el extremo de momento.
Los diagramas se construyen con 78 muestras para la viga completa.

**Resultados adicionales incorporados en v4:**

| Magnitud | Caso G |
|---|---|
| Axial al inicio | N(0) = 0 kN en el resultado exportado |
| Desplazamiento nodo 60 [mm] | UX=−0.3323; UY=−0.3788; UZ=−1.8057 |
| Desplazamiento nodo 70 [mm] | UX=−0.3323; UY=−0.3976; UZ=−1.4219 |
| Carga distribuida de losa | q=11.37344 kN/m |
| Total distribuido de losa | q·L=113.7344 kN |
| Peso propio total de esta viga | 23.544·0.60·0.80·10=113.0112 kN |

El peso propio se aplica en OpenSees como aportes nodales de la mitad del peso
de cada tramo en sus extremos. No se suma como carga uniforme al reconstruir
la parábola. Las flechas de v4 muestran únicamente los aportes de esta viga;
no incluyen los aportes de columnas, muros u otras vigas que confluyen en esos nodos.
En EX/EY no hay carga vertical distribuida directa sobre la viga: el sismo se
aplica a los diafragmas.

### 4.4 Evidencias verificables

1. [Edificio.json](../Edificio.json) y su copia en StreamingAssets contienen
   el ID 185, sección 60x80 y nodos 60/70.
2. [analysis_map.json](../Unity/Assets/StreamingAssets/analysis_map.json)
   contiene la identidad, coordenadas, fracciones FE, fuerzas, desplazamientos
   y tributarias utilizadas por la app.
3. ARBeamPlacement asigna un único ElementTag a la viga. ARPlacementSetup
   comprueba su identidad y dimensiones antes de compilar.
4. ARBeamDiagrams valida nodos, sección, longitud, muestras finitas y cierres
   de fuerzas/momentos para los cinco casos.
5. [Registro de compilación v4](../Unity/Builds/AR_Resultados_v4_build.log):
   comprobaciones de escena y geometría aprobadas, cinco mensajes
   AR DIAGRAM CHECK PASS y AR PLACEMENT BUILD: Succeeded.
6. El usuario confirmó la colocación v2 y la visualización M/V v3 en el teléfono.
   Falta incorporar fotos o video que documenten el ID, el elemento físico y
   los resultados en una misma toma.

El mapa de StreamingAssets coincide por SHA-256 con el de resultados/11_mapa_visor:

~~~text
C846CE7014705E4F4BB5D46986C9B496390C5C1375BA5DE7CB1A6AEEA22194F7
~~~

Esto verifica que la app utiliza la misma fuente de datos del visor.

---

## 5. QA final estructural

Se distingue entre verificaciones previas conservadas, comprobaciones repetidas
en este cierre y validación física pendiente. Esta semana no se cambió el modelo
estructural ni se repitió el análisis OpenSees completo.

| Prueba | Estado |
|---|---|
| Equilibrio G | **OK en resultados previos:** error exportado 0.0 y todas_ok_eq=True. Evidencia: verificaciones_casos_excel.csv y resultado G. No se repitió la corrida global. |
| Equilibrio Q | **OK en resultados previos:** error exportado 0.0 y todas_ok_eq=True. Misma evidencia para Q. No se repitió la corrida global. |
| Corte basal EX | **OK en resultados previos:** F esperada y aplicada=16650.7931 kN, error exportado 0.0. |
| Corte basal EY | **OK en resultados previos:** F esperada y aplicada=16650.7931 kN, error exportado 0.0. |
| Superposición | **PASS del motor C# repetido:** 147945 comprobaciones sobre el mapa activo. **Con observación** frente a corridas FE: error relativo de desplazamientos de 6.78e−9 a 8.422e−9, superior al umbral 1e−10; reacciones y fuerzas sí lo cumplen. |
| M-phi | **Calculada y contrastada previamente:** curva de columna 70×70; momento en flexión pura de fibras=1232.69 kN·m. Comparación H.A.=1214.42 kN·m, diferencia 1.505 %. No se regeneró el análisis de fibras esta semana. |
| P-M columna | **Calculada y contrastada previamente:** columna 70×70, diferencia en el punto balanceado=1.540 % según verificacion_rc.json. Permanece en el laboratorio de escritorio; no se incorporó a AR. |
| P-M muro | **Calculada y contrastada previamente:** muro 30×356, diferencia balanceada=2.427 % y en flexión pura=7.140 %. No se regeneró esta semana ni se incorporó a AR. |
| IDs Unity | **OK en datos y viga AR:** 722 registros del contrato y 722 del mapa, sin IDs duplicados ni IDs del mapa ausentes en el contrato. Build comprueba exactamente un ElementTag 185. La unicidad de todos los objetos del visor en Play Mode no se reaudita en este cierre. |
| AR | **Validación funcional del usuario para v2/v3; build v4 aprobado.** Escala, independencia de cámara, movimientos y cambio de ancla comprobados en Unity. Pendientes: ensayo físico v4, medición de precisión y evidencia fotográfica. |

Los 722 registros del contrato incluyen categorías que no corresponden uno a uno
con barras FE. El resumen del análisis exportado informa 701 elementos
estructurales y 516 nodos; son conteos diferentes y no se deben intercambiar.

### 5.1 Fuentes del QA estructural

- [Verificaciones por caso](../resultados/08_verificacion/verificaciones_casos_excel.csv).
- [Superposición: tres combinaciones](../resultados/06_superposicion/verificacion_3combinaciones.csv).
- [Contraste RC](../resultados/08_verificacion/verificacion_rc.json).
- [Curva M-phi](../resultados/07_capacidad/mom_curv/mom_curv_columna_70x70.json).
- [P-M columna](../resultados/07_capacidad/pm_columnas/pm_columna_70x70.json).
- [P-M muro](../resultados/07_capacidad/pm_muros/pm_muro_30x356.json).
- [Prueba del motor Unity](../tests/test_viewer_combination.ps1).
- [Antecedentes Semana 5](semana05.md): suite Python histórica de 35 pruebas.

Los ceros exportados son valores almacenados con la precisión del archivo.
No se presentan como una nueva demostración de residuo exactamente cero en
aritmética de precisión completa. El entorno Python disponible en esta revisión
no tiene pytest ni OpenSeesPy; por eso no se declara una nueva ejecución de
las 35 pruebas Python.

### 5.2 Cierre de diagramas de la viga 185

Comprobaciones repetidas utilizando el parser y ElementDiagrams reales en C#:

| Caso | Error de momento [kN·m] | Error de cortante [kN] | Axial y desplazamientos |
|---|---:|---:|---|
| G | 2.690e−6 | 1.070e−6 | Cierre N aprobado; desplazamientos finitos |
| Q | 1.500e−8 | 1.776e−14 | Cierre N aprobado; desplazamientos finitos |
| EX | 1.000e−8 | 0 | Cierre N aprobado; desplazamientos finitos |
| EY | 2.000e−8 | 0 | Cierre N aprobado; desplazamientos finitos |
| COMBO | 3.232e−6 | 1.284e−6 | Cierre N aprobado; desplazamientos finitos |

El criterio de cierre de los diagramas es absoluto: 1e−4 kN para fuerzas y
1e−4 kN·m para momentos. Es distinto del umbral de 1e−10 de equilibrio y
superposición del proyecto. No se afirma que estos residuos cumplan 1e−10.
También se contrastaron q por caso y la superposición de desplazamientos nodales.

### 5.3 Compilación y entrega Android

| Campo | Valor verificado |
|---|---|
| Unity | 6000.6.0f1 |
| AR Foundation / ARCore | 6.6.2 |
| Paquete Android | com.grupo6.p1.arplacement |
| Versión | 0.4.0; versionCode=4 |
| Arquitectura | arm64-v8a |
| Android mínimo | API 29 |
| APK | Unity/Builds/P1_Grupo6_AR_Resultados_v4.apk |
| Tamaño del archivo APK | 41453270 bytes |
| Estado | Build Succeeded; firma APK verificada |
| Instalación | Manual: transferir APK e instalar como actualización |

SHA-256 del APK:

~~~text
ED31BB9DE6C097DEE0FD56B18E6C53C6CFB0FD72D7522367A787D33923FB1DBC
~~~

La compilación se ejecuta mediante
[Compilar_Viga_AR_v4.cmd](../Compilar_Viga_AR_v4.cmd), que llama a
[scripts/build_ar_results.ps1](../scripts/build_ar_results.ps1).
El script verifica que el APK sea nuevo y que el registro informe éxito.
La compilación y la firma no sustituyen la prueba de visualización en el teléfono.

---

## 6. Errores conocidos y límites pendientes

1. **Primer flujo con marker sin validación física satisfactoria.** El usuario
   reportó ubicación incorrecta, seguimiento aparente del teléfono y problemas
   de escala. Se sustituyó por colocación manual; el reconocimiento automático
   del elemento físico sigue pendiente.
2. **Correspondencia física incompleta.** El ID y los resultados coinciden en
   el contrato, el JSON y el objeto AR. Falta registrar la superposición sobre
   la viga instalada del edificio con fotografía o video.
3. **Precisión no medida.** No hay valores experimentales de alineamiento ni
   deriva. El error angular aumenta con los 10 m de longitud; estabilidad
   visual no implica alineamiento exacto.
4. **Deriva y pérdida de seguimiento.** La iluminación, textura del entorno y
   movimiento del teléfono afectan ARCore. El anchor no garantiza ausencia
   de deriva.
5. **Sin persistencia entre sesiones.** Reiniciar exige volver a colocar la viga.
6. **Viga fija.** La app representa el ID 185; no incorpora selección automática
   de cualquier viga del edificio.
7. **Desplazamientos nodales, no curva continua de flexión.** La unión es lineal
   entre cuatro nodos. El máximo indicado es nodal y no demuestra el máximo
   interior del elemento.
8. **Amplificación visual.** Diagramas, desplazamientos y flechas se amplifican.
   Sus alturas en AR no deben leerse como mediciones físicas del edificio.
9. **Alcance de cargas nodales.** Las flechas de peso propio representan solo
   esta viga. No muestran la carga nodal total de todos los elementos conectados.
10. **Prueba v4 pendiente en hardware.** Axial, desplazamientos y cargas fueron
    implementados y comprobados en datos/build; todavía no tienen confirmación
    del usuario en el teléfono.
11. **Superposición FE frente al umbral estricto.** Los desplazamientos de las
    corridas históricas superan 1e−10, aunque cumplen la tolerancia histórica 1e−6.
    La aprobación del motor C# no elimina esta diferencia.
12. **Redondeo de datos exportados.** Los cierres de diagramas tienen residuos
    pequeños y las cargas totales redondeadas pueden diferir de q·L. Se conserva
    la distinción entre tolerancias y precisión de exportación.
13. **Idealización estructural.** Las losas no son elementos FE; sus cargas se
    transfieren por áreas tributarias. Existen restricciones verticales que
    representan sostén de losas y estabilización de componentes. El modelo
    global es elástico lineal y la capacidad se calcula por separado.
14. **Geometría con observaciones previas.** Los resultados conservan 9 huecos
    pendientes y 4 losas aisladas, aunque sus verificaciones exportadas indican
    conservación aprobada. Deben mantenerse visibles en la revisión del modelo.
15. **Capacidad RC con alcance previo.** Las comparaciones de fibras y bloque
    rectangular tienen diferencias documentadas, especialmente 7.14 % en la
    flexión pura del muro. No constituyen un nuevo cierre de diseño con factores
    de reducción φ. El campo histórico pico_fiber de verificacion_rc.json tampoco
    debe confundirse con el máximo global de la envolvente P-M.
16. **Dependencias AR.** Versiones anteriores de AR Foundation presentaron
    incompatibilidades con URP. La combinación utilizada en esta entrega es
    Unity 6000.6.0f1, URP 17.6 y AR Foundation/ARCore 6.6.2.
17. **Advertencia histórica de renderizado.** Semana 5 registró
    “Ran out of Graphics Ring Buffer space” en Editor; no se declara resuelta
    mediante la compilación Android.
18. **SQ4 permanece como prototipo previo.** El reparto didáctico de carga móvil
    del laboratorio no equivale a un reanálisis estructural exacto y no forma
    parte del flujo AR de esta entrega.

---

## 7. Cierre y próximos pasos

La Semana 6 permitió pasar del prototipo con marker a una representación de
la viga 185 a escala real, colocable y ajustable en el entorno. La confirmación
del usuario respalda el funcionamiento de v2 y de los diagramas M/V de v3.
La versión v4 amplía la consulta de resultados sin cambiar el análisis del edificio.

Para completar la validación física:

- [x] Colocación y ajuste funcionales confirmados en teléfono, versión v2.
- [x] Diagramas de momento y corte confirmados en teléfono, versión v3.
- [x] V4 compilada, identidad y datos comprobados, firma APK verificada.
- [x] Motor de superposición C# repetido: 147945 comprobaciones.
- [x] Correspondencia digital del ID 185, sus tramos FE y sus resultados.
- [ ] Confirmar en teléfono las nuevas vistas de v4.
- [ ] Medir escala, alineamiento y deriva con el procedimiento de §3.
- [ ] Incorporar fotos/video del elemento físico, ID y resultado.
- [ ] Ensayar el guion de defensa completo en el equipo de presentación.

**Defensa técnica:** explicar los ejes de OpenSees, la conversión a Unity, el
origen de la sesión AR, la escala 1:1, la rotación y traslación manuales, la
función del anchor, el procesamiento que realiza el teléfono y el análisis
estructural calculado previamente.