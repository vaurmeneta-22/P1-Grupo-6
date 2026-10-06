# Informe de Avance — Semana 7: reanálisis OpenSees desde Unity

| Campo | Valor |
|---|---|
| **Proyecto** | P1 — Laboratorio Estructural Digital (Edificio de Ingeniería) |
| **Curso** | Métodos Computacionales (8vo semestre) |
| **Grupo** | 6 |
| **Período** | 5–9 de octubre de 2026 |
| **Fecha de corte de este informe** | 6 de octubre de 2026 |
| **Entregable** | Honor Track 4: solicitud, ejecución y verificación del reanálisis desde Unity |
| **Motor estructural** | Python + OpenSeesPy |
| **Interfaz** | Unity 6, Editor para PC |

## Objetivo y continuidad del proyecto

Las semanas anteriores construyeron el modelo estructural, sus análisis y
verificaciones, y los conectaron con el visor interactivo de Unity. La Semana 5
ya permitía aplicar modificaciones desde Unity mediante scripts Python/OpenSees.
La Semana 6 se enfocó en la visualización del elemento estructural en realidad
aumentada y en documentar sus límites de medición.

Durante la Semana 7 se completó un flujo para la pauta **H4 — Reanálisis OpenSees
en vivo**. En la pestaña **Modificaciones → Honor Track 4**, el usuario selecciona
un escenario, conecta el backend local y solicita el cálculo. Python/OpenSees
genera resultados nuevos y Unity los recibe para actualizar el modelo y comparar
los resultados.

**Distinción respecto al flujo previo:** Unity ya podía mostrar resultados
calculados previamente y tenía acciones de modificación que lanzaban procesos
Python desde C#. Honor Track 4 agrega una interfaz de servicio HTTP local para
conectar Unity con el backend, enviar una solicitud validada y devolver un
reporte de comparación junto con el modelo y el mapa actualizados. El servidor
no reemplaza a OpenSees: coordina la solicitud y ejecuta los scripts existentes.

**Estado al corte:** el usuario confirmó que el flujo Unity/backend funciona.
La evidencia detallada guardada en el repositorio corresponde a una ejecución
completa del **Caso B**, con las cinco combinaciones aprobadas al compararse con
una corrida directa y repetirse. A y C aparecen como opciones de la interfaz y
sus contratos se validan en las pruebas automatizadas; este informe no atribuye
una corrida numérica completa de esos dos casos a la evidencia guardada del
corte.

---

## 1. Escenarios disponibles

La pestaña permite seleccionar uno de tres escenarios didácticos. Cada escenario
parte del contrato base `Edificio.json` y se genera como una variante separada.

| Caso | Cambio aplicado antes del análisis | Comprobación de contrato |
|---|---|---|
| **A** | Viga 147: sección 60 × 80 → 50 × 75 cm. | Elemento 147 existe, es `beam_y` y tiene las dimensiones solicitadas. |
| **B** | Apoyo del nodo 1: empotrado → articulado, `DOF=[1,1,1,0,0,0]`. | Apoyo del nodo 1 conserva las tres traslaciones restringidas y libera los giros. |
| **C** | Columna 66: sección 70 × 70 → 40 × 40 cm. | Elemento 66 existe, es una columna y tiene las dimensiones solicitadas. |

En los tres escenarios se analiza el edificio completo. El reanálisis produce
los casos G, Q, EX, EY y COMBO; seleccionar un escenario no significa analizar
solo su elemento, sino modificar la entrada correspondiente y resolver el
modelo global.

---

## 2. Flujo Unity → backend → OpenSees → Unity

~~~text
Modificaciones → Honor Track 4
  → elegir Caso A / B / C
  → Conectar backend
  → Unity comprueba / inicia scripts/backend_opensees.py
  → POST HTTP local /reanalyze con el escenario
  → validación del contrato y generación de la variante
  → OpenSees resuelve G / Q / EX / EY / COMBO
  → se exportan el modelo, analysis_map y reporte
  → comparación con corrida directa y repetición
  → respuesta JSON del backend a Unity
  → Unity valida y guarda los datos de sesión; recarga el visor
