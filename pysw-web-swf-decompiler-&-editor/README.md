PySW Web SWF Decompiler & Editor — Quick Run

Resumen

Esta carpeta contiene la interfaz web (React + Vite + Express) y un endpoint liviano para analizar SWF.

Requisitos

- Node.js 18+ (npm)
- Python 3.10+ (para tests/backend utils)

Desarrollo (frontend + server)

1. Instalar dependencias (si no están instaladas):
   npm install

2. Levantar servidor en modo dev (express + vite):
   npm run dev

3. Comprobar salud:
   curl http://localhost:3000/api/health

Uso del endpoint de parseo (server)

El servidor expone POST /api/parse-swf que acepta JSON { "filename": "name.swf", "b64": "<base64-contents>" } y devuelve un resumen de tags.

Linux / macOS example:
  b64=$(base64 -w0 test.swf)
  curl -sS -X POST http://localhost:3000/api/parse-swf \
    -H "Content-Type: application/json" \
    -d "{ \"filename\": \"test.swf\", \"b64\": \"$b64\" }"

PowerShell example:
  $b = [Convert]::ToBase64String([IO.File]::ReadAllBytes('test.swf'))
  Invoke-RestMethod -Uri http://localhost:3000/api/parse-swf -Method POST -Body (@{ filename = 'test.swf'; b64 = $b } | ConvertTo-Json) -ContentType 'application/json'

Cliente: también puede usar el botón "Parse on Server" en la UI para enviar el archivo al servidor directamente.

AI Decompiler

El endpoint /api/decompile-ai ya existe y requiere la variable de entorno GEMINI_API_KEY para que funcione. Sin clave, la UI mostrará un error evocando la falta de configuración.

Python tests (backend validation)

1. Crear venv (si no existe):
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install --upgrade pip

2. Instalar dependencias Python:
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt

3. Ejecutar tests:
   .\.venv\Scripts\python.exe -m pytest -q tests/test_swf.py

Estado actual

- Dev server corriendo en http://localhost:3000 (comprobado).
- Tests Python: 7 passed.
- Cambios comprometidos en la rama iro007-swf-web-app.

Siguientes pasos sugeridos

- Crear README en la raíz con instrucciones de despliegue (opcional).
- Añadir build y Docker/CD ajustes para producción.
- Mejorar experiencia AI (manejo de streaming, límites de tamaño).

Si desea que construya el bundle de producción y prepare Docker, indicar "build+docker".
