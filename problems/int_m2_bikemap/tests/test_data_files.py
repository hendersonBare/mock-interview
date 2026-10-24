import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


def test_ride_file_is_a_feature_collection():
    ride = json.loads((DATA / "ride_canal_loop.geojson").read_text())
    assert ride["type"] == "FeatureCollection"
    (feature,) = ride["features"]
    assert feature["geometry"]["type"] == "LineString"
    assert len(feature["properties"]["times"]) == len(feature["geometry"]["coordinates"])


def test_landmark_ids_are_unique():
    landmarks = json.loads((DATA / "landmarks.json").read_text())
    assert len({lm["id"] for lm in landmarks}) == len(landmarks) == 30