~~~

### 2.1 Inicio y conexión

La conexión se inicia con el botón de Honor Track 4. Unity consulta
`http://127.0.0.1:8765/health`; si no hay un backend disponible, inicia
`scripts/backend_opensees.py` como proceso local oculto y espera que responda.
No se necesita abrir una terminal ni iniciar el servidor por separado. El
servicio escucha en loopback, es decir, en el mismo computador donde corre Unity.

La conexión es independiente de la ejecución del análisis: después de conectarse,
se pulsa **Ejecutar verificación** para enviar el escenario seleccionado. Unity
también ofrece desconectar el proceso que inició. La implementación limita esta
interfaz a Unity Editor en PC, donde están disponibles Python/OpenSees y la
ejecución de procesos locales.

### 2.2 Responsabilidades de cada parte

| Componente | Responsabilidad |
|---|---|
| Unity / `ModificationMode.cs` | Elegir el caso, iniciar o detectar el backend, enviar la solicitud, validar la respuesta y presentar el resultado. |
| `scripts/backend_opensees.py` | Servir `/health` y `/reanalyze`, validar el identificador y los parámetros del caso, ejecutar el verificador y devolver los archivos producidos. |
| `scripts/generar_modificaciones.py` | Regenerar las variantes A/B/C desde el contrato base, sin usar una modificación anterior como nueva base. |
| `scripts/verificar_h4.py` | Validar el modelo, provocar errores controlados, ejecutar el caso solicitado, hacer las corridas de referencia y crear los reportes de H4. |
| `scripts/ejecutar_modificacion.py` | Ejecutar OpenSees para las cinco combinaciones, exportar el mapa del visor y sincronizar los datos solicitados por Unity. |
| OpenSeesPy | Resolver el modelo estructural y producir fuerzas, desplazamientos, reacciones, resumen y verificaciones. |

### 2.3 Solicitud y respuesta

Unity envía un objeto JSON con `case_id` y los datos que identifican el cambio.
Por ejemplo, para B se envía el nodo 1 y el tipo de apoyo `pinned`; para A/C se
envían el ID del elemento y sus dimensiones esperadas. El backend comprueba que
el caso exista y que los valores concuerden con el escenario implementado.

La respuesta HTTP incluye estado de éxito, el JSON del modelo recalculado,
`analysis_map.json`, el reporte de verificación y el registro del solver. Unity
comprueba que el cambio recibido coincida con la selección y que el mapa y el
reporte sean JSON válidos antes de guardarlos en `Application.persistentDataPath`
y recargar la escena.

El servidor hace de puente de comunicación y proceso. El cálculo estructural
sigue ocurriendo en OpenSees ejecutado por Python; Unity no contiene el motor
OpenSees.

---

## 3. Validación y manejo de errores

El flujo realiza comprobaciones antes y durante la ejecución:

- El cuerpo de la solicitud debe ser JSON y debe identificar un caso A, B o C.
- El modelo debe contener listas válidas de nodos y elementos, IDs no duplicados,
  referencias a nodos existentes y dimensiones positivas y finitas para los
  elementos estructurales.
- Se comprueba la condición específica del escenario: sección de la viga,
  condición de apoyo o sección de la columna.
- Se verifican los archivos de modelo, mapa y reporte antes de responder a Unity.
- Unity vuelve a comprobar el cambio objetivo, el mapa y el identificador del
  reporte antes de aplicar los datos recibidos.
- El backend comunica errores de entrada, fallo del solver y timeout en la
  respuesta HTTP, junto con el detalle que Unity muestra en la pestaña.

El verificador ejecuta pruebas negativas intencionales: una dimensión estructural
inválida y un archivo de entrada faltante. Que el runner devuelva código distinto
de cero para el archivo faltante es el resultado esperado de la prueba de manejo
de errores, no un fallo del análisis válido.

---

## 4. Comparación y reproducibilidad

Para el caso elegido, el backend genera tres conjuntos identificables:

1. **Ejecución solicitada desde Unity**, que produce resultados con la etiqueta
   de la variante (por ejemplo, `modB`).
