---
name: kpi-dashboard
description: >
  Genera dashboards de KPIs interactivos con calidad ejecutiva (C-level) como un
  solo archivo HTML autocontenido: tiles de KPI con deltas y sparklines, gráfica
  de tendencia con crosshair y tooltip, barras por categoría, vista de tabla,
  filtros de rango de fechas y tema claro/oscuro. Usar cuando el usuario pida un
  dashboard, tablero, panel de KPIs, reporte ejecutivo interactivo o
  visualización de métricas de negocio. El resultado funciona offline y puede
  publicarse como Artifact.
---

# KPI Dashboard — dashboards ejecutivos interactivos

Esta skill produce un dashboard de KPIs en **un solo archivo HTML sin
dependencias externas** (sin CDNs, sin fetch), apto para abrirse localmente,
enviarse por correo o publicarse como Artifact bajo CSP estricta.

## Flujo de trabajo

1. **Levanta los requisitos.** Identifica con el usuario (o infiere de sus
   datos): los 3–6 KPIs que importan al nivel ejecutivo, la unidad de cada uno
   (`currency` / `number` / `percent`), si "subir es bueno" (`goodDirection`),
   y una dimensión de desglose (región, canal, producto…). Si el usuario dio
   datos (CSV, tabla, API), úsalos; si pidió un demo, genera datos sintéticos
   plausibles con tendencia y estacionalidad semanal.

2. **Escribe el config JSON.** Sigue el contrato de datos de abajo. Las series
   son diarias y todas deben tener la misma longitud que `dates`.

3. **Genera el HTML:**

   ```bash
   python scripts/build_dashboard.py config.json -o dashboard.html
   ```

   El script valida el config (series alineadas, unidades, límites de series y
   categorías) y falla con mensajes claros antes de producir HTML roto.

4. **Verifica renderizando.** Abre el HTML (o toma screenshot con Playwright y
   el Chromium preinstalado) en modo claro y oscuro. Revisa la checklist
   C-level de abajo antes de entregar.

## Contrato de datos (config JSON)

```jsonc
{
  "title": "Resumen ejecutivo",
  "subtitle": "Rendimiento comercial",        // opcional
  "locale": "es-MX",                          // opcional, default es-MX
  "currency": "MXN",                          // opcional, default USD
  "defaultRange": "30d",                      // 7d | 30d | 90d | all
  "footnote": "Fuente: CRM interno",          // opcional
  "dates": ["2026-01-01", "..."],             // ISO diarias, ascendentes
  "kpis": [
    {
      "id": "revenue",
      "label": "Ingresos",
      "unit": "currency",                     // currency | number | percent
      "aggregate": "sum",                     // sum | avg | last
      "goodDirection": "up",                  // up | down (down: churn, costos)
      "series": [12000, 13400, "..."]         // un valor por fecha
    }
  ],
  "charts": [
    {
      "id": "trend",
      "type": "line",
      "title": "Ingresos diarios",
      "unit": "currency",
      "area": true,                           // wash solo con 1 serie
      "span": 8,                              // columnas de 12 (opcional)
      "series": [ { "kpi": "revenue" } ]      // o {name, values:[...]}  — máx 3
    },
    {
      "id": "by-region",
      "type": "bar",
      "title": "Ingresos por región",
      "unit": "currency",
      "categoryLabel": "Región",
      "valueLabel": "Ingresos",
      "span": 4,
      "categories": ["Norte", "Centro", "Sur"],   // máx 8; el resto → "Otros"
      "values": [[...], [...], [...]]             // matriz categoría × fecha
    }
  ]
}
```

Notas del contrato:

- **`aggregate`** define cómo se resume la serie en la ventana del filtro:
  `sum` para flujos (ingresos, pedidos), `last` para stocks (usuarios activos,
  MRR), `avg` para tasas (conversión, NPS, ticket promedio).
- El **delta** de cada tile compara la ventana activa contra la ventana
  anterior de igual longitud, y se colorea según `goodDirection` (una caída de
  churn se pinta verde).
- Los filtros de rango re-agregan **todo**: tiles, gráficas y tablas siempre
  cuentan la misma historia.

## Reglas de diseño (no negociables)

La paleta y las especificaciones vienen del método de dataviz validado — el
detalle está en `references/design.md`. Lo esencial:

- **Un eje.** Nunca doble eje Y. Dos medidas de escala distinta → dos gráficas.
- **Máximo 3 series por línea** (la paleta valida all-pairs solo en 3 slots) y
  **máximo 8 categorías** por barra; el excedente se pliega en "Otros".
- El color sigue a la entidad, no al ranking; los colores no se reciclan al
  filtrar.
- El texto nunca viste el color de la serie: valores y etiquetas usan tokens
  de tinta; la identidad la da la marca de color junto al texto.
- Toda gráfica tiene tooltip (crosshair en líneas, hit-target por barra) y
  **vista de tabla** ("Ver tabla") — el tooltip mejora, nunca condiciona.
- El modo oscuro usa pasos propios de la paleta, no una inversión automática.
- Números grandes en cifras proporcionales; `tabular-nums` solo en columnas.

## Checklist C-level (antes de entregar)

- [ ] ¿El primer vistazo responde "¿cómo vamos?" en menos de 5 segundos?
      (tiles arriba, tendencia principal dominante, deltas con dirección).
- [ ] Cada KPI tiene delta vs periodo anterior con color según `goodDirection`.
- [ ] Los filtros re-agregan tiles, gráficas y tablas de forma consistente.
- [ ] Tooltip funciona en todas las gráficas; crosshair engancha a la fecha.
- [ ] Modo claro y oscuro revisados con screenshot (no solo el CSS).
- [ ] Sin colisiones de etiquetas, sin texto cortado, sin scroll horizontal.
- [ ] Etiquetas en sentence case; nada de MAYÚSCULAS decorativas.
- [ ] El archivo abre offline: cero requests externos (verifica con DevTools
      o grep de `http` en el HTML generado).

## Verificación con screenshot (Chromium preinstalado)

```bash
node -e '
const { chromium } = require("playwright");
(async () => {
  const b = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium" });
  const p = await b.newPage({ viewport: { width: 1280, height: 900 } });
  await p.goto("file://" + process.argv[1]);
  await p.screenshot({ path: "light.png", fullPage: true });
  await p.evaluate(() => { document.documentElement.dataset.theme = "dark"; });
  await p.click("#theme-toggle"); await p.click("#theme-toggle"); // re-render
  await p.screenshot({ path: "dark.png", fullPage: true });
  await b.close();
})();' /ruta/absoluta/dashboard.html
```

Mira ambas capturas antes de entregar: el validador de paleta ya corrió; lo
que queda es geometría, colisiones y overflow — eso solo se ve mirando.
