from pathlib import Path

from autocomplete import config


def test_project_paths_are_derived_from_package_location():
    assert config.PROJECT_ROOT == Path(config.__file__).parents[2]
    assert config.DATA_DIR == config.PROJECT_ROOT / "data"
    assert config.RAW_DATA_DIR == config.DATA_DIR / "raw"
    assert config.PREPARED_DATA_DIR == config.DATA_DIR / "prepared"


def test_default_index_path_is_under_prepared_data_dir():
    assert config.DEFAULT_INDEX_PATH == (
        config.PREPARED_DATA_DIR / "autocomplete-index.json"
    )
