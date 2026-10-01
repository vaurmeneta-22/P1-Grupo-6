# Viga AR v3: diagramas M y V

La colocacion y el ajuste manual se usan como en Colocacion v2, validada por el
usuario en el telefono. Al fijar la viga aparecen controles Ocultar/Momento/Corte
y selector G/Q/EX/EY/COMBO. El control de altura cambia solo la amplitud visual.
Los diagramas son hijos del objeto de la viga y acompanian desplazamientos, giros
y cambio de anclaje. El eje blanco indica cero, cian positivo arriba y naranja
negativo abajo. Se muestran extremos y min/max con distancia desde nodo 60.

Se utiliza `ElementDiagrams.Construir(185, caso, PlanoVertical)`, el mismo motor
del visor de escritorio. My se muestra en kN·m y Vz en kN. Los tres tramos FE se
concatenan conservando discontinuidades de cortante. Incluye la muestra exacta de
extremo de momento donde V=0. No se interpreta el momento como resultante absoluta.

Datos: `StreamingAssets/analysis_map.json`, extraido del APK mediante
UnityWebRequest. El cargador valida identidad 185, nodos 60/70, seccion 60x80,
longitud 10 m, datos finitos, abscisas ordenadas y cierres de extremo. Se exige el
umbral absoluto del visor: 1e-4 kN/kN·m; la precision exportada de q es limitada.
COMBO usa los factores efectivos que carga el motor de AnalysisMap, mostrados
en pantalla. El telefono no ejecuta OpenSees.

Comprobacion en el mapa activo, usando fuentes C# reales del parser y motor:

| Caso | Tramos | Muestras | Error M (kN·m) | Error V (kN) |
|---|---:|---:|---:|---:|
| G | 3 | 78 | 2.690e-6 | 1.070e-6 |
| Q | 3 | 78 | 1.500e-8 | 1.776e-14 |
| EX | 3 | 78 | 1.000e-8 | 0 |
| EY | 3 | 78 | 2.000e-8 | 0 |
| COMBO | 3 | 78 | 3.232e-6 | 1.284e-6 |

Codigo nuevo compilado contra referencias Unity 6000.6.0f1. El metodo de build
valida nuevamente escena, geometria y los cinco casos antes de crear el APK.
La lectura visual y legibilidad de los diagramas requieren prueba en el telefono.

Compilar con `Compilar_Viga_AR_v3.cmd`. APK:
`Unity/Builds/P1_Grupo6_AR_Diagramas_v3.apk`, nombre de app Viga AR v3,
version 0.3.0, versionCode 3. Conserva el paquete com.grupo6.p1.arplacement,
por lo que Android lo instala como actualizacion de la app anterior.