2. **Corrida directa**, que invoca el solver OpenSees directamente con el mismo
   archivo de modelo y los mismos casos.
3. **Repetición directa**, que vuelve a resolver el mismo modelo para comprobar
   reproducibilidad.

Se comparan los campos exportados: fuerzas globales de elementos,
desplazamientos, reacciones, resumen y verificaciones. La tolerancia numérica
declarada por el verificador es:

~~~text
|x − y| ≤ 1×10⁻⁸ + (1×10⁻⁹) × max(|x|, |y|)
~~~

Unity muestra filas por G/Q/EX/EY/COMBO con el valor entregado por la ejecución
solicitada, el valor de la corrida directa y la diferencia. La tabla resume
magnitudes relevantes para el escenario, mientras que el reporte JSON contiene
el detalle numérico de todos los campos comparados.

Una coincidencia demuestra que, para esas entradas y esa configuración, las
ejecuciones produjeron datos iguales dentro de la tolerancia. Si aparecen
diferencias, la comparación permite detectar el desacuerdo pero no identifica
por sí sola si su causa es el modelo, las cargas, la configuración del solver,
la exportación o la lectura de datos.

---

## 5. Evidencia de verificación al corte

El artefacto detallado de la última ejecución guardada es
[`resultados/12_h4/verificacion_h4.json`](../resultados/12_h4/verificacion_h4.json),
con versiones legibles en `.md` y `.txt`. El reporte registra el Caso B y las
siguientes comprobaciones:

| Comprobación | Resultado registrado | Evidencia |
|---|---|---|
| Modelo válido | **Aprobado** | 536 nodos, 722 elementos; apoyo del nodo 1 articulado; se rechazó la dimensión inválida de prueba. |
| Manejo de errores | **Aprobado** | Se detectaron tanto la entrada estructural inválida como el archivo de modelo faltante. |
| Resultados preparados | **Aprobado** | Se calcularon los cinco escenarios y se prepararon el modelo y el mapa para Unity. |
| Unity/backend vs corrida directa | **Aprobado** | Diferencia máxima registrada: 0 en G, Q, EX, EY y COMBO. |
| Repetibilidad | **Aprobado** | Diferencia máxima registrada entre la corrida directa y su repetición: 0 en los cinco casos. |

El reporte numérico registra 20 539 comparaciones para G, 20 540 para Q,
20 543 para EX, 20 543 para EY y 20 539 para COMBO en cada conjunto de
comparación. La salida quedó idéntica en los campos numéricos y no numéricos
exportados para esta ejecución.

La compilación C# se comprobó con el compilador incluido con Unity 6000.6.0f1:
no hubo errores de compilación. Permanecen advertencias de API obsoleta en
`EdificioLoader.cs`; no impidieron compilar ni entrar a Play Mode. El usuario
confirmó en Unity que el flujo funcional también corre desde la interfaz.

### Archivos principales

- [`Unity/Assets/Scripts/ModificationMode.cs`](../Unity/Assets/Scripts/ModificationMode.cs): interfaz, control del backend y recepción de resultados.
- [`scripts/backend_opensees.py`](../scripts/backend_opensees.py): servidor HTTP local y contrato de solicitud.
- [`scripts/verificar_h4.py`](../scripts/verificar_h4.py): validación, corridas, comparación y reporte.
- [`scripts/generar_modificaciones.py`](../scripts/generar_modificaciones.py): creación reproducible de casos A/B/C.
- [`scripts/ejecutar_modificacion.py`](../scripts/ejecutar_modificacion.py): ejecución y sincronización del análisis.
- [`resultados/12_h4/verificacion_h4.md`](../resultados/12_h4/verificacion_h4.md): resumen humano de la ejecución más reciente.

---

## 6. Ajustes complementarios del visor 3D

Junto al flujo H4 se incorporaron mejoras de presentación y lectura del modelo
en Unity. Estos cambios son visuales: no alteran la línea base del análisis ni
reemplazan la geometría del contrato estructural.

