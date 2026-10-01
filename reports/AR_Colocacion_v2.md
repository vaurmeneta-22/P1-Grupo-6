# AR — Colocacion v2

## Alcance

Colocar la viga 185 sobre un plano horizontal detectado por ARCore, mantenerla
anclada al entorno y ajustar manualmente posicion y giro. Sin marcador impreso.
No cambia el modelo OpenSees ni sus resultados. Esta version no muestra diagramas.

## Uso en Android

1. Instalar `P1_Grupo6_AR_Colocacion_v2.apk` y abrir **Viga AR v2**.
   El identificador es `com.grupo6.p1.arplacement`, distinto de las demos previas.
2. Permitir la camara. Mover suavemente el telefono mirando una superficie
   horizontal iluminada y con detalles, entre 0.3 y 8 m de la camara.
3. Apuntar con la mira central. Una flecha amarilla de 1 m indica el inicio y
   sentido de la viga. Pulsar **Colocar viga aqui**.
4. La viga aparece con su cara inferior apoyada sobre la superficie detectada;
   desde ese inicio se extiende horizontalmente 10 m siguiendo la flecha.
5. Caminar lateralmente y comprobar que permanece en el lugar. Su posicion en la
   pantalla debe cambiar con la perspectiva; no debe permanecer pegada a la mira.
6. Pulsar **Ajustar posicion**. Elegir paso: 5 cm/1 grado, 25 cm/5 grados o
   1 m/15 grados. Izquierda/derecha y acercar/alejar siguen la vista horizontal
   del telefono en el momento de pulsar. Subir/bajar siguen la vertical del mundo.
   Los giros son alrededor del centro de la viga. Cada pulsacion aplica un paso.
7. Pulsar **Fijar posicion**. Se crea un nuevo anclaje cerca del centro manteniendo
   la pose visible. Se puede volver a ajustar. **Volver a colocar** pide confirmacion.

La ubicacion dura durante la sesion. Cerrar/reiniciar la app requiere colocar de
nuevo. La escala no es ajustable: longitud 10 m, altura 0.8 m, ancho 0.6 m.
Las bandas amarillas estan separadas 1 m para contrastar con una huincha.

## Implementacion

- Escena independiente: `Unity/Assets/Scenes/ARBeamPlacement.unity`.
- `ARPlacementSetup.cs`: escena, materiales referenciados, verificaciones y build.
- `ARBeamPlacement.cs`: preview, raycast sobre poligono de plano horizontal,
  anclaje asincrono, ajuste y UI.
- `ARBeamPlacementMath.cs`: convenciones de geometria y transformaciones.
- `ARSession` + **ARInputManager** + `XROrigin` a escala uno y altura de camara cero.
- Camara con `TrackedPoseDriver` del Input System; bindings para XRHMD y
  HandheldARInputDevice, posicion y rotacion, actualizacion antes de render.
- El objeto colocado cuelga del ARAnchor. Solo el preview sigue la mira.
  Los controles modifican el hijo; nunca escriben la transformacion del anchor.
- Al perder tracking se oculta la geometria y se bloquean ajustes; se conserva el
  anclaje para recuperar el seguimiento. No se recoloca automaticamente.
- Materiales serializados para incluir los shaders URP en el APK.

## Compilacion y verificaciones

Con Unity 6000.6.0f1 y target Android:

```text
Unity.exe -batchmode -quit -projectPath ".../P1-Grupo-6/Unity" -buildTarget Android -executeMethod ARPlacementSetup.BuildAndroid -logFile ".../build.log"
```

Antes de compilar, el metodo exige: una camara, ARInputManager, ARSession,
proveedor ARCore, bindings de pose y origen metrico. Comprueba las transformaciones
reales de Unity: dimensiones, ID unico, independencia respecto a una camara que
se mueve, orientacion en cuatro direcciones, movimiento horizontal, giro alrededor
del centro y conservacion de pose al cambiar de padre.

## Validacion fisica necesaria

Compilar y pasar las pruebas de transformaciones no verifica el seguimiento del
telefono. En el Xiaomi hay que comprobar: permiso/camara, deteccion del suelo,
estabilidad al caminar, marcas de 1 m contra huincha, ajuste en seis sentidos,
giro, fijacion, recuperacion despues de perder tracking y nueva colocacion.
La opcion **Ver estado AR** muestra sesion, tracking del anclaje y posicion de
camara; permite identificar un seguimiento detenido. No se promete ausencia de
deriva ni precision topografica.
