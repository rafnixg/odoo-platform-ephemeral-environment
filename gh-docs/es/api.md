# API HTTP

Inicie FastAPI con `mini-runbot serve`. La especificación interactiva está disponible en `/docs` y
el dashboard en `/`.

## Crear un build

`POST /builds` persiste la solicitud, la entrega al ejecutor acotado y devuelve `202 Accepted`.

```json
{
  "repositories": [
    {"repository": "custom", "ref": "feature/catalog"},
    {"repository": "oca", "ref": "16.0"}
  ],
  "modules": ["custom_sale", "website_sale"],
  "ttl_seconds": 14400
}
```

El payload histórico con `repository` y `ref` sigue admitido para un único repositorio. Alias
duplicados, módulos inválidos, refs inseguras o repositorios no configurados reciben `400`. Si no
hay repositorios listos para ejecutar, la API devuelve `503`.

## Endpoints

| Método | Ruta | Resultado |
| --- | --- | --- |
| `GET` | `/app-config` | Repositorios públicos permitidos y límites del formulario. |
| `POST` | `/builds` | Crea y despacha un build. |
| `GET` | `/builds` | Lista builds. |
| `GET` | `/builds/{build_id}` | Devuelve el build y sus etapas. |
| `GET` | `/builds/{build_id}/logs?stage=test` | Devuelve logs restringidos a una etapa. |
| `DELETE` | `/builds/{build_id}` | Destruye el runtime; devuelve `409` si sigue activo. |

Los IDs desconocidos devuelven `404`. Las lecturas de logs están limitadas a 100 KB y solo pueden
acceder a rutas registradas bajo el directorio `logs` del build.

## Compatibilidad

La versión actual de FastAPI es `0.2.0`, pero la API todavía pertenece a una prueba de concepto y no
promete estabilidad entre versiones. Consuma los enums de estado como cadenas y tolere campos
nuevos en las respuestas.
