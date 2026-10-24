import pytest

from mock_map import MockMapServer


@pytest.fixture
def map_server():
    with MockMapServer() as server:
        yield server
