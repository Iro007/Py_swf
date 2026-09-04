Plan para igualar/superar a JPEXS - estado y próximos pasos

Resumen rápido (estado actual):
- Infraestructura: servidor Express + frontend React + backend Python (py_swf). CI ejecuta pytest; PR abierto: feature/complete-swf-work.
- Testing: suite pytest (14 tests) pasa localmente.
- Corpus: generador sintético y 50 fixtures generadas en tests/fixtures.
- Herramientas añadidas: benchmark, generator, ai_infer_names, decompile_abc, decompress_zws helper (ZWS best-effort).
- UI: Export .AS ZIP con preview; Gemini AI endpoint integrado y opt-in.

Fases (entregables y responsables automáticos)
1) Corpus & legal (completado parcialmente)
   - Generar 50+ fixtures sintéticos (hecho).
   - Acción pendiente: ingestar SWF reales con licencia del usuario.

2) Núcleo AVM (en progreso)
   - Objetivo: cubrir todos opcodes AVM1/AVM2, robustez de parser. 
   - Acciones hechas: ampliaciones iniciales en stack_sim y flow_recovery; helper para ZWS agregado.
   - Próximo: revisar py_swf/avm2.py para añadir casos de opcodes faltantes y pruebas unitarias por opcode.

3) Recuperación de flujo (parcial)
   - Hecho: lookupswitch -> pseudo-switch, heurísticas if/while.
   - Próximo: detectar do/while, switch con fallthrough, reconstrucción anidada.

4) Reconstrucción semántica (por hacer)
   - Mejorar class_reconstruct, inferencia de nombres (heurísticas + IA), tipos y firmas.
   - Integrar pipeline IA en server safe/opt-in.

5) Recursos & UI (parcial)
   - Hecho: Zip export, preview (confirm list). Server en http://0.0.0.0:3000 (dev).
   - Próximo: modal árbol navegable, editor con aplicar cambios y rebuild SWF.

6) Rendimiento & tests (en progreso)
   - Hecho: benchmark script; ran on 52 fixtures; mean ~0.6s per fixture (synthetic).
   - Próximo: add regression corpus, integrate benchmarks in CI, compare with JPEXS timings (if available).

7) Packaging & docs
   - Hecho: draft release created; PR open.
   - Próximo: publish release artifacts post-merge; provide install/run docs.

Próximas acciones automatizadas que ejecutaré ahora (sin intervención):
- Añadir más pruebas unitarias por opcode y extender stack_sim para más mnemonics.
- Implementar modal ZIP preview en UI (reemplazo de confirm).
- Integrar benchmark en CI (artifact output).
- Preparar script que compare contra JPEXS output si el usuario provee jpexs outputs o SWF.

Notas de seguridad/licencia
- No descargaré SWF públicos sin permiso. Para comparaciones con JPEXS, subir SWF de prueba o autorizar descarga es necesario.

Contacto
- PR: https://github.com/Iro007/Py_swf/pull/2
- Server dev: http://0.0.0.0:3000

Si estás de acuerdo, continuaré implementando modal UI, ampliaré stack_sim y añadiré benchmarks en CI. Si quieres que importe SWF reales, súbelos o dame permiso explícito para descargarlos de URLs específicos.