| Mejora | Implementación | Alcance |
|---|---|---|
| Muros superiores | Para los IDs 299, 309, 319, 324, 467, 468, 482 y 483, el visor usa la segunda dimensión declarada en `section` para construir la longitud visible del muro. | Corrige su representación en Unity sin reescribir dimensiones del JSON estructural ni recalcular resultados. |
| Vigas junto a losas | Vigas 240 y 241 se alinean visualmente con la cara superior de las losas adyacentes, considerando el espesor y desfase visual configurados para las losas. | Evita que la representación quede por debajo o solapada con la losa; es un ajuste de renderizado. |
| Terreno | Se genera una capa de terreno con una superficie baja hasta el fondo visual de las zapatas y una plataforma/corte escalonado para el grupo de zapatas en cota superior. | Se muestra como capa `Terreno`, que puede ocultarse con el control de visibilidad. Es una representación esquemática de cotas, no un modelo geotécnico. |
| Gráficos de Datos | Los gráficos 2D incorporan escalas numéricas en ambos ejes, título y unidades más legibles, marcador de máximo destacado y texturas reutilizadas mientras los datos y el tamaño no cambien. | Mejora lectura y reduce recreaciones del gráfico durante el repintado de la interfaz. |
| Paneles de curvas | La vista Momento–Curvatura y P-M ajustan su altura al tamaño de pantalla; el panel organiza mejor la curva y su resumen numérico. | Hace más legible el panel en ventanas estrechas y evita que una curva deje un gran espacio vacío. |

Estos ajustes pertenecen al visor de Unity; la app AR de Semana 6 mantiene su
alcance propio de colocación de la viga 185. No se afirma que el terreno modele
estratos, propiedades de suelo ni interacción suelo-estructura.

---

## 7. Alcance y límites

1. El backend es local al computador; no es un servidor remoto ni permite que
   otra máquina se conecte.
2. La operación requiere Unity Editor en PC, Python y las dependencias del
   proyecto, incluido OpenSeesPy.
3. La solicitud usa escenarios definidos previamente. No es todavía un editor
   libre de geometría, materiales, cargas o cualquier parámetro del modelo.
4. Los resultados coincidentes verifican el recorrido de datos y cálculo para
   el escenario probado, pero no certifican que las hipótesis del modelo
   representen completamente el edificio real.
5. El reporte de esta fecha documenta una ejecución completa del Caso B. Las
   validaciones de entrada A/C pasan en las pruebas; queda guardar reportes
   completos individuales de esos escenarios para ampliar la evidencia.
6. El punto de control de esta semana es el análisis global lineal del modelo.
   No se implementó en esta tarea un nuevo solver no lineal ni un reanálisis
   de curvas P-M.
7. Al fallar el análisis, Unity conserva el detalle del error y no debe tratar
   una respuesta incompleta como modelo válido.

---

## 8. Conclusión y checklist

Honor Track 4 extiende el laboratorio desde la consulta de resultados ya
calculados hacia una solicitud de reanálisis explícita desde Unity. El backend
recibe la modificación, coordina Python/OpenSees y devuelve resultados,
reportes y el mapa necesario para actualizar el visor. La comparación directa
y la repetición permiten demostrar que el flujo produjo los mismos resultados
para el escenario registrado.

- [x] Pestaña de Honor Track 4 dentro de Modificaciones.
- [x] Selección de casos A, B y C con descripción del cambio.
- [x] Botones para conectar/desconectar y ejecutar desde Unity, sin iniciar una terminal manualmente.
- [x] Backend local Python HTTP con rutas de salud y reanálisis.
- [x] Validación de solicitud, contrato estructural y respuesta.
- [x] Manejo reportado de entradas inválidas, archivo faltante y fallos de ejecución.
- [x] Reanálisis de G/Q/EX/EY/COMBO y comparación directa + repetición.
- [x] Caso B documentado con todos los controles aprobados y diferencia máxima cero.
- [x] Compilación C# sin errores; advertencias de API obsoleta pendientes de limpieza.
- [x] Ajustes visuales del visor: dimensiones representadas de muros superiores, alineamiento de vigas 240/241, terreno escalonado y gráficos legibles.
- [ ] Guardar ejecución completa de H4 para A y C en reportes independientes.
- [ ] Ensayar y archivar evidencia visual del flujo de cada escenario en Unity.

