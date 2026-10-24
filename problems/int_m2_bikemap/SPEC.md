# Ride maps

<!-- commands -->
> Commands: `pytest -q` runs the tests · `prep reveal` adds the next part to this file · `prep grade` when the timer is up · full list in README.md (Quick start).

Riders upload rides recorded on their Trailhead bike computers and want a picture of
the route plus a few facts about it. Pathfinder (see `DOCS.md`) renders maps and knows
about landmarks. Your job is to add the commands that turn a ride file into those
outputs.

The spec arrives in parts. Finish (or stop) one part before revealing the next with
`python reveal.py <n>`. Later parts build on earlier ones; interfaces defined in one
part keep working in later parts.

## Part 1: load a ride

Create `bikemap/ride.py` with:

```python
def load_ride(path) -> Ride:
    ...
```

It reads a ride file (format in `DOCS.md`, "Ride files") and returns a
`bikemap.models.Ride` whose `name` is the ride's name and whose `points` are
`bikemap.models.TrackPoint` objects in file order, with:

- `lat`, `lon`: the position in decimal degrees (floats),
- `ele`: the elevation in metres (float) or `None` when the position has none,
- `time`: an aware UTC `datetime`, or `None` when the timestamp is `null`.

Add a `summary` command:

```
python -m bikemap summary data/ride_canal_loop.geojson
```

It prints exactly five lines:

```
name: <name>
points: <number of points>
start: <lat>,<lon>
end: <lat>,<lon>
bbox: <min_lat>,<min_lon>,<max_lat>,<max_lon>
```

`start` is the first point, `end` the last one, and `bbox` the bounding box of all
points. Every coordinate is written with exactly 6 digits after the decimal point
(`52.379185`). `bikemap.cli.main(argv)` must run the same command and return 0.

Example (made-up ride):

```
name: Morning spin
points: 3
start: 51.500000,-0.120000
end: 51.510000,-0.100000
bbox: 51.500000,-0.120000,51.510000,-0.100000
```
