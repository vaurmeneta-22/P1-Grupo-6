# P1 — Laboratorio Estructural Digital

**Edificio de Ingeniería — Grupo 6**

## Descripción

Laboratorio estructural digital que combina:

- Análisis estructural 3D con OpenSeesPy
- Visualización e interacción en Unity
- Realidad aumentada con AR Foundation
- Realidad virtual con Google Cardboard: recorrido de los pisos 1 a 4 y consulta de resultados estructurales

## Tecnologías

| Componente | Tecnología |
|-----------|-----------|
| Análisis | Python + OpenSeesPy |
| Visualización | Unity + C# (**6000.6.0f1**) |
| AR | AR Foundation + ARCore, detección de planos y ARAnchor |
| VR | Google Cardboard XR Plugin, estéreo y seguimiento de orientación |
| Datos | JSON (contrato OpenSees↔Unity) |

## Funcionalidades del visor Unity

El visor oficial del proyecto es Unity. La interfaz principal se organiza en cuatro pestañas: **Visualización / Modificaciones / Análisis / Datos**.

- **6 diafragmas rígidos** (niveles 0.00, 3.56, 7.12, 10.68, 14.24 y 17.8 m) por la huella real de piso: plano casi transparente con borde cian y triangulación de polígono cóncavo (tecla `D`).
- **HUD del visor** (`ViewerHud.cs`): barra superior con `Visualización`, `Modificaciones`, `Análisis` y `Datos`; información arriba-izquierda; leyenda de colores y casillas para alternar capas.
- **Capas alternables por familia** a través de teclas o de las casillas de la leyenda; incluye un terreno escalonado que sigue las dos cotas de las zapatas y se puede ocultar desde `Terreno`.
- **Buscador de elementos** en Visualización: permite elegir tipo e ID, enfoca automáticamente el elemento, lo resalta en amarillo y restaura vista/materiales con `Limpiar`.
- **Inspector por clic / doble clic**: al hacer clic sobre una viga, columna, muro o losa se muestra un panel con sus propiedades y, en vigas, el área tributaria y las **cargas** G (permanente) y Q (sobrecarga) calculadas en el análisis. En el modo análisis el **hover** resalta en magenta el elemento bajo el puntero y el **doble clic** sobre una columna/muro de hormigón dibuja la **curva P-M** con su punto de demanda, mientras que sobre una viga o un **metálico** reporta N/V/M/DEF de ambos extremos (`PickHighlight.cs`).
- **Modo modificaciones** (`ModificationMode.cs`): ejecuta desde Unity Base, Mod A, Mod B y Caso C, muestra el registro, guarda historial y recarga la escena al terminar. Incluye **Honor Track 4**, que inicia un backend Python/OpenSees local en segundo plano, envía la modificación por HTTP y muestra validación, errores, reproducibilidad y comparación directa. Caso C cambia la columna 66 de 70×70 a 40×40 cm.
- **Modo análisis**: superpone al modelo los resultados del análisis lineal con OpenSees — deformada y diagramas de momento (M), axial (N) y corte (V).
- **SQ4 carga móvil**: en Análisis, doble clic sobre una losa activa martillo/carga móvil arrastrable, vigas receptoras, reparto de `P_user`, conservación de carga y flechas de transferencia.
- **Panel DATOS** (tecla `B` o botón `DATOS`, `DataPanel.cs`): ventana derecha con **6 pestañas** — Sismo (12 columnas con ux/uy/Rz por piso), Mom-Curv, P-M (fibra vs H.A.), Reacciones (con *Pintar en 3D*), Tributarias y **Diagramas 2D N/V/M** apilados — alimentadas por la API real de `AnalysisMap`.
- **Modo hormigón** (`H`): pinta todo el edificio en tonos de concreto (fundaciones más oscuras).

### Modo análisis del visor

Accesible desde la pestaña **Análisis**:

- **Vistas**: deformada (con amplificación ajustable), Momento M, Axial N y Corte V.
- **Casos de carga**: G (permanente), Q (sobrecarga), EX, EY y COMBO. En Unity los sliders `λG`, `λQ`, `λEX`, `λEY` actualizan COMBO en memoria sin reanálisis cuando se combinan casos ya calculados.
- **Color por valor**: cada elemento se pinta con un colormap azul→verde→rojo normalizado por el **percentil 90** de los valores (evita que uno o dos muros en la base dominen la escala y dejen el resto en azul). La leyenda inferior derecha muestra los rangos reales en las unidades de cada vista (mm en deformada, kN·m en momento, kN en axial/corte).
- **Doble clic en análisis**: sobre una **columna o muro de hormigón** dibuja en el inspector la **curva de capacidad** P-M (de las secciones de fibra RC, como **diamante completo simétrico**: rama +M a la derecha y su espejo −M a la izquierda) y marca el punto de demanda del caso activo (P axial y M resultante del extremo i del elemento), reportando el % de la **capacidad interpolada a esa misma carga axial** y si la demanda cae dentro de la curva (una demanda fuera de la curva se marca en rojo). Sobre una **viga** —y también sobre los **refuerzos metálicos** (columnas y vigas de acero, que no usan P-M)— muestra una tabla con los valores **numéricos** de N (axial), V (corte), M (momento resultante) y DEF (desplazamiento nodal) para los **dos extremos** i y j del elemento del caso activo. El inspector se cierra con la **X** de su esquina superior.
- **Refuerzos metálicos**: 20 elementos de acero A240ES (10 columnas `300x300x20` y 10 vigas diagonales `300x300x50`, en color amarillo) insertados entre los niveles 2–3 y 4–Techo. Su capacidad P-M está exportada en `analysis_map.json`, pero por diseño el visor solo les muestra el reporte N/V/M/DEF.
- Deformada amplificable con el deslizador `x` (escala x120 por defecto, rango 10–600). M/N/V en respuesta lineal del modelo global.

