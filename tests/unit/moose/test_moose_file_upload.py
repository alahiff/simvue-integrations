from simvue_integrations.connectors.moose import MooseRun
import pathlib
from unittest.mock import patch
import tempfile
import uuid
import simvue
import filecmp
import time
import threading

def mock_moose_process(self, *_, **__):
    # No need to do anything this time, just set termination trigger
    self._trigger.set()
    return True

def mock_input_parser(self, *_, **__):
    self._output_dir_path = str(pathlib.Path(__file__).parent.joinpath("example_data", "moose_outputs"))
    self._results_prefix = "moose_test"

@patch.object(MooseRun, '_moose_input_parser', mock_input_parser)
@patch.object(MooseRun, 'add_process', mock_moose_process)
def test_moose_file_upload(folder_setup):
    """
    Check that Exodus file is correctly uploaded as an artifact once simulation is complete.
    """    
    name = 'test_moose_file_upload-%s' % str(uuid.uuid4())
    temp_dir = tempfile.TemporaryDirectory(prefix="moose_test")
    with MooseRun() as run:
        run.init(name=name, folder=folder_setup)
        run_id = run.id
        run.launch(
            moose_application_path=pathlib.Path(__file__),
            moose_file_path=pathlib.Path(__file__),
        )
        
        client = simvue.Client()
        
        # Retrieve Exodus and CSV file from server and compare with local copies
        client.get_artifacts_as_files(run_id, "output", temp_dir.name)
        comparison = filecmp.dircmp(pathlib.Path(__file__).parent.joinpath("example_data", "moose_outputs"), temp_dir.name)
        assert not (comparison.diff_files or comparison.left_only or comparison.right_only)
        
def mock_aborted_moose_process(self, *_, **__):
    """
    Mock a long running MOOSE process which is aborted by the server
    """
    def abort():
        """
        Instead of making an API call to the server, just sleep for 1s and return True to indicate an abort has been triggered
        """
        time.sleep(1)
        return True
    self._simvue.get_abort_status = abort
    
    def aborted_process():
        """
        Long running process which should be interrupted at the next heartbeat
        """
        self._heartbeat_interval = 2
        time.sleep(10)
        
    thread = threading.Thread(target=aborted_process)
    thread.start()

@patch.object(MooseRun, '_moose_input_parser', mock_input_parser)
@patch.object(MooseRun, 'add_process', mock_aborted_moose_process)    
def test_moose_file_upload_after_abort(folder_setup):
    """
    Check that outputs are uploaded if the simulation is aborted early by Simvue
    """
    name = 'test_moose_file_upload_after_abort-%s' % str(uuid.uuid4())
    temp_dir = tempfile.TemporaryDirectory(prefix="moose_test")
    with MooseRun() as run:
        run.init(name=name, folder=folder_setup)
        run_id = run.id
        run.launch(
            moose_application_path=pathlib.Path(__file__),
            moose_file_path=pathlib.Path(__file__),
        )
    
    client = simvue.Client()
    # Check that run was aborted correctly, and did not exist for longer than 10s
    runtime = time.strptime(client.get_run(run_id)["runtime"], '%H:%M:%S.%f')
    assert runtime.tm_sec < 10
    
    # Check files correctly uploaded after an abort
    client.get_artifacts_as_files(run_id, "output", temp_dir.name)
    comparison = filecmp.dircmp(pathlib.Path(__file__).parent.joinpath("example_data", "moose_outputs"), temp_dir.name)
    assert not (comparison.diff_files or comparison.left_only or comparison.right_only)
    