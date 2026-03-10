# AGENTS.md

## Objetivo del proyecto
API backend en Python/FastAPI para [describe en 2-3 líneas].

## Arquitectura
- app/api: rutas
- app/services: lógica de negocio
- app/db: modelos y acceso a datos
- tests: pruebas

## Reglas de estilo
- Seguir PEP 8
- Priorizar claridad sobre “magia”
- Funciones pequeñas y con una responsabilidad
- Evitar lógica grande en endpoints
- No duplicar código si puede extraerse a servicio o helper
- Nombres explícitos
- Tipado cuando aporte claridad
- Docstrings cortas en funciones no obvias
- No añadir dependencias sin justificarlo

## Reglas de seguridad
- No borrar archivos sin avisar
- No cambiar interfaces públicas sin explicarlo
- No tocar configuración sensible sin permiso explícito
- No hacer refactors masivos fuera de alcance

## Testing
- Toda funcionalidad nueva debe incluir prueba mínima o plan manual de validación
- Si cambias una ruta, revisar respuesta, errores y edge cases
- Ejecutar tests relevantes antes de dar por terminado el trabajo

## Forma de trabajar
- Primero analiza
- Luego propone plan
- Después ejecuta por fases
- Resume qué cambiaste, qué falta y qué riesgos ves