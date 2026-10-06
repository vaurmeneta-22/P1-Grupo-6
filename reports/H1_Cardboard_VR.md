# H1 — Google Cardboard VR · pisos 1 a 4

## Alcance implementado

Una app Android con menú inicial y acceso **Visualizador VR** en la esquina
inferior derecha. El menú ofrece AR de la viga 185 y recorrido VR de los pisos 1 a 4.
El APK conserva `com.grupo6.p1.arplacement` para actualizar la app AR instalada.
Versión 0.6.1 / código 11.

- Render estereoscópico y distorsión óptica mediante el SDK oficial Google
  Cardboard XR Plugin 1.35.0, fijado al commit
  `36ac9815b8f191fe11e149b7f323368fa86655a6` en manifest y lock de paquetes.
- Seguimiento de orientación con `TrackedPoseDriver` antes de renderizar.
  La posición del visitante la controla la locomoción; el teléfono orienta la mirada.
- Cuatro flechas: avanzar, retroceder, izquierda y derecha. La locomoción es
  horizontal respecto a la mirada, con cápsula de colisión y comprobación de
  soporte sobre la unión de losas existentes. La velocidad inicial es 0.8 m/s.
- Selección con mira, permanencia de mirada y pulsador del Cardboard.
- Consulta G/Q/EX/EY/COMBO desde el mismo JSON y motor C# del visor de escritorio.
- Diagramas N/V/M en ambos planos locales, consulta de muestras y extremos.
  Únicamente en el diagrama de momento M, negativos arriba y positivos abajo;
  las etiquetas mantienen el signo físico del resultado.
- Consulta P-M con la curva asociada por las reglas de `PickHighlight.CapacityCur`
  y punto de demanda calculado por `PickHighlight.DemandaPM`, compartidos con el visor.
- Consulta momento-curvatura como **referencia de columna 70×70 a P=0**.
  No se presenta esta curva como curvatura real del elemento ni se hace depender
  de los casos de carga del modelo global.

## Datos y representación

El teléfono lee `Edificio.json` y `analysis_map.json` incluidos en el APK.
No ejecuta OpenSees ni se conecta al backend H4 para el recorrido.
La geometría la construye `EdificioLoader.BuildSolids`, compartiendo las
correcciones visuales del visor existente. Las coordenadas pasan de centímetros
a metros, con el mismo espejo X y conversión de altura usados por el visor.

Se seleccionan los elementos que delimitan la planta y el volumen del piso elegido.
La altura de circulación se obtiene de sus losas, incluyendo el espesor y
offset visuales utilizados por el visor. Los huecos de losas quedan excluidos
de las zonas transitables. El entorno representa la estructura disponible en
el modelo; no contiene un levantamiento arquitectónico adicional de tabiques,
puertas, muebles o terminaciones de pasillos.

Cada sólido conserva un `ElementTag` y su ID original. Las vigas subdivididas
conservan todos sus tramos FE mediante `ElementDiagrams.Construir`.
La ficha distingue unidades kN, kN·m, m y 1/m. Si falta una curva de capacidad
o un resultado se indica explícitamente, sin reemplazarlo por datos de otra sección.

## Uso

1. Instalar `Unity/Builds/P1_Grupo6_AR_VR_v11.apk` como actualización.
2. Abrir **Laboratorio Grupo 6** y pulsar **Visualizador VR**.
3. Poner el teléfono horizontal; escanear el QR del visor cuando Cardboard lo
   solicite, para usar sus parámetros ópticos. Introducir el teléfono en el visor.
4. Mirar una flecha durante 0.7 s para desplazarse. Dejar de mirarla detiene
   el movimiento. El pulsador sobre una flecha produce un paso corto. Los botones
   **Piso 1 / Piso 2 / Piso 3 / Piso 4**, debajo de las flechas, cambian de nivel por mirada (1.1 s) o pulsador.
   El recorrido inicia en el piso 3; cada cambio lleva a un punto libre de obstáculos.
