# AR RealScale v1 — implementación y protocolo de prueba

Esta versión reemplaza la calibración manual experimental. No lee los ajustes
antiguos de PlayerPrefs. Su funcionamiento físico todavía requiere validación.

## Uso

1. Imprimir Grupo6_Viga185_AR.png a 20 x 20 cm incluyendo sus bordes.
2. Colocarlo horizontal, imagen hacia arriba. El centro identifica el nodo 60.
3. El eje local +X (hacia el borde derecho de la imagen) apunta hacia el nodo 70.
4. Abrir RealScale v1 y detectar el marker. Se exige seguimiento y estabilidad
   durante 1.5 s (desviaciones máximas de 2 cm y 3 grados durante la ventana).
5. Se crea un ARAnchor; el elemento queda como hijo del anchor, no del marker.
6. Volver a ubicar elimina la colocación y permite repetir.

## Coordenadas y geometría

- Unidades: metros. Geometría Unity local: centro (5,0,0), dimensiones (10,0.8,0.6).
- Nodo i = (0,0,0); nodo j = (10,0,0). Eje longitudinal X, altura Y, ancho Z.
- La sección es 60 x 80 cm. El plano del marker es XZ; su normal es +Y.
- El centro del marker representa el eje de la sección inicial. Por ello la mitad
  inferior de la sección queda bajo ese plano de referencia; no es un apoyo físico.
- El visor general convierte [x,y,h] estructural a [-x,h,y]. Esta demo utiliza
  un sistema local del elemento, trasladando el nodo inicial al origen y orientando
  el tramo hacia +X del marker. No reproduce la ubicación global del edificio.
- Transformación: p_AR = T_anchor * p_local, sin escala adicional.
- Camera TrackedPoseDriver actualiza posición y rotación antes del render.
- OpenGLES3 y ARBackgroundRendererFeature conservan la configuración de cámara.

## Datos

ElementTag 185, nodos 60 y 70, sección 60x80. Se valida la identidad en
analysis_map.json. Android extrae StreamingAssets mediante UnityWebRequest.
El panel muestra Vz y My del caso G calculados previamente por OpenSees.
El teléfono ejecuta tracking, detección, anchor, transformación y renderizado;
no ejecuta OpenSees ni reanaliza la estructura.

## Validación pendiente en Xiaomi

- Confirmar cámara y dimensiones con referencia métrica.
- Desplazarse lateralmente: la viga debe permanecer ubicada, no seguir la mira.
- Sacar el marker de la vista y comprobar tracking del anchor.
- Comprobar nodo inicial, orientación y panel de fuerzas.
- Probar Volver a ubicar; revisar logs si falla antes de otra compilación.
- La pantalla muestra RealScale v1 para distinguir APKs anteriores.

No se afirma precisión topográfica ni ausencia de deriva. Compilar no sustituye
la prueba del seguimiento y de la escala en dispositivo.