**Siguiente paso recomendado:** ejecutar A y C desde la misma pestaña, guardar
los reportes resultantes y verificar que Unity muestre el modelo y los
resultados del escenario correcto después de cada recarga.

---

## 9. Nuevo Honor Track: H1 — Google Cardboard VR — hasta +4

Esta ampliación de Semana 7 incorpora un segundo Honor Track: **H1 — Google
Cardboard VR**, además de H4, documentado en las secciones anteriores. Se integró
un recorrido del edificio en la misma aplicación Android que contiene el modo AR
para la viga 185. El acceso **Visualizador VR** aparece en el menú y en la esquina
inferior derecha del modo AR.

El desarrollo comenzó con el piso 3 y se amplió a los **pisos 1, 2, 3 y 4**.
Permite recorrer la estructura, seleccionar elementos y consultar resultados
OpenSees y curvas de capacidad desde el teléfono. La versión final al corte es
**v11, versión 0.6.1, código Android 11**.

### 9.1 Correspondencia con los requisitos de la pauta

| Requisito H1 | Implementación realizada | Comprobación y alcance |
|---|---|---|
| **Render estereoscópico** | Google Cardboard XR Plugin genera la vista para ambos ojos y la distorsión óptica del visor. El panel y los gráficos se dibujan en el espacio 3D, visibles en ambos ojos. | Se verificó la configuración de ambos ojos y se compiló el SDK nativo en Android. La vista previa del Editor está identificada como **sin estéreo**; falta archivar la comprobación física con visor Cardboard. |
| **Head tracking** | La orientación de la cámara sigue el giro del teléfono/cabeza mediante `TrackedPoseDriver`, actualizado también antes del renderizado. Se permite recentrar la orientación. | Se verificó el controlador de orientación. La posición la controla la locomoción; no se añade desplazamiento físico de cabeza que produzca deriva del recorrido. |
| **Locomoción** | Cuatro flechas: avanzar, retroceder, izquierda y derecha. Se usa una cápsula de colisión y apoyo sobre losas reales; hay selector de pisos y retorno a la posición inicial. | Play Mode comprobó movimiento, ubicación segura, colisiones, límites y cruces de la junta en ambos sentidos en los cuatro niveles. |
| **Selección de elementos** | Una mira permite seleccionar vigas, columnas, muros y elementos metálicos por permanencia de mirada o pulsador Cardboard. Se conserva el ID original del elemento. | Se probaron selección, apertura/cierre de fichas, pausa de movimiento durante la consulta y correspondencia de IDs con el mapa de resultados. |
| **Resultados OpenSees** | Las fichas consultan G, Q, EX, EY y COMBO desde `analysis_map.json`, compartiendo el motor de lectura y diagramas del visor de escritorio. | Se comprobaron datos finitos, unidades, resultados por piso y cierres de diagramas. El teléfono muestra resultados exportados; este recorrido no ejecuta OpenSees ni utiliza el backend H4. |
| **Interacción con diagramas/capacidad** | Vistas de axial N, corte V, momento M, planos x-z/x-y, consulta de muestras, curva P-M y referencia momento-curvatura. | Se probaron los cinco casos, cambio de vista, plano y muestra, render de P-M y momento-curvatura. Una capacidad ausente se informa, sin sustituirla por la de otro elemento. |

Los seis puntos tienen implementación y comprobaciones digitales. Esto no
representa una asignación de puntaje: la evaluación de la pauta y la evidencia
física completa del visor corresponden a la entrega y revisión del curso.

### 9.2 Integración AR/VR y flujo de uso

La aplicación conserva el paquete Android `com.grupo6.p1.arplacement`, de modo
que el APK se instala como actualización de la app existente. ARCore y Cardboard
están registrados; se inicia el proveedor del modo elegido y se detiene el
anterior al cambiar de escena. El teléfono pasa a horizontal al entrar en VR y
vuelve a vertical al regresar al menú o al modo AR.

