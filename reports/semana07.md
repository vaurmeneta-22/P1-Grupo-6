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
