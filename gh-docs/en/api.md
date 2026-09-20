# HTTP API

Start FastAPI with `mini-runbot serve`. Interactive OpenAPI documentation is available at `/docs`
and the dashboard at `/`.

## Create a build

`POST /builds` persists the request, dispatches it to the bounded executor, and returns
`202 Accepted`.

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

The historical `repository` plus `ref` payload remains valid for one repository. Duplicate aliases,
invalid modules, unsafe refs, or unconfigured repositories receive `400`. If no repositories are
ready for execution, the API returns `503`.

## Endpoints

| Method | Path | Result |
| --- | --- | --- |
| `GET` | `/app-config` | Public repository options and form limits. |
| `POST` | `/builds` | Creates and dispatches a build. |
| `GET` | `/builds` | Lists builds. |
| `GET` | `/builds/{build_id}` | Returns a build and its stages. |
| `GET` | `/builds/{build_id}/logs?stage=test` | Returns logs restricted to one stage. |
| `DELETE` | `/builds/{build_id}` | Destroys runtime; returns `409` while active. |

Unknown IDs return `404`. Log reads are limited to 100 KB and can only access recorded paths below
the build's `logs` directory.

## Compatibility

The current FastAPI application version is `0.2.0`, but the API is still part of a proof of concept
and does not promise stability between releases. Consume status enums as strings and tolerate new
response fields.