~~~text
Menú / modo AR → Visualizador VR
  → iniciar Cardboard y cargar geometría + resultados del APK
  → aparecer en un punto seguro del piso 3
  → recorrer con cuatro flechas
  → elegir Piso 1 / 2 / 3 / 4 debajo de las flechas
  → reubicarse en un punto libre del nivel elegido
  → mirar un elemento y abrir su ficha
  → consultar caso, N/V/M, plano, muestras y capacidad
  → Recorrer piso para cerrar la ficha
  → Inicio para regresar al menú
~~~

- Mirar una flecha durante **0.7 s** inicia el movimiento; dejar de mirarla lo
  detiene. El pulsador sobre una flecha produce un paso corto. La velocidad
  inicial es **0.8 m/s**.
- Mirar un elemento durante **1 s** abre su ficha. Los botones de interfaz,
  incluidos los de piso, se activan por mirada de **1.1 s** o pulsador.
- **Centrar panel** recupera los controles frente a la mirada; **Volver al
  inicio** restablece la posición del piso actual.
- La rueda de Cardboard permite configurar el visor mediante su QR. Mantener
  el pulsador tres segundos y soltar recentra la orientación y el panel.
- En Editor se dispone de una vista previa: ratón con clic derecho para mirar,
  WASD/flechas para moverse y clic izquierdo para seleccionar. Esta prueba no
  reemplaza el render estereoscópico nativo en el teléfono.

### 9.3 Geometría y recorrido de los cuatro pisos

La geometría usa el mismo constructor del visor, `EdificioLoader.BuildSolids`,
con las correcciones visuales existentes. Se preservan las coordenadas del
contrato, la conversión de centímetros a metros, el espejo X y los IDs.
Cada nivel incluye sus losas inferiores, elementos de su volumen y losas
superiores como techo; estas últimas tienen material claro opaco, visibles
por ambas caras, y espesor tomado del campo `t` del contrato.

| Piso | Elementos activos | Losas de circulación | Losas de techo | Diagramas verificados | Elementos con capacidad disponible |
|---|---:|---:|---:|---:|---:|
| **1** | 207 | 27 | 41 | 1390 | 43 |
| **2** | 261 | 41 | 45 | 1750 | 44 |
| **3** | 274 | 45 | 48 | 1810 | 40 |
| **4** | 284 | 48 | 38 | 1980 | 56 |

Las cifras se verifican por nivel; no deben sumarse como elementos únicos del
edificio, pues el techo de un piso también pertenece al nivel siguiente.
Solo el piso activo mantiene geometría y colisiones habilitadas. Los niveles
ya construidos se reutilizan al regresar a ellos, evitando reconstruirlos
cada vez y manteniendo IDs únicos en la geometría activa.

La altura de circulación se obtiene de las losas del nivel. El piso 4 tiene
una diferencia de **1.5 cm** entre grupos de losas: la cápsula se ubica sobre
la cota visual más alta sin cambiar sus dimensiones. Cambiar de piso reubica
al visitante; no se implementó un ascenso físico por escaleras. No se inventan
losas para completar zonas ausentes del contrato ni se rellenan sus huecos.

### 9.4 Solución del cruce de la junta de dilatación

La junta deja una separación de **45–60 cm** entre las losas de ambos bloques.
La protección contra caída impedía cruzarla porque no había suelo bajo el
visitante. Se incorporó un **cubrejunta exclusivo de navegación VR**, calculado
por separado para cada piso.

Primero se encuentran franjas donde hay losas utilizables a ambos lados;
después se recortan usando las colisiones reales de muros y otros obstáculos
a la altura del visitante, considerando el radio de su cápsula de **22 cm**.
En los cuatro pisos queda un paso libre en el corredor central. El cubrejunta
tiene material gris oscuro, espesor visual de 3 cm y collider.

La solución conserva el bloqueo de los cruces con muros y excluye la estrecha
franja junto al hueco de escaleras. Tampoco cubre otros huecos o los bordes del
edificio. El cubrejunta no posee `ElementTag` ni ID estructural: no modifica
`Edificio.json`, cargas, condiciones de apoyo o resultados OpenSees.

Las pruebas con colisiones reales verificaron el cruce en ambos sentidos a
Z=8.5 m y Z=9.0 m en los cuatro niveles, así como la protección de escaleras
y de las zonas con muros junto a la junta.

