import pytest

from api.utils import parse_bbox, to_feature, to_feature_collection


def test_parse_bbox_valid():
    assert parse_bbox("-104.7,50.4,-104.5,50.5") == (-104.7, 50.4, -104.5, 50.5)


def test_parse_bbox_allows_spaces():
    assert parse_bbox(" -104.7, 50.4 , -104.5,50.5 ") == (-104.7, 50.4, -104.5, 50.5)


@pytest.mark.parametrize(
    "text",
    [
        "-104.7,50.4,-104.5",          # only 3 numbers
        "-104.7,50.4,-104.5,abc",      # not a number
        "-104.5,50.4,-104.7,50.5",     # min lon bigger than max lon
        "-104.7,50.5,-104.5,50.4",     # min lat bigger than max lat
        "-200,50.4,-104.5,50.5",       # longitude out of range
    ],
)
def test_parse_bbox_invalid(text):
    with pytest.raises(ValueError):
        parse_bbox(text)


def test_to_feature():
    row = {
        "id": 7,
        "name": "Spray Pad",
        "amenity_type": "Spray Pad",
        "park_name": "Victoria Park",
        "geometry": {"type": "Point", "coordinates": [-104.61, 50.45]},
    }
    feature = to_feature(row)

    assert feature["type"] == "Feature"
    assert feature["id"] == 7
    assert feature["geometry"]["type"] == "Point"
    assert "geometry" not in feature["properties"]
    assert feature["properties"]["park_name"] == "Victoria Park"
    # the original row should not be changed
    assert "geometry" in row


def test_to_feature_collection_empty():
    fc = to_feature_collection([])
    assert fc == {"type": "FeatureCollection", "count": 0, "features": []}
