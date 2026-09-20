# ADR 0002: ejecución local, persistencia y recuperación

- Estado: aceptada para el PoC
- Fecha: 2026-09-19

## Decisión

La API entrega builds a un pool de threads local y acotado. Así `POST /builds` responde rápidamente
sin introducir Redis ni una cola externa. La CLI con `--run` ejecuta síncronamente. Ambos caminos
llaman al mismo pipeline de `BuildManager`.

Cada etapa terminada se persiste inmediatamente. Después de un reinicio confirmado,
`recover_interrupted` marca ejecuciones interrumpidas con un diagnóstico, reconcilia sus recursos y
reintenta builds en `DESTROYING`. La recuperación es explícita para no interferir con otro proceso
API que todavía esté trabajando.

Los logs viven bajo el workspace validado. La API solo lee rutas registradas cuyo padre directo sea
el directorio `logs` del build y limita la respuesta a 100 KB.

Los puertos de preview se coordinan mediante leases transaccionales SQLite entre procesos locales.
La recuperación elimina leases huérfanos y restaura leases ausentes cuando el runtime sigue activo.

## Limitaciones

El ejecutor no es durable: las tareas en memoria se pierden al terminar el proceso. SQLite y el
pool local son adecuados para este PoC de un solo host, no para builders distribuidos. Una cola
durable queda aplazada hasta justificar la complejidad operativa.