### 9.5 Controles y mejoras de presentación

Se resolvió el problema de los controles que quedaban detrás al girar: el panel
acompaña la orientación horizontal. La dirección para avanzar se guarda antes
de elegir una flecha; mirar el botón lateral no cambia la dirección del pasillo.
Al consultar resultados, la ficha permanece fija y pausa la locomoción.

La versión v11 coloca los botones **Piso 1 / Piso 2 / Piso 3 / Piso 4 justo
debajo de las flechas**. Inicio, Centrar panel y Volver al inicio quedan en la
última fila, liberando la parte superior de la vista. Al bajar la mirada hacia
el selector, el panel se mantiene fijo, incluso al girar entre botones o sus
espacios; vuelve a acompañar el giro al mirar hacia el pasillo. El seguimiento
natural de cabeza permanece activo. Apuntar a un botón no desplaza al visitante;
la reubicación ocurre al activar el cambio de piso.

También se corrigió la orientación visual de momentos: **negativos arriba y
positivos abajo**, manteniendo el signo real de los valores y las etiquetas.
La misma convención se aplicó al diagrama My de la viga colocada en AR; su
leyenda indica naranja negativo arriba y cian positivo abajo. Corte y axial
conservan su orientación. El cambio es de representación, sin recalcular ni
invertir los resultados estructurales.

La carga Android se corrigió reemplazando la mira esférica por un anillo con
`LineRenderer`. Se añadieron etapas visibles de carga, lectura del APK mediante
URI, timeout de 20 s y manejo de errores. **Inicio** sigue disponible si la
carga falla. El usuario confirmó que el edificio y el recorrido inicial cargan
y funcionan en el teléfono después de esta corrección.

### 9.6 Diagramas, unidades y capacidad

Las fichas conservan las unidades físicas: N y V en kN, M en kN·m, posiciones
en m y curvatura en 1/m. Se puede cambiar de caso, plano y muestra, consultar
extremos y ver la demanda junto a la capacidad P-M disponible para el elemento.
Las vigas subdivididas conservan sus tramos FE al construir los diagramas.

La vista momento-curvatura se identifica como **referencia de columna 70×70
con P=0**. No se presenta como la curva real de cualquier elemento seleccionado
ni como una respuesta recalculada para cada caso de carga global. La capacidad
P-M se obtiene con las reglas compartidas del visor; si falta, se indica en
la ficha. El recorrido VR no constituye un nuevo análisis no lineal.

### 9.7 Evidencia y estado de validación

La compilación v11 y la prueba real en Play Mode aprobaron:

- Selección de los cuatro pisos mediante sus botones, cambios repetidos y
  ubicación inicial con apoyo sobre losas y libre de obstáculos.
- Panel y visitante sin desplazamiento al apuntar a los botones de piso;
  raycasts que alcanzan el botón correspondiente.
- Cuatro direcciones, seguimiento de giro y conservación de dirección al
  mirar flechas laterales; pausa al abrir fichas.
- Cruces de junta en ambos sentidos por nivel, protección de huecos y
  colisiones que impiden atravesar muros.
- IDs, unidades, losas de piso y techo, muestras finitas, cinco casos y dos
  planos, gráficos de resultados y curvas de capacidad disponibles.
- Salida al menú y segunda entrada al recorrido sin errores de ejecución.

Todos los niveles conservan los cierres N/V/M dentro del umbral de
**1×10⁻⁴ kN/kN·m**; el residuo máximo de M registrado es aproximadamente
**3.02×10⁻⁵ kN·m** y el de V **6.78×10⁻⁶ kN**. Estos son cierres de diagramas
con valores exportados, no el umbral de equilibrio del análisis global.
No se volvió a resolver el modelo estructural para esta ampliación VR.

