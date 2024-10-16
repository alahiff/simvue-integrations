from simvue_integrations.connectors.fds import FDSRun
import simvue
import pathlib
import shutil
import time
import uuid
import tempfile
from unittest.mock import patch

def mock_fds_process(self):
    shutil.copy(pathlib.Path(__file__).parent.joinpath("example_data", "fds_header.txt"), pathlib.Path(self.workdir_path).joinpath(f"fds_test.out"))
    time.sleep(0.5)
    self._trigger.set()
    return

@patch.object(FDSRun, 'add_process', mock_fds_process)
def test_moose_header_parser(folder_setup):
    name = 'test_fds_header_parser-%s' % str(uuid.uuid4())
    temp_dir = tempfile.TemporaryDirectory(prefix="fds_test")
    with FDSRun() as run:
        run.init(name=name, folder=folder_setup)
        run_id = run.id
        run.launch(
            fds_input_file_path = pathlib.Path(__file__).parent.joinpath("example_data", "fds_input.fds"),
            workdir_path = temp_dir,
        )
        
    client = simvue.Client()
    
    run_data = client.get_run(run_id)
    
    assert run_data["metadata"]["fds.revision"] == "FDS-6.9.1-0-g889da6a-release"        
    assert run_data["metadata"]["fds.revision_date"] == "Sun Apr 7 17:05:06 2024 -0400"
    assert run_data["metadata"]["fds.compiler"] == "Intel(R) Fortran Intel(R) 64 Compiler Classic for applications running on Intel(R) 64, Version 2021.7.1 Build 20221019_000000"
    assert run_data["metadata"]["fds.compilation_date"] == "Apr 09, 2024 13:24:51"
    assert run_data["metadata"]["fds.mpi_processes"] == 1
    assert run_data["metadata"]["fds.mpi_version"] == 3.1
    assert run_data["metadata"]["fds.mpi_library_version"] == "Intel(R) MPI Library 2021.6 for Linux* OS"