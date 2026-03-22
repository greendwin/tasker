import pytest
from pyfakefs.fake_filesystem import FakeFilesystem


@pytest.fixture(autouse=True)
def setup_fake_fs(fs: FakeFilesystem) -> None:
    _ = fs