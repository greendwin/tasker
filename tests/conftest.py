import os
from pathlib import Path
from typing import Protocol

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

import tasker


@pytest.fixture
def project_root() -> Path:
    proj_root = Path("/myproj")
    proj_root.mkdir()
    return proj_root


@pytest.fixture(autouse=True)
def setup_fake_fs(fs: FakeFilesystem, project_root: Path) -> None:
    fs.add_real_directory(Path(tasker.__file__).parent / "templates")
    os.chdir(project_root)


@pytest.fixture
def tasks_root(project_root: Path) -> Path:
    root_dir = project_root / "tasker"
    root_dir.mkdir(parents=True, exist_ok=True)
    return root_dir


@pytest.fixture
def tasks_archive_root(tasks_root: Path) -> Path:
    root_dir = tasks_root / "archive"
    root_dir.mkdir(parents=True, exist_ok=True)
    return root_dir


class GetTaskFile(Protocol):
    def __call__(self, task_ref: str) -> Path: ...


def get_task_file(tasks_root: Path) -> GetTaskFile:
    def callback(task_ref: str) -> Path:
        path = next(tasks_root.glob(f"{task_ref}.md"), None)
        assert path is not None, f"file {tasks_root}/{task_ref}.md does not exist"
        return path

    return callback
