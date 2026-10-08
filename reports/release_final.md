# Entrega final - Proyecto 01

**Versión de entrega: `v1.0.0`. [Estado y descargas en GitHub](https://github.com/vaurmeneta-22/P1-Grupo-6/releases/tag/v1.0.0).**

Fecha de preparación: 8 de octubre de 2026. Grupo 6. El PDF final fue proporcionado por el equipo y no se modifica su contenido ni el identificador Android.

## Archivos de la entrega

| Componente | Archivo | Forma de entrega |
|---|---|---|
| Informe final Markdown | [final.md](final.md) | Repositorio y adjunto de Release |
| Informe final PDF | [Informe_Final_Grupo6_P1_MCOMP.pdf](Informe_Final_Grupo6_P1_MCOMP.pdf) | Repositorio y adjunto de Release |
| Instrucciones reproducibles | [README.md](../README.md) | Repositorio |
| Ejecutable Android AR/VR | `Unity/Builds/P1_Grupo6_AR_VR_v11.apk` | Adjunto descargable de Release; `Builds/` está excluido de Git |
| Código y configuraciones | Raíz, `opensees/`, `scripts/`, `tests/`, `data/`, `Unity/` | Snapshot del commit final del tag |
| Notas de publicación | Este archivo | Texto preparado para la Release |

El tag **`v1.0.0`** identifica el commit de la entrega del proyecto. Esta versión es independiente de la versión interna Android **0.6.1**, código **11**. El commit exacto y los adjuntos se consultan en la Release enlazada arriba.

## Producto ejecutable comprobado

| Propiedad | Valor verificado en el APK existente |
|---|---|
| Archivo | `P1_Grupo6_AR_VR_v11.apk` |
| Tamaño | 46 663 432 bytes |
| Paquete | `com.grupo6.p1.arplacement` |
| Versión / código Android | 0.6.1 / 11 |
| Android mínimo / objetivo | API 29, Android 10 / API 36 |
| Arquitectura | ARM64 |
| Firma | APK Signature Scheme v2 verificada; certificado Android Debug |
| Proveedores | Bibliotecas nativas ARCore y Cardboard presentes |
| Modelo incluido | Base; 536 nodos y 722 objetos con IDs únicos |
| Casos de resultados | G, Q, EX, EY y COMBO |

SHA-256:

```text
FDE4437DF2779EE690E6B336D94F677F27938BD73A1514C8707A17A5179F0508
```

Para comprobar el archivo desde la raíz en PowerShell:

```powershell
Get-FileHash -LiteralPath .\Unity\Builds\P1_Grupo6_AR_VR_v11.apk -Algorithm SHA256
```

La comprobación local del 8 de octubre verificó integridad del contenedor, firma, metadatos, bibliotecas XR y contenido de los JSON. La geometría coincide semánticamente con `Edificio.json` y el mapa coincide con el mapa base versionado en `5fe4c82`. El hash debe recalcularse si se recompila o sustituye el APK.

El último build y Play Mode existentes registran éxito de la compilación y aprobación de comprobaciones VR para los cuatro pisos. Se revisaron sus logs; no se ejecutó un nuevo build ni una prueba física durante esta preparación.

## Cómo ejecutar el producto

### Aplicación Android

1. Descargar el APK que se adjunte a la Release final, en la sección **Assets**.
2. Instalarlo en un teléfono Android ARM64 con Android 10 o superior. Para AR, utilizar un equipo compatible con ARCore y Google Play Services for AR.
3. Permitir el acceso a cámara al entrar en AR. Detectar una superficie horizontal, colocar la viga y ajustar/fijar su posición.
4. Consultar los casos G/Q/EX/EY/COMBO y las vistas de resultados.
5. Abrir **Visualizador VR**, usar el teléfono horizontal y configurar el visor Cardboard si se solicita.
6. Utilizar las flechas para moverse y los botones inferiores para elegir pisos 1 a 4. Seleccionar elementos para abrir sus resultados y diagramas/capacidad disponibles.

El móvil consulta los JSON incluidos en el APK. No necesita Python ni ejecuta el backend H4 o un nuevo análisis estructural durante el recorrido.

### Laboratorio de escritorio y H4

1. Obtener el repositorio completo correspondiente al tag `v1.0.0`.
2. Instalar Unity **6000.6.0f1** y, para modificaciones/H4, Python **3.12 de 64 bits** y OpenSeesPy **3.8.0.0**, siguiendo el README.
3. Abrir `Unity/` desde Hub y la escena `Assets/Scenes/SampleScene.unity`. Esperar la importación y pulsar Play.
4. Consultar el modelo y sus resultados. Para H4, ir a **Modificaciones → Honor Track 4 → Conectar backend**, seleccionar A/B/C y ejecutar la verificación.

H4 inicia o conecta un backend local en `127.0.0.1:8765`. Python debe estar disponible como `python` en el entorno heredado por Unity.

El ejecutable empaquetado de esta preparación es Android. El laboratorio de escritorio se entrega como proyecto Unity con instrucciones de ejecución; no se afirma que exista un `.exe` de Windows preparado.

## Alcance y evidencias

- Modelo global tridimensional elástico lineal y capacidad de sección separada.
- Resultados identificados por elemento y con unidades.
- AR con viga 185, planos, colocación manual y ancla.
- H1 con estéreo Cardboard, orientación, locomoción, selección, resultados y consulta de diagramas/capacidad en pisos 1 a 4.
- H4 con validación, manejo de errores, comparación directa y repetición. El informe fuente declara evidencia completa archivada para B y validación de entradas para A/C.
- Prueba funcional móvil v11 declarada en el PDF. Sin medición cuantitativa AR ni evidencia física archivada de visor Cardboard.
- Superposición histórica de desplazamientos con error 6,78 × 10⁻⁹: cumple 10⁻⁶ y no 10⁻¹⁰.
- Capacidad nominal uniaxial y combinaciones de estudio; no se presenta como una verificación normativa completa.

El [informe final](final.md) conserva la matriz QA, las contribuciones, las diferencias documentales y el detalle de las limitaciones.

## Procedimiento de cierre y trazabilidad

1. Revisar los informes finales del Grupo 6 y conservar el PDF proporcionado por el equipo.
2. Elegir expresamente qué resultados de variantes se archivarán; evitar subir cambios locales generados accidentalmente junto con los documentos.
3. Si se recompila, restaurar primero el modelo base: el mapa local de StreamingAssets contiene una variante y no coincide con el mapa base del APK comprobado. Mantener los resultados de variantes separados.
4. Registrar el commit final que acompañará al tag y al ejecutable comprobado.
5. Asociar el tag `v1.0.0` con el commit final y publicar la Release con el APK, el PDF, el Markdown y `SHA256SUMS.txt`. Comprobar los hashes de los archivos adjuntos antes de publicar.

El APK se mantuvo intacto y no se publicó ningún archivo durante esta preparación.
