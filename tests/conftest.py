from pathlib import Path

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

import tasker


@pytest.fixture(autouse=True)
def setup_fake_fs(fs: FakeFilesystem) -> None:
    fs.add_real_directory(Path(tasker.__file__).parent / "templates")