5. Mirar un elemento durante 1 s o usar el pulsador para abrir su ficha.
6. Seleccionar caso, N/V/M, plano, P-M o M-curvatura con mirada o pulsador.
   Las flechas de muestra permiten consultar puntos de la curva.
7. **Recorrer piso** cierra la ficha. **Centrar panel** coloca los controles
   frente a la mirada. Mantener el pulsador tres segundos y soltar recentra
   la orientación de Cardboard y el panel.
8. **Volver al inicio** restablece la ubicación. **Inicio** o la X de Cardboard
   regresa al selector AR/VR. La rueda de Cardboard permite escanear otro visor.

La interfaz VR es un Canvas en el espacio 3D, visible en ambos ojos. Las
flechas acompañan el giro horizontal y se mantienen bajo la vista del usuario.
Al bajar la mirada para elegir un control se conserva la dirección del pasillo.
Las fichas de resultados conservan su orientación y pausan la locomoción.
Perder el foco de la aplicación también la pausa.

En Editor se puede abrir `VRFloor3.unity`: clic derecho y movimiento del ratón
para mirar, WASD/flechas para desplazarse y clic izquierdo para seleccionar.
Esta vista previa se identifica como **sin estéreo**; no valida el Cardboard.

## Compilación reproducible

Cerrar el editor Unity y ejecutar desde la raíz:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_mobile_vr.ps1
```

También existe `Lab > Móvil > Compilar APK AR + Cardboard VR`.
Se configuran las dependencias Android del SDK, entrada Activity y OpenGL ES 3.
Los proveedores ARCore y Cardboard se registran en el build; la app inicia
solamente el elegido y detiene el anterior después de descargar su escena.

Fuentes oficiales:
- [Quickstart de Google Cardboard para Unity](https://developers.google.com/cardboard/develop/unity/quickstart).
- [SDK oficial v1.35.0](https://github.com/googlevr/cardboard-xr-plugin/tree/v1.35.0).

## Validación y límites

`VRMobileSetup.Validate` verifica identidad, unidades, suelo de circulación,
cuatro flechas, colisiones, configuración de ambos ojos, orientación de cabeza,
muestras finitas en los cinco casos y ambos planos, render de las fichas de
diagramas, P-M y momento-curvatura. Su evidencia está en
`Unity/Builds/H1_checks.json` y el registro de compilación.

Verificación realizada el 6 de octubre de 2026:

- 274 elementos con IDs originales y 45 losas de circulación.
- 1810 diagramas en los cinco casos y ambos planos; 40 elementos con capacidad disponible.
- Cierre máximo: N = 0 kN, V = 6.78×10⁻⁶ kN y M = 3.02×10⁻⁵ kN·m.
- Suite existente de combinaciones: 147945 comprobaciones aprobadas.
- `VRPlayCheck.Run`: prueba real en Play Mode aprobada, incluyendo carga desde
  menú, selección, cinco vistas y cinco casos, cambio de plano y muestra,
  pausa al abrir fichas, desplazamiento sobre losas, salida y segunda entrada.
  No hubo errores de ejecución durante esta prueba. Registro:
  `Unity/Builds/H1_play_check.log`.
- APK Android compilado con éxito; contiene las bibliotecas nativas Cardboard
  y ARCore y los JSON de geometría y resultados.
  Primera versión: `P1_Grupo6_AR_VR_v5.apk`, 46655248 bytes.
  SHA-256: `A05491EAD5CC64551BC9603A9B7D5E67133C6F348E6D6261CE1A5CAADD4D8363`.
  La firma coincide con la del APK AR v4; ambos JSON dentro del APK coinciden
  byte por byte con sus fuentes de StreamingAssets.

La prueba de Play Mode puede repetirse cerrando Unity y ejecutando el editor
con `-batchmode -projectPath Unity -buildTarget Android -executeMethod VRPlayCheck.Run`
(sin `-quit`, porque el verificador cierra Unity al terminar).

El contraste digital reutiliza exactamente el motor y las convenciones del
visor de escritorio; no se afirma haber realizado un nuevo análisis estructural.
Los residuos N/V/M registrados son cierres de diagramas con datos exportados,
distintos del umbral de equilibrio del modelo global.

**La comprobación física en teléfono y visor Cardboard queda pendiente del usuario.**
Es necesario confirmar imagen de ambos ojos, orientación al girar la cabeza,
cuatro direcciones, detención, colisiones, selección, legibilidad de resultados,
regreso al menú y alternancia AR → VR → AR sin reiniciar la app.
La compilación y la vista previa de Editor no sustituyen esta evidencia.

## Corrección de carga en Android · v6

El usuario informó que aparecían los controles pero persistía el mensaje
«Cargando geometría y resultados OpenSees». Se encontró una ruta sin captura
de errores antes de leer el modelo: `CreatePrimitive(Sphere)` y el acceso
inmediato a su Collider. El build v5 no conservaba `SphereCollider` entre sus
tipos de escena ni en el código IL2CPP generado. Esta es una causa probable;
no se obtuvo un log del teléfono para confirmar su excepción concreta.

Se reemplazó la esfera por una mira circular con `LineRenderer`, sin Collider.
La carga distingue lectura del edificio, lectura de resultados y construcción
del piso. Las lecturas del APK usan URI con separadores `/` y un timeout de
20 segundos. El botón Inicio permanece disponible aunque la carga falle.
Las dimensiones, unidades y resultados estructurales no se alteraron.

La documentación de Unity advierte del fallo de `CreatePrimitive` cuando el
build elimina sus componentes necesarios:
[GameObject.CreatePrimitive](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/GameObject.CreatePrimitive.html).

La prueba `VRPlayCheck.Run` volvió a aprobar carga, reentrada y consultas
con la mira nueva (`Unity/Builds/H1_play_check_v6.log`). La compilación Android
v6 terminó correctamente, con los mismos 274 elementos y 1810 diagramas.
APK: `P1_Grupo6_AR_VR_v6.apk`, 46655436 bytes, versión 0.5.1 / código 6.
SHA-256: `F11F684DC03591F71B0E535FE7938742EC7F7C66A827109B2C9DCADCCE352D6D`.
La firma coincide con v5 y los JSON incluidos coinciden con StreamingAssets.
Queda pendiente confirmar en el teléfono que se resolvió el síntoma reportado.

El usuario confirmó que v6 carga el edificio correctamente en el teléfono.

## Techo y controles al girar · v7

Se identifica explícitamente el techo del piso 3 con las 48 losas reales del
nivel superior. Ya estaban incluidas en el volumen seleccionado; ahora tienen
material opaco claro, visibles por ambas caras, y espesor tomado de su campo
`t`: 44 losas de 15 cm y cuatro de 12 cm. Se preservan los IDs, posiciones,
huellas y huecos existentes.
Las 45 losas transitables conservan su altura anterior. Este ajuste es visual:
el JSON y el análisis estructural no cambian.

Los controles acompañan la orientación horizontal a 240 grados por segundo,
con margen de 3 grados para evitar movimientos pequeños del panel. Se colocan
a 1.7 m, con su centro 35 cm bajo los ojos. Cuando se mira hacia abajo más de
12 grados o se apunta a un botón, el panel permite selección sin perseguir
la mirada. Un giro mayor de 35 grados también recupera los controles aunque
se mantenga la mirada baja.

Avanzar, retroceder y desplazarse lateralmente usan la dirección del pasillo
guardada antes de elegir la flecha. Mirar el botón de derecha o izquierda no
modifica esa dirección. La ficha de resultados permanece quieta al leerla.

Las verificaciones comprueban las 48 losas opacas y su espesor, seguimiento de
un giro a la derecha, bloqueo al seleccionar y avance efectivo en el nuevo
pasillo. La prueba del comportamiento de v7 en el teléfono queda pendiente.

`H1_play_check_v7.log` registra la prueba aprobada de giro y avance real en
Play Mode, además de selección, cinco casos, cinco vistas, muestra, plano y
reentrada. `H1_checks.json` verifica 48 techos, 45 losas transitables y 1810
diagramas. Se inspeccionaron las capturas de navegación y techo.

Compilación v7 aprobada: `P1_Grupo6_AR_VR_v7.apk`, 46656024 bytes.
SHA-256: `000B06B9462D64AA84994BF31D662F0AEE864F482B6362C215620C8D9415BF5F`.
La firma coincide con la versión instalada y los JSON del APK coinciden con
StreamingAssets. Registro: `Unity/Builds/AR_VR_v7_build.log`.

## Cruce de la junta de dilatación · v8

La separación entre las losas de los dos bloques es de 45 o 60 cm en el
modelo. La protección contra caída rechazaba el avance por falta de suelo
bajo el visitante. Se agrega un cubrejunta exclusivamente para VR, al nivel
del suelo, en el corredor central libre entre los muros. Primero se intersectan
los bordes de las losas de ambos lados de la junta auditada
(X=-0.60/-0.45 hasta X=0, en coordenadas del visor). Después se recortan
las franjas con los bounds de los colliders reales a la altura del visitante,
incluyendo su radio de 22 cm para muros adyacentes.

No se cubre la franja junto al hueco de escaleras (Z=9.95 a 12.77 m): su
estrecha losa lateral no admite el ancho del visitante. Tampoco se cierran
otros huecos ni se cambia la protección de los bordes del edificio.

Los cubrejuntas tienen material gris oscuro, espesor visual de 3 cm y collider.
No tienen `ElementTag`, ni ID OpenSees, y se guardan separados de las 45 losas
reales. No modifican geometría JSON, cargas, restricciones ni resultados.
La comprobación cubre continuidad de apoyo en dos puntos del corredor central,
preservación de huecos y paso con colisiones reales en ambos sentidos.
Verificación de v8: compilación Android completada y comprobaciones H1 aprobadas
(274 elementos, 45 losas de circulación, 48 losas de techo, 1 paso central,
1810 diagramas y 40 capacidades). La prueba en Play Mode verificó el cruce del
corredor central en ambos sentidos con colisiones reales; se mantienen bloqueados
los muros y huecos de escaleras. Falta confirmar este cruce en el teléfono.

APK: `Unity/Builds/P1_Grupo6_AR_VR_v8.apk`, versión 0.5.3 (código 8),
46 659 500 bytes.
SHA-256: `CD4749F88111CFA3766BA6BCD4E3C29FDF01849B5A0EB087095258AD6E8FBEA8`.
La firma coincide con v7 y ambos JSON empaquetados coinciden con StreamingAssets.
Registro de compilación: `Unity/Builds/AR_VR_v8_build.log`.

## Orientación de momentos en AR · v9

En la viga colocada en AR, el diagrama My ahora muestra los valores negativos
arriba del eje cero y los positivos abajo, para G/Q/EX/EY/COMBO. Se invierte
únicamente la ordenada visual en `ARBeamDiagrams.Point`: muestras, signos,
extremos, unidades y colores siguen correspondiendo a los resultados OpenSees.
Las etiquetas usan la misma posición de la curva. La leyenda indica naranja
negativo arriba y cian positivo abajo. Corte y axial conservan su orientación.

La versión móvil 0.5.4 (código 9) incluye este ajuste y el cruce VR de v8.
La comprobación visual en el teléfono queda pendiente.

Compilación Android v9 completada; verificaciones H1 aprobadas (274 elementos,
1810 diagramas y 40 capacidades). APK: `Unity/Builds/P1_Grupo6_AR_VR_v9.apk`.
SHA-256: `FEBA6FC1EC3B1FA5E7CFCEC11D0DC9B3783B3978608998E57BCEA2E0F4445318`.
Registro: `Unity/Builds/AR_VR_v9_build.log`.

## Recorrido de los pisos 1–4 · v10

El recorrido inicia en el piso 3 y muestra cuatro botones de piso en el panel
que acompaña la mirada. Mirar un botón durante 1.1 s o usar el pulsador cambia
de nivel y ubica al visitante sobre una losa, libre de muros y columnas. La ficha
de resultados debe cerrarse antes de cambiar de piso. Cada nivel conserva la
selección de elementos y los resultados G/Q/EX/EY/COMBO, diagramas y capacidades
disponibles en el mapa. Los pisos ya construidos se reutilizan; solo el activo
mantiene geometría y colisiones habilitadas.

| Piso | Losas de circulación | Losas superiores / techo |
|---|---:|---:|
| 1 | 27 | 41 |
| 2 | 41 | 45 |
| 3 | 45 | 48 |
| 4 | 48 | 38 |

Las alturas provienen de las losas de cada piso. El piso 4 tiene una diferencia
de 1.5 cm entre grupos de losas: la cápsula se mantiene sobre la cota visual
más alta, sin alterar las losas. No se inventan techos ni se rellenan huecos.
El cambio de piso es una reubicación, no un recorrido físico de escaleras.

La junta se calcula por separado en cada nivel usando sus losas y los colliders
reales. Se mantiene el paso central libre, sin convertir el cubrejunta VR en
un elemento OpenSees. La prueba en Play Mode verificó cruces en ambos sentidos
a Z=8.5 y Z=9.0 m en los cuatro niveles, protección de los huecos de escaleras
y bloqueo de las zonas con muros junto a la junta. También probó cambios
repetidos mediante los botones reales, ubicación segura, resultados por piso,
pausa al consultar fichas, salida al menú y reingreso sin errores de ejecución.
Registro: `Unity/Builds/H1_multifloor_play.log`.

Las verificaciones por nivel se guardan en
`Unity/Builds/H1_floor1_checks.json` hasta `H1_floor4_checks.json`.
La prueba visual y de navegación de v10 en el teléfono queda pendiente.

Resultados de las comprobaciones por piso (compilación v10):

| Piso | Elementos activos | Diagramas verificados | Elementos con capacidad |
|---|---:|---:|---:|
| 1 | 207 | 1390 | 43 |
| 2 | 261 | 1750 | 44 |
| 3 | 274 | 1810 | 40 |
| 4 | 284 | 1980 | 56 |

Todos conservan IDs únicos en la geometría activa, 1 paso central sobre la junta,
losas y techos reales, y cierres de N/V/M dentro del umbral de 1e-4 kN/kN·m.

APK v10 compilado: Unity/Builds/P1_Grupo6_AR_VR_v10.apk; versión 0.6.0, código 10; 46663352 bytes.
SHA-256: 30D510E493BA45D897690BEF6A9F0625D1DD9853BC73A45C057962669679FE06.
Firma compatible con v9; Edificio.json y analysis_map.json del APK coinciden con StreamingAssets.
Registro de compilación: Unity/Builds/AR_VR_v10_build.log.

## Selector inferior y selección estable · v11

Los cuatro botones de piso se sitúan inmediatamente debajo de las flechas;
Inicio, Centrar panel y Volver al inicio quedan en la fila inferior. Se libera
la zona superior del recorrido. Mirar hacia la fila de pisos mantiene fijo el
panel, incluso al girar horizontalmente entre botones o sus espacios. Al volver
a mirar hacia el pasillo, el panel vuelve a acompañar el giro. El seguimiento
natural de la cabeza permanece activo; apuntar al selector no desplaza al
visitante. El cambio de ubicación sucede al activar el botón de piso.

Play Mode comprobó con raycasts reales que se alcanza cada botón sin que cambie
su posición ni la del visitante, y repitió navegación, resultados y cruces de
junta en los cuatro niveles. Registro: `Unity/Builds/H1_v11_play.log`.
La verificación visual en el teléfono queda pendiente.

APK v11 compilado: Unity/Builds/P1_Grupo6_AR_VR_v11.apk; versión 0.6.1, código 11; 46663432 bytes.
SHA-256: FDE4437DF2779EE690E6B336D94F677F27938BD73A1514C8707A17A5179F0508.
Firma compatible con v10; ambos JSON empaquetados coinciden con StreamingAssets.
Verificaciones de los cuatro pisos aprobadas. Registro: Unity/Builds/AR_VR_v11_build.log.