Los datos se cargan desde `Unity/Assets/StreamingAssets/analysis_map.json`, generado por `exportar_analysis_map.py` a partir de los resultados `edificio_full_results*.json`. La navegación funciona con mouse (arrastrar-rota, rueda-zoom, clic derecho-pan) y con **touch** en móvil/simulador (1 dedo-rota, 2 dedos-pinch zoom y pan, tap-seleccionar y doble tap-reporte, `CameraController.cs` + `activeInputHandler: Both`).

### Atajos de teclado

En Unity las capas se alternan con las casillas del panel izquierdo o con las teclas siguientes:

| Tecla | Acción |
|-------|--------|
| `C` | Alternar columnas |
| `X` | Alternar vigas X |
| `Y` | Alternar vigas Y |
| `W` | Alternar muros |
| `L` | Alternar lozas |
| `G` | Alternar refuerzos metálicos (columnas y vigas de acero) |
| `P` | Alternar apoyos (fundaciones) |
| `N` | Alternar nodos |
| `E` | Alternar solo los ejes |
| `D` | Alternar diafragmas rígidos |
| `TAB` | Alternar modo análisis (deformada / M / N / V) |
| `1`–`5` | Seleccionar caso G / Q / EX / EY / COMBO (modo análisis) |
| `M` / `N` / `V` / `D` | Vista Momento / Axial / Corte / Deformada (modo análisis) |
| `R` | Pintar/ocultar las reacciones en 3D (modo análisis) |
| `+` / `-` | Amplificar / reducir la escala de la deformada (10–600) |
| `B` | Abrir/cerrar el panel DATOS (Sismo, Mom-Curv, P-M, Reacciones, Tributarias, Diagramas) |
| `H` | Modo hormigón (concreto claro / fundaciones oscuras) |
| Clic izquierdo | Inspector de propiedades y cargas del elemento; en modo análisis, el **hover** resalta el elemento en magenta y el **doble clic** sobre columna/muro de hormigón dibuja la curva P-M, o sobre viga/**metálico** los valores M/V/N/DEF numéricos (cierre con **X**) |
| Arr. rotar (mouse) / 1 dedo | Orbitar la cámara |
| Zoom 2 dedos (móvil) / rueda | Zoom de la cámara |
| Pan 2 dedos (móvil) / clic derecho | Desplazar la vista (pan) |
| Tap (móvil) | Equivale al clic izquierdo (seleccionar/inspeccionar); doble tap = doble clic (P-M / N-V-M-DEF en análisis) |

## Estructura

```
├── Edificio.json         # Contrato OpenSees↔Unity (regenerado desde el visor)
├── opensees/             # Scripts de análisis estructural
│   ├── loads/            # Definición de cargas
│   ├── fiber_sections/   # Secciones de fibras RC
│   ├── analysis/         # Análisis lineal y no lineal
│   ├── opensees_edificio_v1.py  # Análisis del edificio completo (versión v1)
│   ├── opensees_edificio_v2.py  # FE principal: casos G/Q/EX/EY/COMBO, diafragmas, auditorías
│   ├── conexiones.py     # Reglas de conexión/rigidLinks y apoyos huérfanos (reglas A-E)
│   ├── superposicion.py  # Auditoría de superposición del COMBO
│   ├── verificador_camino_carga.py  # Verificación del camino de carga losa→viga→columna→fundación
│   ├── areas_tributarias.py        # Áreas y cargas tributarias de vigas
│   ├── exportar_analysis_map.py   # Resultados → analysis_map.json (modo análisis del visor)
│   ├── exportar_resultados_csv.py # Resultados → CSV
├── resultados/                    # Resultados del análisis (carpeta tipo)
│   ├── 00_readme.md               # Índice y semántica de sobrescritura
│   ├── 01_casos_base/             # edificio_full_results*.json (G/Q/EX/EY/COMBO)
│   ├── 02_reacciones/             # reacciones.csv
│   ├── 03_desplazamientos/        # desplazamientos.csv
│   ├── 04_fuerzas_elementos/      # fuerzas_elementos.csv
│   ├── 05_sismo/                  # sismo_por_piso.csv (EX/EY)
│   ├── 06_superposicion/          # verificacion.csv de la superposición COMBO
│   ├── 07_capacidad/              # M-φ y P-M: mom_curv/, pm_columnas/, pm_muros/, sensibilidad/
│   ├── 08_verificacion/           # benchmark_3d.json, verification.md, verificacion_rc.json
│   ├── 09_demanda_capacidad/      # demanda_capacidad_*.png + critica.json
│   ├── 10_figuras/                # Diagramas 2D/3D y marco_3d interactivo
│   ├── 11_mapa_visor/             # analysis_map.json, tributary_map.js, mapas del visor
├── reports/              # Informes hasta Semana 7, Honor Tracks H1/H4 y documentación AR
├── Unity/                # Proyecto Unity
│   └── Assets/
│       ├── Scripts/      # EdificioLoader.cs, AnalysisMap.cs, AnalysisMode.cs,
│       │                 # CameraController.cs, PickHighlight.cs, DataPanel.cs,
│       │                 # ViewerHud.cs, ModificationMode.cs, ElementSearchPanel.cs,
│       │                 # Plot2D.cs, TributaryInspector.cs,
│       │                 # DiaphragmData.cs, ElementTag.cs
│       └── StreamingAssets/   # Edificio.json + tributary_map.js + analysis_map.json (runtime)
├── data/                 # Datos compartidos (geometría, materiales, secciones)
├── tests/                # Verificaciones (equilibrio, superposición, tributarias, empalmes, camino de carga)
├── scripts/              # Utilidades (generar_modificaciones.py, ejecutar_modificacion.py,
│                         #   parte_d_fiber.py, parte_d_muros.py,
│                         #   sensibilidad_secciones.py, comparacion_rc.py, demanda_capacidad.py)
├── regla_g_walls.json    # Selección de muros para la regla G de conexiones
└── Enunciado_Proyecto1/  # Enunciado, cronograma y recursos
```

## Flujo de datos

`opensees` calcula los resultados y escribe archivos `edificio_full_results*.json`. Luego `exportar_analysis_map.py` genera `analysis_map.json`; Unity consume `Edificio.json` y `analysis_map.json` desde `StreamingAssets`.

```
data/ ──► opensees ──► resultados/01_casos_base/edificio_full_results*.json
                     └──► exportar_analysis_map.py ──► analysis_map.json
Edificio.json ───────────────────────────────────────► Unity/StreamingAssets
```

Los tipos de elemento soportados por el modelo: `column`, `beam_x`, `beam_y`, `wall`, `loza`, `steel_column` y `steel_beam` (acero A240ES). El orden de elementos debe mantenerse consistente entre `Edificio.json` y `analysis_map.json` para que el modo análisis indexe correctamente.

El modelo actual contiene **536 nodos, 722 elementos** (118 columnas, 141 vigas X, 165 vigas Y, 79 muros, 199 lozas, 10 columnas y 10 vigas metálicas) y **64 apoyos fijos**. Los valores se guardan en **cm** en el JSON.

## Ejecución

Los comandos de esta sección y de **Verificaciones** se ejecutan desde la
**raíz del repositorio**, donde están `Edificio.json`, `opensees/`, `scripts/`
y `Unity/`. Instalar primero las dependencias de la guía de instalación.

### OpenSeesPy
El FE principal es `opensees_edificio_v2.py`. Cada caso construye el modelo desde cero (`ops.wipe`) y exporta su archivo de resultados:

```bash
python opensees/opensees_edificio_v2.py --case G     # → resultados/01_casos_base/edificio_full_results.json
python opensees/opensees_edificio_v2.py --case Q     # → resultados/01_casos_base/edificio_full_results_Q.json
python opensees/opensees_edificio_v2.py --case EX    # → resultados/01_casos_base/edificio_full_results_EX.json
python opensees/opensees_edificio_v2.py --case EY    # → resultados/01_casos_base/edificio_full_results_EY.json
python opensees/opensees_edificio_v2.py --case COMBO --lambda-g 1.2 --lambda-q 1.0 --lambda-ex 1.4 --lambda-ey 1.4
                                            # → resultados/01_casos_base/edificio_full_results_COMBO.json
```

- **G**: peso propio + losa permanente; **Q**: sobrecarga de uso; **EX/EY**: sismo pseudostático en X/Y (carga lateral en el centro de masa de cada diafragma, `F = α·(G + 0.5·Q)` con `α=0.20`).
- **COMBO**: superposición `R = λG·G + λQ·Q + λEX·EX + λEY·EY`, concurrente en X e Y. Sin argumentos usa los defaults `λG=λQ=λEX=λEY=1.0`; pasar explícitamente los lambdas para cualquier otra combinación.
- El script imprime auditorías de equilibrio (ΣR = W), conservación de carga de losa, diafragma rígido, masa sísmica por piso y superposición del COMBO. Si usas los 5 casos, verifica cada resultado y luego regenera el mapa del visor.

También disponible: `benchmark_3d.py` (módulo de prueba 2D/3D) y `superposicion.py` (auditoría de la combinación; al correr completo exporta el resumen a `resultados/06_superposicion/verificacion.csv`). `exportar_analysis_map.py` adicionalmente exporta el sismo por piso a `resultados/05_sismo/sismo_por_piso.csv`.

### Modo análisis del visor (regenerar resultados)
Los resultados del análisis (deformada, M/N/V por caso y capacidad P-M) se exportan a `resultados/11_mapa_visor/analysis_map.json` para Unity. Regenerarlos tras un análisis nuevo:

```bash
python opensees/exportar_analysis_map.py
```

La capacidad P-M se genera con `scripts/parte_d_fiber.py` (columna 70×70 y muro 30×356) y `scripts/parte_d_muros.py` (los **14 muros del contrato restantes**, con la enfierradura proporcional de `sections.muro_tipificado()`). Las curvas P-M y M-φ se escriben en `resultados/07_capacidad/` (`mom_curv/`, `pm_columnas/`, `pm_muros/`). Los diagramas P-M se dibujan como **diamante completo simétrico** (rama ±M, espejo por simetría de la sección). Para el acero, `exportar_analysis_map.py` calcula las curvas P-M de los tubos `300×300×20` y `300×300×50` (elásticas, fy=240 MPa, `A` y `Zp`) en `capacidad.steel`; el visor no las dibuja (los metálicos muestran N/V/M/DEF en su lugar). El visor busca cada curva por el nombre de sección del elemento.

Para regenerar esas curvas, ejecutar desde la raíz:

```bash
python scripts/parte_d_fiber.py
python scripts/parte_d_muros.py
```

Además, al regenerar resultados de capacidad se corre el resto del módulo de capacidad (`scripts/`), que sobrescribe `resultados/`:

```bash
python scripts/sensibilidad_secciones.py   # audita convergencia de la malla de fibras → 07_capacidad/sensibilidad/
python scripts/comparacion_rc.py           # verificación RC (bloque ACI/NCh vs fiber) → 08_verificacion/verificacion_rc.json
python scripts/demanda_capacidad.py        # barre 128 columnas + 79 muros con el COMBO → 09_demanda_capacidad/
```

Si se regeneró la capacidad, volver a ejecutar `python opensees/exportar_analysis_map.py`
para incorporar las nuevas curvas al mapa. Para generar los CSV del **caso G**:

```bash
python opensees/exportar_resultados_csv.py
```

Este exportador lee `edificio_full_results.json` y escribe `reacciones.csv`,
`desplazamientos.csv` y `fuerzas_elementos.csv` en las carpetas
`resultados/02_reacciones/`, `03_desplazamientos/` y `04_fuerzas_elementos/`.

Finalmente, sincronizar el modelo y el mapa para el visor. Desde la raíz en
PowerShell, con Play Mode detenido:

```powershell
Copy-Item -LiteralPath .\Edificio.json -Destination .\Unity\Assets\StreamingAssets\Edificio.json -Force
Copy-Item -LiteralPath .\resultados\11_mapa_visor\analysis_map.json -Destination .\Unity\Assets\StreamingAssets\analysis_map.json -Force
```

El flujo completo es: **analizar G/Q/EX/EY/COMBO → generar capacidad si cambió
la sección → exportar el mapa y los CSV → sincronizar StreamingAssets → abrir el visor**.

### Unity
1. Abrir `Unity/` como proyecto en Unity Hub con **Unity 6000.6.0f1** (ver la guía de instalación más abajo).
2. Al abrir por primera vez Unity regenera `Library/` y los paquetes (toma unos minutos).
3. Abrir `Assets/Scenes/SampleScene.unity` desde la ventana Project y pulsar **Play** para ver el edificio: columnas, vigas, muros, lozas y los 6 diafragmas.
4. Usar las pestañas `Visualización`, `Modificaciones`, `Análisis` y `Datos`.
5. En `Visualización`, buscar por tipo+ID o hacer clic en un elemento para abrir su inspector.
6. En `Modificaciones`, aplicar `Base`, `Mod A`, `Mod B` o `Caso C` desde Unity.
7. En `Análisis`, usar sliders `G/Q/EX/EY`, deformada, M/N/V, reacciones y SQ4.

Si se actualizó `Edificio.json`, copiarlo a `Unity/Assets/StreamingAssets/Edificio.json`. El inspector por clic lee sus cargas desde `StreamingAssets/tributary_map.js`; ambos deben estar sincronizados. El modo análisis lee `StreamingAssets/analysis_map.json`.

### Modificaciones reproducibles

Desde Unity: pestaña **Modificaciones** → `Restaurar Base`, `Aplicar Mod A`, `Aplicar Mod B` o `Aplicar Caso C`.
Para la pauta H4, abre **Modificaciones → Honor Track 4**, elige Caso A (viga 147: 50×75 cm), B (apoyo articulado en nodo 1) o C (columna 66: 40×40 cm), y pulsa **Conectar backend**. Unity se conecta a un servicio activo o inicia `scripts/backend_opensees.py` oculto en segundo plano. Una vez conectado, pulsa **Ejecutar verificación** para enviar el escenario elegido y recibir los resultados. Cada escenario recalcula G/Q/EX/EY/COMBO y compara contra una corrida directa y una repetición. **Desconectar backend** cierra el proceso iniciado por Unity; también se cierra al salir de Play/aplicación. No se requiere abrir una terminal. El reporte detallado queda en `resultados/12_h4/verificacion_h4.json`.

También se puede ejecutar por terminal:

```bash
python scripts/generar_modificaciones.py
python scripts/ejecutar_modificacion.py --tag modA --json Edificio_mod_A.json --element 147 --unity
python scripts/ejecutar_modificacion.py --tag modB --json Edificio_mod_B.json --element 76 --unity
python scripts/ejecutar_modificacion.py --restore
```

- **Mod A:** viga 147, sección 60×80 → 50×75 cm.
- **Mod B:** nodo 1, apoyo empotrado → articulado (`DOF=[1,1,1,0,0,0]`).
- **Caso C:** columna 66, sección 70×70 → 40×40 cm. Genera la curva P-M específica para el ID 66 y reanaliza G/Q/EX/EY/COMBO.
- Cambiar sección/apoyo requiere reanálisis; mover sliders de casos ya calculados no.

## Conexiones y camino de carga

- **Conexiones** (`opensees/conexiones.py`): implementa las reglas A-E que deciden qué nodos se conectan al FE con `rigidLink`, qué apoyos quedan fijos y cuáles "huérfanos" se soportan verticalmente. La selección de muros para la regla G se configura en `regla_g_walls.json`.
- **Camino de carga** (`opensees/verificador_camino_carga.py` + `tests/test_camino_carga.py`): verifica que cada losa se apoye y transmita su carga a través de vigas → columnas/muros → fundación, sin tramos perdidos ni elementos "flotantes".
- **Empalmes viga-viga** (`tests/test_empalmes_viga_viga.py` + `reports/plan_empalmes_viga_viga.md`): documenta cómo se subdividen las vigas (reglas B/F) y se conectan entre sí y con los muros; el visor dibuja las fracciones reales del FE para que el doblez del empalme se vea y no parezca flotar.

## Verificaciones

Ejecutar la suite Python completa desde la **raíz del repositorio**:

```bash
python -m pytest tests -q
```

Debe terminar sin tests fallidos y con código de salida 0. Para revisar solo
un módulo, por ejemplo las secciones de fibras:

```bash
python -m pytest tests/test_fiber_sections.py -v
```

Usar pytest: algunos archivos contienen funciones y fixtures de prueba que no
se ejecutan al invocarlos simplemente con `python archivo.py`. La suite incluye
equilibrio, superposición, áreas tributarias, camino de carga, empalmes,
secciones de fibras y pruebas del backend/validación H4.

La combinación de resultados del visor C# tiene una comprobación adicional
para Windows, también desde la raíz:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tests\test_viewer_combination.ps1
```

Además hay verificaciones *ad hoc* en `opensees/test_asymmetric.py`, `opensees/test_eleforce.py`, `opensees/verificador_camino_carga.py`, `fiber_sections/verification_ha.py` y en el módulo de capacidad (`scripts/sensibilidad_secciones.py`, `scripts/comparacion_rc.py`, `scripts/demanda_capacidad.py`). El detalle del modelo (masa por piso, momentos, equilibrios) queda auditado en consola por `opensees_edificio_v2.py`; resumen en `resultados/08_verificacion/verification.md`, con resultados RC en `verificacion_rc.json`.

## Ciclo de desarrollo

```
Issue → Plan → Build → Test → Review → Merge
```

## Documentación

- [Enunciado del proyecto](Enunciado_Proyecto1/)
- [Agentes IA](AGENTS.md)
- [Avance Semana 3 (entregable)](reports/semana03.md) — casos base, curvas M-φ/P-M, verificación RC y demanda-capacidad
- [Avance Semana 4 (entregable)](reports/semana04.md) — diagramas 2D M/V/N en el visor, auditoría de la convención de esfuerzos de extremo y **traspaso completo del visor a Unity** (modo análisis, HUD, doble clic P-M / N-V-M-DEF y panel DATOS)


---

## Instalación en otro PC: Unity, Android/AR/VR y Python/OpenSees

Esta guía reproduce el entorno de **Windows de 64 bits** de la entrega. Para
abrir el visor y consultar los resultados incluidos se necesita Unity; para
**Modificaciones y Honor Track 4** también se necesita Python/OpenSeesPy; para
compilar el APK se necesitan los módulos Android. El teléfono utiliza los
resultados incorporados al APK y no instala Python ni ejecuta el backend local.

### 0. Obtener el proyecto completo

1. Instalar [Git para Windows](https://git-scm.com/downloads/win), disponible
   desde la terminal y otras aplicaciones mediante el PATH. Package Manager
   también lo necesita para descargar el plugin Cardboard desde GitHub.
   [Requisito oficial de Unity para dependencias Git](https://docs.unity3d.com/6000.0/Documentation/Manual/upm-git.html).
2. Clonar el repositorio en una carpeta con permiso de escritura:

   ```powershell
   git clone https://github.com/vaurmeneta-22/P1-Grupo-6.git
   cd P1-Grupo-6
   git --version
   ```

3. Conservar la raíz completa: `Unity/`, `scripts/`, `opensees/`, `data/`,
   `resultados/` y los JSON del modelo. H4 busca los scripts desde esa raíz.
   En Unity Hub agregar **la subcarpeta Unity/**, no la raíz del repositorio.
4. Mantener los archivos `.meta`, `Packages/manifest.json`,
   `Packages/packages-lock.json` y `ProjectSettings/` incluidos en Git.
   Unity regenera `Library/`, `Temp/` y `Logs/`; no se deben copiar de otro PC.

La primera importación y compilación requieren Internet para descargar paquetes
de Unity, Cardboard y dependencias de Gradle. Los APK de `Unity/Builds/` se
generan localmente y están excluidos de Git: clonar el repositorio no descarga
el APK ya compilado.

La versión con la que se compiló y verificó la app es **Unity 6000.6.0f1**.
Está registrada en [ProjectVersion.txt](Unity/ProjectSettings/ProjectVersion.txt).
Para reproducir esta entrega, instalar esa versión y abrir la carpeta **Unity/**
del repositorio como proyecto existente.

### 1. Descargas desde Unity Hub

En **Unity Hub → Installs/Instalaciones → Unity 6000.6.0f1 → Add modules/Agregar módulos**,
seleccionar:

| Módulo que se debe descargar | Para qué se utiliza |
|---|---|
| **Android Build Support** | Permite generar la aplicación Android. |
| **Android SDK & NDK Tools** — dentro de Android Build Support | Incluye las herramientas de Android y la compilación nativa requerida por IL2CPP. |
| **OpenJDK** — dentro de Android Build Support | Incluye Java para Gradle y la generación del APK. |

Los tres deben quedar instalados en **la misma versión del editor**.
Si Unity ya está instalado, se pueden agregar desde ese menú sin reinstalar
el proyecto. Unity recomienda utilizar los SDK, NDK y JDK que instala Hub para
mantener las versiones compatibles.
[Documentación oficial: dependencias Android](https://docs.unity.com/en-us/engine/6000.3/manual/platform-specific/android/getting-started/sdksetup/install-dependencies).

En Unity, revisar **Edit → Preferences → External Tools** y seleccionar las
herramientas Android instaladas con Unity. La licencia del editor debe estar
activa en Unity Hub para abrir el proyecto y compilar.

Herramientas comprobadas en la instalación usada para la entrega:

| Herramienta | Versión |
|---|---|
| Editor Unity | **6000.6.0f1** |
| Android SDK Platform / compile SDK / target API del APK AR+VR | **36** |
| Android SDK Build Tools | **36.0.0** |
| Android NDK | **r27c — 27.2.12479018** |
| OpenJDK incluido con Unity | **17.0.18** |
| Android mínimo del APK | **API 29 — Android 10** |

Usar **SDK/NDK/JDK installed with Unity** en External Tools. No hace falta
instalar Android Studio ni un Java independiente para este flujo. Si faltan
componentes Android, completarlos desde Hub antes de compilar.

**Complemento opcional:** Visual Studio con el workload **Game development with Unity**
para editar y depurar C#. La configuración del proyecto está en
[Unity/.vsconfig](Unity/.vsconfig). Para instalar un APK ya generado en el teléfono,
basta el APK: el teléfono no necesita Unity ni las herramientas de desarrollo.

### 2. Paquetes dentro de Unity: Package Manager

Al abrir el proyecto por primera vez, Package Manager descarga automáticamente
los paquetes declarados en [manifest.json](Unity/Packages/manifest.json).
Esperar a que termine la importación. Las versiones resueltas se conservan en
[packages-lock.json](Unity/Packages/packages-lock.json).

| Paquete | Identificador | Versión de esta entrega | Uso |
|---|---|---|---|
| **AR Foundation** | com.unity.xr.arfoundation | **6.6.2** | Sesión AR, planos, raycasts, cámara y anclas. |
| **Google ARCore XR Plugin** | com.unity.xr.arcore | **6.6.2** | Proveedor AR para Android. |
| **Google Cardboard XR Plugin** | com.google.xr.cardboard | **1.35.0**, commit `36ac9815b8f191fe11e149b7f323368fa86655a6` | Render estereoscópico y seguimiento VR. |
| **Input System** | com.unity.inputsystem | **1.20.0** | Entrada y actualización de posición/orientación de la cámara AR. |
| **Universal Render Pipeline — URP** | com.unity.render-pipelines.universal | **17.6.0** | Renderizado y materiales del proyecto. |
| **XR Plug-in Management** | com.unity.xr.management | **4.7.0** | Dependencia resuelta: configuración y activación de ARCore. |
| **XR Core Utilities** | com.unity.xr.core-utils | **2.6.0** | Dependencia resuelta: XROrigin y utilidades XR. |
| **XR Legacy Input Helpers** | com.unity.xr.legacyinputhelpers | **3.0.1** | Dependencia resuelta de los proveedores XR. |
| **XR Mock HMD** | com.unity.xr.mock-hmd | **1.5.0-exp.3** | Simulación XR en el editor. |
| **Unity UI** | com.unity.ugui | **2.6.0** | Interfaz del menú móvil y los paneles VR. |
| **Device Simulator Devices** | com.unity.device-simulator.devices | **1.0.1** | Previsualización de la interfaz móvil en el editor. |

XR Plug-in Management y XR Core Utilities se resuelven como dependencias; no
hace falta descargarlos por separado si el proyecto abre correctamente.
Para revisar o restaurar un paquete, abrir **Package Manager**, buscarlo por
nombre o utilizar **Install package by name** con el identificador de la tabla.
Conservar las versiones registradas para reproducir esta entrega.

Cardboard ya está fijado a ese commit en el manifest; conservar esa referencia
para evitar descargar otra versión. No es necesario importarlo manualmente ni
agregar sus ejemplos al proyecto.
[Guía oficial de Cardboard](https://developers.google.com/cardboard/develop/unity/quickstart).
Las versiones de **todos los demás paquetes**, incluidos herramientas de editor
y dependencias transitivas, están en `manifest.json` y `packages-lock.json`;
esos archivos son la referencia completa, además de la tabla anterior.

AR Foundation requiere un proveedor de plataforma para funcionar en el teléfono;
en este proyecto es ARCore.
[Documentación oficial: configuración XR](https://docs.unity.com/en-us/engine/6000.7/manual/xr/configuring-project-for).

### 3. Ajustes del proyecto que deben comprobarse

- **Build Profiles:** plataforma Android.
- **Project Settings → XR Plug-in Management → Android:** proveedores ARCore y
  Cardboard registrados. En el APK combinado, **Initialize XR on Startup queda
  desactivado durante la compilación**: el menú inicia el proveedor del modo
  elegido. Usar el compilador AR+VR del proyecto para aplicar esa configuración.
- **Player → Active Input Handling:** Both, para conservar la entrada del visor
  y el seguimiento de cámara mediante Input System.
- **Player → Scripting Define Symbols:** USE_AR_FOUNDATION para Android.
- **Scripting Backend:** IL2CPP; **Target Architectures:** ARM64.
- **Minimum API Level:** Android API 29, equivalente a Android 10.
- **Graphics APIs:** OpenGL ES 3 para el APK AR+VR.
- **URP:** utilizar los assets de renderizado incluidos en el proyecto. El
  pipeline predeterminado y la calidad PC utilizan PC_RPAsset; el compilador
  móvil selecciona Mobile_RPAsset durante el build.

La escena AR utiliza ARSession, ARInputManager, XROrigin, ARPlaneManager,
ARRaycastManager y ARAnchorManager. La cámara incorpora TrackedPoseDriver,
ARCameraManager y ARCameraBackground. El script
[ARPlacementSetup.cs](Unity/Assets/Editor/ARPlacementSetup.cs) crea y comprueba
esta configuración.

El Device Simulator sirve para revisar la interfaz. La detección de planos y
la estabilidad del seguimiento se validan en un teléfono compatible con ARCore.

### 4. Python y OpenSeesPy para modificaciones y H4

Instalar **Python 3.12 de 64 bits** desde [python.org](https://www.python.org/downloads/windows/)
y marcar **Add python.exe to PATH**. La versión de Python está indicada en
[.python-version](.python-version). OpenSeesPy **3.8.0.0** es la versión registrada
en el [reporte de semana 5](reports/semana05.md); su distribución Windows requiere
Python 3.12 según la [documentación oficial](https://openseespydoc.readthedocs.io/en/latest/).

Cerrar Unity y Unity Hub después de instalar Python/Git y abrir una terminal
nueva para que las aplicaciones reciban el PATH actualizado. Desde la raíz:

```powershell
python --version
python -m pip install "openseespy==3.8.0.0" "openseespywin==3.8.0.0" matplotlib pytest
python -m pip check
python -c "import sys; import openseespy.opensees as ops; import matplotlib; import pytest; print(sys.executable); print('OpenSees:', ops.version())"
```

El primer comando debe mostrar **Python 3.12.x**. El último debe importar las
dependencias y mostrar el intérprete y la versión del motor sin excepciones.
Se instala OpenSeesPy en ese mismo intérprete: Unity ejecuta **`python`** mediante
un proceso externo. Que funcione solamente `py`, o instalar paquetes en otro
entorno de Python, no garantiza que Unity los encuentre.

`matplotlib` permite generar las figuras de capacidad y `pytest` ejecuta las
pruebas. NumPy se instala como dependencia de Matplotlib. Sus versiones y las
de otras dependencias auxiliares **no están bloqueadas en el repositorio**:
estos comandos preparan el entorno, pero no constituyen un lock completo de
Python. Para registrar el entorno instalado, guardar `python -m pip freeze`.

El backend `scripts/backend_opensees.py` utiliza el servidor HTTP de la biblioteca
estándar de Python: no requiere Flask, FastAPI ni instalar OpenSees.exe.
En **Modificaciones → Honor Track 4 → Conectar backend**, Unity inicia o conecta
el servicio en **127.0.0.1:8765**. El puerto debe estar disponible para el backend;
el servicio se ejecuta en el mismo PC. No hace falta iniciarlo manualmente.

### 5. Comprobación inicial y problemas frecuentes

- Abrir `Unity/Assets/Scenes/SampleScene.unity` para el visor de escritorio y
  esperar a que termine la importación, sin errores de compilación, antes de Play.
- Para la app conjunta, usar **Lab → Móvil → Compilar APK AR + Cardboard VR**.
  Este menú configura las escenas y XR. También existe
  [scripts/build_mobile_vr.ps1](scripts/build_mobile_vr.ps1): apunta a
  `C:\Program Files\Unity\Hub\Editor\6000.6.0f1\Editor\Unity.exe`.
  Si Unity está instalado en otra ruta, ajustar su variable `unityExe` o usar
  el menú del editor. Cerrar Unity antes de ejecutar el script batch.
- Si Cardboard no se descarga, comprobar `git --version`, la conexión a GitHub
  y reiniciar Hub después de instalar Git. Conservar el manifest y el lock.
- Si aparece **python no encontrado** o **No module named openseespy**, repetir
  la comprobación de Python anterior y reiniciar Hub; los paquetes deben estar
  instalados en el intérprete que devuelve `python`.
- Si falla H4, revisar el log de Unity y `resultados/12_h4/`. Comprobar que se
  clonó el repositorio completo y que el backend puede usar el puerto 8765.
- Para comprobar el entorno de análisis, ejecutar desde la raíz
  `python -m pytest tests -q`. H4 se valida desde su propia pestaña con los casos
  A/B/C y la comparación directa. Consultar resultados precalculados no requiere
  recalcular ni sobrescribir los archivos existentes.

## Realidad aumentada: Viga AR v4 — Semana 6

El prototipo inicial utilizó AR Foundation con Image Tracking y marcador.
**La app vigente utiliza detección de planos,
colocación manual y ARAnchor.** La viga está asociada al ID 185 y no requiere
imprimir un QR ni un marker para colocarla.

### Alcance y resultados

- **Viga 185:** nodos 60–70, sección 60 × 80 cm y longitud 10 m, a escala 1:1.
- Colocación sobre un plano horizontal y ajuste manual de posición/giro.
- Anclaje al entorno para recorrer la viga con el teléfono.
- **Momento My** en kN·m; **corte Vz** y **axial N** en kN.
- **Desplazamientos nodales** en mm, con amplificación visual ajustable.
- **Área tributaria:** únicamente el valor en m²; para la viga 185, 20.56 m².
- **Cargas:** carga distribuida de losa y aportes del peso propio de esta viga
  en sus nodos, según el caso.
- Selector **G/Q/EX/EY/COMBO**. Los diagramas conservan los tres tramos FE de la
  viga completa: tags 185, 300082 y 300083.
- Los resultados proceden del JSON incorporado al APK. OpenSees se ejecutó
  previamente en el computador.
- Las curvas P-M permanecen en el laboratorio de escritorio y no se incluyen
  en la interfaz de esta app AR.

### Compilar el APK en Windows

1. Completar la instalación de módulos y paquetes descrita arriba.
2. Cerrar el editor Unity si tiene este proyecto abierto.
3. Abrir PowerShell en la raíz del repositorio y ejecutar el comando indicado abajo.
4. Esperar a que indique que el APK fue creado; conservar el registro si falla.

| Archivo | Ubicación |
|---|---|
| Script de compilación | [scripts/build_ar_results.ps1](scripts/build_ar_results.ps1) |
| Registro | Unity/Builds/AR_Resultados_v4_build.log |
| APK | Unity/Builds/P1_Grupo6_AR_Resultados_v4.apk |

El script apunta a Unity 6000.6.0f1 instalado en la ruta estándar de Windows.
En otro computador, comprobar la variable **unityExe** de build_ar_results.ps1.
Los lanzadores locales .cmd se excluyen de GitHub. Ejecutar desde la raíz:

~~~powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_ar_results.ps1
~~~

La aplicación se genera como **Viga AR v4**, versión **0.4.0**, código **4**,
paquete **com.grupo6.p1.arplacement**. Antes del build se comprueban escena,
dimensiones, identidad, independencia de cámara y resultados de los cinco casos.

### Instalar y utilizar en el teléfono

1. Usar un Android compatible con ARCore y Android 10 o superior. Tener
   **Google Play Services for AR** instalado/actualizado.
2. Transferir el APK al teléfono, por ejemplo mediante Drive, e instalarlo.
   V4 conserva el paquete y la firma de v2/v3 para instalarse como actualización.
3. Abrir la app y permitir el acceso a la cámara.
4. Mover lentamente el teléfono mirando una superficie horizontal iluminada
   y con detalles. Apuntar con la mira y pulsar **Colocar viga aquí**.
5. Comprobar la ubicación caminando alrededor. Usar **Ajustar posición** y
   **Fijar posición** para alinearla.
6. Seleccionar **Momento**, **Corte**, **Axial**, **Desplaz.** o **Cargas**, y el
   caso de análisis. Deslizar el panel inferior si algún control queda oculto.

**Estado de validación:** colocación v2 y diagramas M/V v3 confirmados por el
usuario en Xiaomi Redmi Note 12 Pro. V4 compilada y firma verificada; faltan
confirmar sus nuevas vistas en el teléfono y medir el error de alineamiento.

**Límites:** el anchor puede presentar deriva; no se guardan anclas entre sesiones.
Las ordenadas de diagramas, desplazamientos y flechas se amplifican visualmente,
mientras la geometría permanece a escala real. Los desplazamientos se unen
linealmente entre nodos y las flechas de peso propio no incluyen las cargas de
los elementos vecinos.

## App móvil: AR + Visualizador VR de los pisos 1 a 4

Esta app implementa **H1 — Google Cardboard VR — hasta +4**. La versión actual
es **v11 (0.6.1, código Android 11)**; reúne AR y VR en un mismo APK.
El procedimiento de AR v4 de la sección anterior se conserva como referencia
de esa versión; para la app combinada vigente se usa la compilación siguiente.

La versión móvil v11 incluye **Visualizador VR** en la esquina inferior derecha del
menú y del modo AR. El recorrido inicia en el piso 3 e incluye botones para cambiar
a los pisos 1, 2, 3 y 4, debajo de las flechas de movimiento. El panel se mantiene
fijo al bajar la mirada hacia el selector. Cada piso tiene su geometría, techo y
paso libre sobre la junta de dilatación, conservando muros y huecos de escaleras.
Usa Google Cardboard, cuatro flechas, selección
por mirada/pulsador y fichas OpenSees G/Q/EX/EY/COMBO. Incluye diagramas N/V/M
en dos planos, curvas P-M disponibles y referencia momento-curvatura de columna
70×70 a P=0. La geometría y la construcción de diagramas se comparten con el visor.
El teléfono lee `Edificio.json` y `analysis_map.json` incluidos en el APK;
OpenSees calcula previamente en el computador. El recorrido VR no utiliza
el backend de H4 ni ejecuta un nuevo análisis estructural.

| Requisito H1 | Función disponible |
|---|---|
| Render estereoscópico | Vista para ambos ojos y distorsión óptica del SDK Cardboard; controles y gráficos en 3D. |
| Head tracking | Giro de cámara según la orientación de la cabeza/teléfono y recentrado. |
| Locomoción | Cuatro flechas, colisiones, apoyo sobre losas y cambio de piso a una posición segura. |
| Selección de elementos | Mira, permanencia de mirada o pulsador; ID y ficha del elemento original. |
| Resultados OpenSees | Consulta G/Q/EX/EY/COMBO con unidades físicas. |
| Diagramas/capacidad | N/V/M, dos planos, muestras, P-M disponible y referencia momento-curvatura identificada. |

Los momentos se representan con **negativos arriba y positivos abajo**, tanto
en VR como en el diagrama My de la viga AR; los valores mantienen su signo real.
El paso sobre la junta es una ayuda de navegación exclusiva de VR, calculada
por piso: no altera los elementos, cargas ni resultados del modelo estructural.

APK: `Unity/Builds/P1_Grupo6_AR_VR_v11.apk`. Mantiene el paquete Android de la app
AR para instalarse como actualización. En el teléfono se cambia a horizontal
al entrar en VR y se vuelve a vertical al regresar al menú o AR.

Cerrar el editor Unity y compilar desde la raíz:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_mobile_vr.ps1
```

Este constructor registra ARCore y Cardboard y configura la app para iniciar
solo el proveedor del modo elegido. Así se realiza el cambio AR ↔ VR desde el
menú, conservando la misma aplicación instalada.

Uso, arquitectura, verificación y alcance de la prueba física:
[H1 — Cardboard VR](reports/H1_Cardboard_VR.md).

1. Instalar el APK v11 como actualización y abrir **Visualizador VR**.
2. Poner el teléfono horizontal; configurar el visor mediante su QR si Cardboard
   lo solicita. En Editor la vista previa se identifica como **sin estéreo**.
3. Mirar una flecha **0.7 s** para moverse; dejar de mirarla detiene el movimiento.
4. Elegir **Piso 1 / 2 / 3 / 4**, debajo de las flechas, por mirada de **1.1 s** o
   pulsador. Apuntar al selector mantiene fijo el panel y no desplaza al visitante;
   el cambio de piso se realiza al activar el botón.
5. Mirar un elemento **1 s** o usar el pulsador para consultar su ficha. La consulta
   pausa la locomoción; **Recorrer piso** vuelve a los controles.
6. **Centrar panel** recupera los controles, **Volver al inicio** restablece la
   ubicación del piso actual e **Inicio** regresa al menú AR/VR.

**Validación:** Play Mode y compilación v11 aprobados para los cuatro pisos,
incluidos cambios repetidos, selección estable, resultados y cruce de juntas en
ambos sentidos. Las comprobaciones por nivel quedan en
`Unity/Builds/H1_floor1_checks.json` a `H1_floor4_checks.json`; los registros son
`H1_v11_play.log` y `AR_VR_v11_build.log` en la misma carpeta. Las salidas de
Builds se generan localmente al verificar/compilar.

El usuario confirmó el funcionamiento del recorrido inicial en el teléfono.
Queda confirmar la versión final v11 y archivar la prueba de imagen estéreo y
head tracking con visor Cardboard antes de declarar H1 validado físicamente.
El [informe de Semana 7](reports/semana07.md) reúne H4 y la implementación de H1.

## Entrega final

La entrega se identifica con el tag **`v1.0.0`**. El APK Android AR/VR v11, el informe PDF, el informe Markdown y sus checksums se distribuyen desde la [Release final en GitHub](https://github.com/vaurmeneta-22/P1-Grupo-6/releases/tag/v1.0.0). El código fuente y las configuraciones corresponden al commit señalado por ese tag.

Para instalar la app, descargar `P1_Grupo6_AR_VR_v11.apk` desde **Assets** de la Release. Usar Android 10 o superior, ARM64 y un teléfono compatible con ARCore para el modo AR. El APK no se almacena dentro del historial Git. Las instrucciones de escritorio, H4, análisis, tests y compilación están en las secciones anteriores.

## Documentación complementaria

- [Informe final](reports/final.md) — informe Markdown con resultados, QA, contribuciones, H1/H4, limitaciones e instrucciones reproducibles.
- [Informe final original en PDF](reports/Informe_Final_Grupo6_P1_MCOMP.pdf).
- [Notas de la Release final](reports/release_final.md) — archivos de entrega, instrucciones de uso y comprobaciones del APK.
- [Avance Semana 1](reports/semana01.md) — benchmark y convenciones.
- [Avance Semana 2](reports/semana02.md) — modelo y áreas tributarias.
- [Avance Semana 5](reports/semana05.md) — laboratorio interactivo, modificaciones y superposición.
- [Avance Semana 6](reports/semana06.md) — flujo AR, transformaciones, precisión, resultados, QA y errores conocidos.
- [Avance Semana 7](reports/semana07.md) — H4: reanálisis OpenSees y backend local; H1: Google Cardboard VR, pisos 1–4, interacción y evidencia de validación.
- [H1 — Google Cardboard VR](reports/H1_Cardboard_VR.md) — uso, controles, junta de dilatación, compilación y evolución del APK.
- [AR: colocación v2](reports/AR_Colocacion_v2.md) — colocación, ajuste y anclaje.
- [AR: diagramas v3](reports/AR_Diagramas_v3.md) — diagramas M/V y verificación de resultados.
