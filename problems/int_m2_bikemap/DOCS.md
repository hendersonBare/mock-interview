# Pathfinder Maps API (v1) - reference

Pathfinder renders route maps and serves points of interest. This repository ships a
local copy of the API (`mock_map/`) that behaves as described here.

## Base URL

```
http://127.0.0.1:8700        # python -m mock_map (default port)
```

## Authentication

Every endpoint except `/v1/health` needs the API key in a header:

```
X-Api-Key: pk_test_pathfinder_51c0
```

`pk_test_pathfinder_51c0` is the test key accepted by the local server. A missing or
wrong key gives `401`. The key is not accepted as a query parameter or bearer token.

## Conventions

- **Positions** in requests and responses are always `[latitude, longitude]` in
  decimal degrees (WGS 84): latitude first. Latitude must be in [-90, 90] and
  longitude in [-180, 180].
- **Colors** are `#rrggbb` hex strings (case-insensitive; the API reports lowercase).
- **Timestamps** are UTC ISO 8601 with a literal `Z`, e.g. `2026-05-03T07:42:10Z`,
  optionally with fractional seconds (`07:45:34.500Z`). Numeric offsets such as
  `+02:00` are not valid.
- **Distances** are metres on a spherical Earth with radius **6 371 000 m**, using the
  haversine formula:

  ```
  a = sin²(Δφ/2) + cos φ1 · cos φ2 · sin²(Δλ/2)
  d = 2 · R · asin(√a)          φ = latitude, λ = longitude, in radians
  ```

  `bikemap.geo.haversine_m(lat1, lon1, lat2, lon2)` implements exactly this.

## Ride files

Rides are exported by Trailhead bike computers as GeoJSON (RFC 7946):

```json
{
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature",
    "properties": {"name": "Canal loop", "times": ["2026-05-03T07:42:10Z", "..."]},
    "geometry": {"type": "LineString",
                 "coordinates": [[4.900061, 52.379185, 2.9], [4.897311, 52.378791]]}
  }]
}
```

- The file holds one `LineString` feature: the track.
- As in every GeoJSON file, each position in `coordinates` is
  **`[longitude, latitude]`**, optionally followed by an elevation in metres. Some
  positions have an elevation and some do not.
- `properties.times[i]` is the timestamp of `coordinates[i]`. An entry can be `null`
  when the device had no time fix.
- `properties.name` is the ride's display name.

Note that this is the opposite order from the API, which expects latitude first.

## Endpoints

| method | path | description |
|---|---|---|
| GET | `/v1/health` | `{"status": "ok"}`; no authentication |
| POST | `/v1/render` | draw paths and markers, returns a PNG image |
| GET | `/v1/landmarks` | list points of interest |

### POST /v1/render

Request: `Content-Type: application/json` (anything else is `415`).

```json
{
  "width": 640,
  "height": 480,
  "paths": [
    {"points": [[52.379185, 4.900061], [52.378791, 4.897311]], "color": "#1f77b4", "width": 3}
  ],
  "markers": [
    {"at": [52.379185, 4.900061], "kind": "start"}
  ]
}
```

| field | required | notes |
|---|---|---|
| `width`, `height` | no | image size in pixels, 64 to 2048; default 640 x 480 |
| `paths` | yes | non-empty list of polylines |
| `paths[].points` | yes | list of at least 2 positions (`[lat, lon]`); a straight segment is drawn between each consecutive pair |
| `paths[].color` | no | one color for every segment of this path; default `#1f77b4` |
| `paths[].colors` | no | list of colors used in turn: segment `k` of the path (from point `k` to point `k+1`, counting from 0) gets `colors[k % len(colors)]`. Use either `color` or `colors`, not both |
| `paths[].width` | no | line width in pixels, 1 to 9; default 3 |
| `markers` | no | list of markers drawn on top of the paths |
| `markers[].at` | yes | position (`[lat, lon]`) |
| `markers[].kind` | no | `start`, `end` or `poi` (default `poi`) |
| `markers[].color` | no | default depends on `kind`: start `#2a9d8f`, end `#e63946`, poi `#f4a261` |

At most 5000 positions per request (`413` above that).

Response `200`:

- body: the PNG image bytes (`Content-Type: image/png`),
- header `X-Render-Id: rnd_<hex>`: identifies this rendering (the same request
  always produces the same image and id).

The PNG carries a `tEXt` chunk with keyword `pathfinder:render` whose value is JSON
describing what was drawn: `width`, `height`, `segments` (each with `from`, `to`,
`color`, `width`) and `markers` (each with `at`, `kind`, `color`).
`bikemap.png.png_info(data).text` reads it, which is handy for checking a request.

### GET /v1/landmarks

| query parameter | default | notes |
|---|---|---|
| `limit` | `10` | page size, 1 to **10** |
| `page_token` | none | value of `next_page_token` from the previous page |

```json
{
  "data": [
    {"id": "lm_001", "name": "Pedestrian bridge 12", "category": "bridge",
     "coordinates": [52.379795, 4.882107]}
  ],
  "next_page_token": "lmp_10"
}
```

`coordinates` is `[latitude, longitude]` like every position in this API.
`next_page_token` is `null` on the last page. Tokens are opaque; an invalid token is
a `400`. Landmark data is contributed by users; a record may be incomplete or have
unusable coordinates.

## Errors

Errors have a JSON body:

```json
{"error": {"type": "invalid_request_error", "message": "paths[0].points needs at least 2 positions"}}
```

| status | meaning | retry? |
|---|---|---|
| 400 | invalid request (message says what) | no |
| 401 | missing or wrong `X-Api-Key` | no |
| 404 / 405 | unknown path / wrong method | no |
| 413 | too many positions | no |
| 415 | body is not `application/json` | no |
| 429 | rate limited; wait `Retry-After` seconds | yes |
| 500, 502, 503, 504 | temporary server problem | yes, with a short backoff |

All requests are safe to repeat (rendering has no side effects).

## Rate limits

Production allows 20 requests per second per key. The local server does not enforce
a limit.

## Running the local server

```
python -m mock_map                          # http://127.0.0.1:8700
python -m mock_map --port 9000 --log-file api.log
python -m mock_map --scenario scenarios/<file>.json
```

Each request is logged as `METHOD /path?query -> status`.

A scenario is a JSON object; every key is optional:

| key | meaning |
|---|---|
| `landmarks` | inline list of landmark records replacing the data file |
| `landmarks_file` | data file path relative to the repository root (default `data/landmarks.json`) |
| `api_keys` | accepted keys (default `["pk_test_pathfinder_51c0"]`) |
| `faults` | list of `{"path", "method"="GET", "query"={}, "after"=0, "times"=1, "status", "delay"}`: the first `after` matching requests pass, then the next `times` matching requests are delayed by `delay` seconds and/or answered with `status` |

In tests, start it in-process on a free port:

```python
from mock_map import MockMapServer
with MockMapServer() as api:
    print(api.url, api.requests, api.renders)
```