| Artefacto | Evidencia registrada |
|---|---|
| `Unity/Builds/H1_floor1_checks.json` a `H1_floor4_checks.json` | Verificaciones por piso, geometría, IDs, diagramas, capacidad y un paso central sobre la junta. |
| `Unity/Builds/H1_v11_play.log` | `H1 PLAY CHECK: PASS`; selección estable, navegación y regresión funcional de los cuatro niveles. |
| `Unity/Builds/AR_VR_v11_build.log` | `H1 MOBILE BUILD: Succeeded`; compilación Android completada. |
| `Unity/Builds/H1_navigation_preview.png` y vistas de pisos | Capturas inspeccionadas del panel, selector inferior y geometría del recorrido. |
| `Unity/Builds/P1_Grupo6_AR_VR_v11.apk` | Versión 0.6.1, código 11; **46 663 432 bytes**; firma compatible con la app anterior. |

SHA-256 del APK v11:
`FDE4437DF2779EE690E6B336D94F677F27938BD73A1514C8707A17A5179F0508`.
Los archivos `Edificio.json` y `analysis_map.json` empaquetados coinciden con
sus fuentes en StreamingAssets. Los artefactos de `Unity/Builds` son salidas
locales de compilación; pueden regenerarse con los métodos de verificación.

La compilación se reproduce cerrando Unity y ejecutando desde la raíz:

~~~powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_mobile_vr.ps1
~~~

**Estado físico al corte:** el usuario confirmó carga y funcionamiento del
recorrido inicial en el teléfono. Queda confirmar y archivar en el teléfono
la versión final v11: los cuatro pisos, selección inferior estable, cruce de
juntas y consultas. La comprobación completa de ambos ojos y head tracking con
un visor Cardboard real permanece pendiente; Play Mode y capturas del Editor
no sustituyen esa evidencia.

### 9.8 Archivos y checklist de H1

- [`reports/H1_Cardboard_VR.md`](H1_Cardboard_VR.md): documentación técnica, uso y evolución v5–v11.
- [`VRFloorModel.cs`](../Unity/Assets/Scripts/VRFloorModel.cs): selección de geometría, apoyo y pasos de junta por piso.
- [`VRFloorTour.cs`](../Unity/Assets/Scripts/VRFloorTour.cs): carga, locomoción, colisiones, cambio de nivel y selección.
- [`VRWorldUI.cs`](../Unity/Assets/Scripts/VRWorldUI.cs): panel en ambos ojos, controles, selector inferior y gráficos.
- [`VRResults.cs`](../Unity/Assets/Scripts/VRResults.cs): fichas, casos de carga, diagramas y capacidad.
- [`MobileLabMenu.cs`](../Unity/Assets/Scripts/MobileLabMenu.cs): acceso y transición AR/VR.
- [`ARBeamDiagrams.cs`](../Unity/Assets/Scripts/ARBeamDiagrams.cs): orientación visual de momentos en la viga AR.
- [`VRMobileSetup.cs`](../Unity/Assets/Editor/VRMobileSetup.cs): escenas, verificación por piso y compilación Android.
- [`VRPlayCheck.cs`](../Unity/Assets/Editor/VRPlayCheck.cs): pruebas reales de navegación e interacción en Play Mode.
- [`scripts/build_mobile_vr.ps1`](../scripts/build_mobile_vr.ps1): compilación del APK actual.

- [x] Integración del SDK Cardboard para render estereoscópico y head tracking.
- [x] Recorrido de pisos 1, 2, 3 y 4 con cuatro flechas y colisiones.
- [x] Selector debajo de controles, fijo durante selección y sin movimiento del visitante al apuntar.
- [x] Techos mediante losas reales y ubicación segura por nivel.
- [x] Paso sobre la junta calculado y probado por piso, sin atravesar muros ni cerrar escaleras.
- [x] Selección por mirada/pulsador con ID original y consulta de resultados OpenSees.
- [x] Diagramas N/V/M, casos, planos, muestras y capacidad disponible.
- [x] Momentos negativos arriba y positivos abajo en VR y en el diagrama de la viga AR.
- [x] Carga Android corregida, estados visibles y manejo de errores.
- [x] Pruebas digitales y compilación del APK v11 aprobadas.
- [ ] Confirmar y archivar navegación e interacción de v11 en el teléfono.
- [ ] Archivar evidencia física de estéreo y seguimiento de cabeza con visor Cardboard.
