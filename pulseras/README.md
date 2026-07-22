# Asignación de Pulseras — Escáner de código de barras

Herramienta web muy sencilla (una sola página HTML) para usar desde el celular:

- Busca colaboradores por **número de empleado** o **nombre**.
- Escanea el **código de barras** de una pulsera con la cámara del celular.
- Asigna ese código al colaborador seleccionado, escribiéndolo de vuelta en el
  Google Sheet (columna `Pulsera`).

No requiere instalación ni build: es un solo archivo `index.html` que puedes
abrir directamente o publicar en cualquier hosting estático (GitHub Pages,
Netlify, Vercel, etc.). Debe servirse por **HTTPS** para que el navegador
permita el acceso a la cámara (GitHub Pages ya es HTTPS).

## Estructura de la hoja

La hoja de Google Sheets debe tener estos encabezados en la fila 1, en este orden:

```
Pulsera | Num Empleado | Nombre | Correo
```

## 1. Lectura de datos (ya funciona con tu link)

La app lee los datos con el link de CSV publicado que ya tienes:

```
https://docs.google.com/spreadsheets/d/e/2PACX-1vQADkYAq7mpvxbGQp7hsUvCfu6N1Hw_TKylWoL_9OGcg9DRxbECF2xCSiPIezJjDxLY-RXzxhBB8vdZ/pub?gid=0&single=true&output=csv
```

Esto ya viene precargado por defecto en la app, así que la **búsqueda funciona
sin configuración adicional**.

> Nota: Google actualiza el CSV publicado cada pocos minutos, no al instante.
> Si acabas de editar la hoja manualmente, la búsqueda puede tardar un poco en
> reflejarlo.

## 2. Escritura de datos (asignar pulsera) — requiere un paso único de configuración

Un CSV publicado es de solo lectura. Para que la app pueda **guardar** la
pulsera asignada en tu hoja, necesitas publicar un pequeño **Google Apps
Script Web App** conectado a esa hoja. Es gratis y tarda 5 minutos:

1. Abre tu Google Sheet.
2. Ve a **Extensiones → Apps Script**.
3. Borra el contenido del archivo `Code.gs` que se abre por defecto y pega
   ahí el contenido del archivo [`Code.gs`](./Code.gs) de esta carpeta.
4. Guarda el proyecto (ícono de disquete).
5. Haz clic en **Implementar → Nueva implementación**.
6. En "Seleccionar tipo", elige **Aplicación web**.
7. Configura:
   - **Ejecutar como:** Yo (tu cuenta)
   - **Quién tiene acceso:** Cualquier usuario
8. Haz clic en **Implementar** y autoriza los permisos que pida Google (es tu
   propio script accediendo a tu propia hoja).
9. Copia la **URL de la aplicación web** que te entrega (algo como
   `https://script.google.com/macros/s/AKfycb.../exec`).

## 3. Configurar la app con esa URL

1. Abre `index.html` en el celular (o la URL donde la publiques).
2. Toca el ícono ⚙️ arriba a la derecha.
3. Pega la URL del Web App en el campo **"URL del Web App de Apps Script"**.
4. Guarda.

Listo. Desde ese momento, al escanear un código y presionar **"Asignar
pulsera"**, la app llamará a ese Web App y actualizará la columna `Pulsera`
del colaborador correspondiente en tu Google Sheet.

## Uso diario

1. Escribe el número de empleado (o nombre) en el buscador.
2. Toca al colaborador en la lista de resultados.
3. Toca **"📷 Escanear código"** y apunta la cámara al código de barras de la
   pulsera (también puedes usar **"⌨️ Ingresar código"** para escribirlo a
   mano si el código está dañado o no escanea).
4. Toca **"Asignar pulsera"**.

La app evita asignar el mismo código de pulsera a dos colaboradores distintos
(el Apps Script rechaza la asignación si ese código ya está en uso).

## Publicar la app (opcional)

Si quieres una URL fija para usar desde el celular sin abrir el archivo
localmente, la forma más simple es GitHub Pages:

1. En GitHub, ve a **Settings → Pages** del repositorio.
2. Fuente: rama `main` (o la que uses), carpeta `/pulseras` o raíz según
   dónde quede el archivo.
3. Guarda: te dará una URL tipo `https://usuario.github.io/repo/pulseras/`.

Abre esa URL desde el celular y agrégala a la pantalla de inicio para que
funcione como una app.
