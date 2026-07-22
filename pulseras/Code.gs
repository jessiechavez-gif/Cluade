/**
 * Apps Script Web App para asignar pulseras/códigos de barras a colaboradores.
 * Instrucciones de instalación en README.md.
 *
 * Estructura esperada de la hoja (encabezados en la fila 1, en este orden):
 *   Pulsera | Num Empleado | Nombre | Correo
 */

function doPost(e) {
  var lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    var data = JSON.parse(e.postData.contents);
    var numEmpleado = String(data.numEmpleado || "").trim();
    var pulsera = String(data.pulsera || "").trim();

    if (!numEmpleado || !pulsera) {
      return jsonOutput({ ok: false, error: "Faltan datos (numEmpleado o pulsera)." });
    }

    var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
    var values = sheet.getDataRange().getValues();
    var headers = values[0].map(function (h) { return String(h).trim().toLowerCase(); });

    var colPulsera = findColumn(headers, "pulsera");
    var colNumEmpleado = findColumn(headers, "num empleado");
    var colNombre = findColumn(headers, "nombre");
    var colCorreo = findColumn(headers, "correo");

    if (colPulsera === -1 || colNumEmpleado === -1) {
      return jsonOutput({ ok: false, error: "No se encontraron las columnas esperadas en la hoja." });
    }

    var targetRow = -1;
    for (var i = 1; i < values.length; i++) {
      if (String(values[i][colNumEmpleado]).trim() === numEmpleado) {
        targetRow = i;
        break;
      }
    }

    if (targetRow === -1) {
      return jsonOutput({ ok: false, error: "No se encontró el número de empleado " + numEmpleado + "." });
    }

    for (var j = 1; j < values.length; j++) {
      if (j !== targetRow && String(values[j][colPulsera]).trim() === pulsera) {
        var otherName = colNombre !== -1 ? values[j][colNombre] : values[j][colNumEmpleado];
        return jsonOutput({ ok: false, error: "Esa pulsera/código ya está asignado a " + otherName + "." });
      }
    }

    sheet.getRange(targetRow + 1, colPulsera + 1).setValue(pulsera);

    return jsonOutput({
      ok: true,
      nombre: colNombre !== -1 ? values[targetRow][colNombre] : "",
      correo: colCorreo !== -1 ? values[targetRow][colCorreo] : "",
      pulsera: pulsera,
    });
  } catch (err) {
    return jsonOutput({ ok: false, error: "Error del servidor: " + err.message });
  } finally {
    lock.releaseLock();
  }
}

function doGet() {
  return jsonOutput({ ok: true, message: "El Web App está activo. Usa POST para asignar pulseras." });
}

function findColumn(headers, target) {
  for (var i = 0; i < headers.length; i++) {
    if (headers[i].indexOf(target) !== -1) return i;
  }
  return -1;
}

function jsonOutput(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
