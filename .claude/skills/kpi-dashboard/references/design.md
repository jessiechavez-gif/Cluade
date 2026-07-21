# Referencia de diseño — paleta validada y especificaciones

Parámetros del sistema de diseño ya horneados en `assets/template.html`.
Provienen de un método de dataviz cuya paleta fue validada por script
(banda de luminosidad, piso de croma, ΔE adyacente bajo simulación CVD ≥ 8,
piso de visión normal ≥ 15, contraste sobre superficie). No cambies valores
sueltos: si necesitas otra marca, sustituye el bloque completo de tokens en
la plantilla y re-valida.

## Tokens

| Rol | Claro | Oscuro |
|---|---|---|
| Página | `#f9f9f7` | `#0d0d0d` |
| Superficie de gráfica | `#fcfcfb` | `#1a1a19` |
| Tinta primaria | `#0b0b0b` | `#ffffff` |
| Tinta secundaria | `#52514e` | `#c3c2b7` |
| Tinta muted (ejes) | `#898781` | `#898781` |
| Gridline (hairline) | `#e1e0d9` | `#2c2c2a` |
| Baseline / eje | `#c3c2b7` | `#383835` |
| Serie 1 (azul) | `#2a78d6` | `#3987e5` |
| Serie 2 (naranja) | `#eb6834` | `#d95926` |
| Serie 3 (aqua) | `#1baf7a` | `#199e70` |
| Delta bueno (texto) | `#006300` | `#0ca30c` |
| Delta malo (texto) | `#d03b3b` | `#d03b3b` |

Solo se exponen **3 slots categóricos**: son los que validan *all-pairs* en
ambos modos (peor par CVD ΔE 9.2 claro / 9.4 oscuro). Por eso la plantilla y
el validador del build limitan las líneas a 3 series. Más series → small
multiples o plegar en "Otros".

El modo oscuro es una **selección** de pasos de las mismas rampas (no un
filtro de inversión): el azul sube a `#3987e5`, el naranja baja a `#d95926`,
para mantener ≥3:1 sobre `#1a1a19`.

## Especificaciones de marca

- Barras: **≤ 24px** de grosor, punta de datos redondeada 4px, base cuadrada,
  crecen desde una sola línea base. Gap de 2px en color de superficie entre
  marcas contiguas.
- Líneas: **2px**, uniones y remates redondeados. Marcador final ≥ 8px con
  anillo de 2px en color de superficie.
- Relleno de área: la tonalidad de la serie a **~10% de opacidad**, solo con
  una serie.
- Grid y ejes: gris un paso sobre la superficie, hairline 1px sólido, nunca
  punteado.
- Etiquetado selectivo: valor al final de la línea, valor en la punta de la
  barra; nunca un número en cada punto. Ticks del eje Y en números limpios.
- Leyenda siempre presente con ≥ 2 series; con 1 serie el título la nombra.
- Sparkline del tile: 12 puntos, trazo en color de de-énfasis (`--baseline`),
  punto final en el acento (serie 1).

## Interacción

- **Crosshair en líneas**: hairline vertical que engancha a la fecha más
  cercana; un solo tooltip lista todas las series en esa X. El valor es lo
  fuerte del tooltip; el nombre de la serie, secundario; la llave es un trazo
  corto del color de la serie, no una caja.
- **Barras**: el hit-target es la fila completa (mayor que la marca); la barra
  hovered se aclara ligeramente; tooltip por marca; focusable con teclado.
- **Nombres = datos no confiables**: siempre `textContent`, nunca `innerHTML`
  concatenado — los nombres de series/categorías vienen de datos del usuario.
- **Filtros**: una sola fila, alineada a la izquierda, encima del contenido;
  rango de fechas primero, con presets antes que rango custom; todo lo que
  está debajo se re-agrega contra la misma ventana.

## Anti-patrones que la plantilla evita (no los reintroduzcas)

- Doble eje Y. Dos escalas → dos gráficas o índice base 100.
- Rainbow / hues generados para la serie N.
- Pie/donut para comparar magnitudes (usa barras).
- Números en cada punto de la línea.
- Texto en el color de la serie.
- Colores de estado (verde/amarillo/rojo) reutilizados como series.
- Tooltip como única vía a un valor (la tabla siempre existe).
- Modo oscuro por inversión automática de colores.
