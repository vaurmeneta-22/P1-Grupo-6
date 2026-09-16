# Resultados para Excel

Los CSV nuevos usan UTF-8, separador `;` y coma decimal, sin separadores de miles.
Si Excel no separa las columnas, importar desde **Datos > Desde texto/CSV**,
elegir punto y coma y configuración regional Español (Chile).
Los valores físicos indican sus unidades en los encabezados. IDs, índices,
coeficientes lambda, errores relativos y ratios son adimensionales.

## Archivos que abrir

| Carpeta | CSV nuevos | Alcance |
|---|---|---|
| 01_casos_base | resumen_casos_excel.csv | Resumen y factores de los cinco casos; los JSON siguen siendo la fuente completa. |
| 02_reacciones | reacciones_G/Q/EX/EY/COMBO.csv | 99 nodos por caso, fuerzas globales con signo en kN y momentos en kN·m. |
| 03_desplazamientos | desplazamientos_G/Q/EX/EY/COMBO.csv | 516 nodos por caso; traslaciones en m y mm, rotaciones en rad. |
| 04_fuerzas_elementos | fuerzas_elementos_G/Q/EX/EY/COMBO.csv | 701 elementos FE por caso, extremos i/j, fuerzas globales y locales. |
| 05_sismo | sismo_por_piso_EX/EY/COMBO.csv | Cinco pisos por caso, con los redondeos del mapa de Unity. G y Q no tienen resultados laterales propios. |
| 06_superposicion | verificacion_excel.csv | Resultados de la verificación existente; incluye comparación con la tolerancia del proyecto. |
| 07_capacidad/pm_columnas | curvas_PM_excel.csv | Curvas por sección y modelo; no dependen de G/Q/EX/EY. |
| 07_capacidad/pm_muros | curvas_PM_excel.csv | Curvas por sección y modelo; no dependen de G/Q/EX/EY. |
| 07_capacidad/mom_curv | momento_curvatura_excel.csv | Curva de la columna 70x70 con el axial P indicado en cada fila. |
| 07_capacidad/sensibilidad | sensibilidad_excel.csv | Discretizaciones de las secciones analizadas. |
| 08_verificacion | verificaciones_casos_excel.csv | Indicadores escalares guardados en cada JSON; celdas vacías significan dato no disponible. |
| 09_demanda_capacidad | demanda_capacidad_critica_COMBO_excel.csv | Demanda crítica existente para COMBO; conserva su criterio y ratio, sin recalcularlos. |
| 10_figuras | diagramas_representativos_G/Q/EX/EY/COMBO.csv | Datos del mapa para viga 147, columna 261 y muro 446; no son diagramas de todos los elementos. |
| 11_mapa_visor | tributarias_excel.csv | Una tabla común con áreas y cargas G/Q por viga, tomadas del JSON G. |

La notación G/Q/EX/EY/COMBO de la tabla representa archivos separados.

## Comparar con Unity

- Seleccionar el mismo caso y el mismo ID. `elementTag` identifica el elemento FE;
  los tags auxiliares de elementos subdivididos no necesariamente son objetos
  independientes seleccionables en el visor.
- En fuerzas, `global_i_*` y `global_j_*` conservan ejes globales y signos.
  `local_i_*` y `local_j_*` conservan ejes locales y signos.
  `unity_abs_i_*` y `unity_abs_j_*` contienen los módulos de las fuerzas locales,
  como la ficha de Unity, con más decimales que la pantalla.
- En reacciones, `aparece_en_tabla_Unity` distingue los nodos que muestra el panel
  de los otros nodos exportados por el análisis. No confundir esa selección con
  la totalidad de reacciones del modelo.
- Los diagramas conservan la convención N/V/M del mapa del visor y su coordenada
  longitudinal; no son las columnas globales de fuerzas en extremos.
- Las curvas P-M de fibra y HA se listan en filas separadas porque sus puntos no
  coinciden. La curva momento-curvatura depende del axial indicado, no del nombre
  de un caso de carga global.

## Archivos originales y alcance de la comprobación

Se conservaron los JSON, JS, figuras, HTML, informes y CSV antiguos. Para Excel,
usar los nuevos CSV con sufijo de caso o `_excel`. En particular, el antiguo
`04_fuerzas_elementos/fuerzas_elementos.csv` tenía números alterados por separadores;
no usarlo para comparar. Los scripts antiguos pueden regenerar sus propios CSV
con otro formato.

No se duplicaron por caso las capacidades, el benchmark independiente de marco
3D ni la verificación RC por sección. Los informes originales mantienen el
detalle de esos ensayos. Tampoco se inventaron demandas críticas de otros casos.

Cada CSV nuevo se reabrió y se comprobó contra los valores usados para exportarlo,
incluida la conversión decimal. Fuerzas y desplazamientos se cotejaron con Unity;
también se cotejaron las reacciones que Unity muestra. El mapa JSON de resultados
y el de Unity coincidían completamente al exportar.

Esto verifica la exportación, no constituye una nueva validación estructural.
La verificación de superposición existente usa tolerancia 1e-6 y registra un
error relativo máximo de desplazamientos de aproximadamente 6,78e-9: cumple su
tolerancia original pero no el umbral 1e-10 del AGENTS.md. La tabla nueva muestra
ambos criterios explícitamente. Los indicadores de equilibrio y conservación
se exportan tal como están guardados, sin recalcular el modelo.

## Regenerar

Desde la raíz del proyecto:

```text
python opensees/exportar_tablas_excel.py
```

El comando regenera las 27 tablas adicionales y los cinco CSV de fuerzas desde
los resultados existentes. No ejecuta OpenSees ni modifica los resultados de Unity.
