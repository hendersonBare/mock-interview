## Part 2: render the route

Create `bikemap/render.py` with:

```python
def render_ride(ride, out_path, *, base_url, api_key, width=640, height=480) -> str:
    ...
```

It sends **one** `POST /v1/render` request (see `DOCS.md`) that draws the ride's
track as a single path through all of its points, in file order, using the API's
default color and line width, with no markers, at `width` x `height` pixels. It
writes the response body to `out_path` byte for byte and returns the render id from
the `X-Render-Id` response header.

If the API answers with an error status, raise `bikemap.errors.ApiError` carrying that
status and do not create or overwrite `out_path`. A `bikemap.errors.TransportError`
(no response) may propagate.

Add a `render` command:

```
python -m bikemap [--base-url URL] [--api-key KEY] render RIDE --out FILE [--width W] [--height H]
```

It prints the render id on one line and exits with status 0. On an API or transport
error it prints a message to stderr and exits with status 1. `--base-url` and
`--api-key` default to `BIKEMAP_BASE_URL` / `BIKEMAP_API_KEY`.

Open the PNG you get. Does the map look like the ride?
