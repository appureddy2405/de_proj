import pytest

from pipeline.sample_data import create_sample_db


@pytest.fixture
def sample_db(tmp_path):
    return create_sample_db(tmp_path / "scraper.sqlite", matches=40)
