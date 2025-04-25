import os
import datetime
import pytest
from unittest.mock import patch, MagicMock, ANY

import main

# Define a fixed timestamp for predictable directory names
FIXED_DATETIME = datetime.datetime(2024, 10, 20, 15, 30, 45)
EXPECTED_TIMESTAMP_DIR = FIXED_DATETIME.strftime("output_%Y_%m_%d_%H%M%S")

# Define dummy data that format_pr_data_for_llm would return
DUMMY_PR_DATA = "### GitHub Pull Request Analysis ###\nFake PR data content."

@pytest.fixture
def mock_github():
    """Mocks the Github object and its chained calls."""
    mock_g = MagicMock()
    mock_repo = MagicMock()
    mock_pr = MagicMock()
    mock_user = MagicMock()
    mock_user.login = 'testuser' # Needed for auth check message

    # Configure mocks for the calls made in the script
    mock_g.get_user.return_value = mock_user # For the authentication check
    mock_g.get_repo.return_value = mock_repo
    mock_repo.get_pull.return_value = mock_pr

    # We don't need to mock PR attributes deeply unless format_pr_data_for_llm is tested
    return mock_g

# Use pytest's tmp_path fixture for a temporary directory
# Use mocker fixture provided by pytest-mock
@patch('main.datetime') # Mock the datetime module used in main
@patch('main.Github')   # Mock the Github class used in main
@patch('main.format_pr_data_for_llm') # Mock the data formatting function
def test_single_pr_output(mock_format_pr, mock_Github, mock_datetime, tmp_path, mock_github, mocker):
    """
    Tests the script's output for a single PR number.
    Checks if the timestamped directory is created and the file is saved correctly.
    """
    # --- Setup Mocks ---
    mock_datetime.datetime.now.return_value = FIXED_DATETIME
    mock_Github.return_value = mock_github # Use the fixture for Github() call
    mock_format_pr.return_value = DUMMY_PR_DATA # Return dummy data

    # Mock sys.argv or argparse directly. Patching parse_args is often cleaner.
    repo_name = "owner/repo"
    pr_num = 123
    base_filename = "output_context.txt"
    args_list = [repo_name, str(pr_num), "--output", base_filename]

    mocker.patch('argparse.ArgumentParser.parse_args',
                 return_value=main.argparse.Namespace(
                     repo=repo_name,
                     pr_numbers=[pr_num],
                     output=base_filename,
                     token=None,        # Simulate no token provided
                     public=True        # Simulate running in public mode
                 ))

    # --- Execute ---
    # Change CWD to tmp_path so the script writes output there
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        main.main()
    finally:
        os.chdir(original_cwd) # Change back to original CWD

    # --- Assert ---
    # 1. Check if the timestamped directory was created inside tmp_path
    expected_dir_path = tmp_path / EXPECTED_TIMESTAMP_DIR
    assert expected_dir_path.is_dir(), f"Directory '{EXPECTED_TIMESTAMP_DIR}' not found in {tmp_path}"

    # 2. Check if the correct file was created inside the directory
    expected_file_path = expected_dir_path / base_filename # Single PR uses base name
    assert expected_file_path.is_file(), f"File '{base_filename}' not found in '{expected_dir_path}'"

    # 3. Check if the file content is what the mocked function returned
    assert expected_file_path.read_text(encoding='utf-8') == DUMMY_PR_DATA

    # 4. Check if format_pr_data_for_llm was called correctly
    mock_format_pr.assert_called_once_with(repo_name, pr_num, mock_github)


@patch('main.datetime')
@patch('main.Github')
@patch('main.format_pr_data_for_llm')
def test_multiple_pr_output(mock_format_pr, mock_Github, mock_datetime, tmp_path, mock_github, mocker):
    """
    Tests the script's output for multiple PR numbers.
    Checks if the timestamped directory is created and files are named correctly.
    """
    # --- Setup Mocks ---
    mock_datetime.datetime.now.return_value = FIXED_DATETIME
    mock_Github.return_value = mock_github
    mock_format_pr.return_value = DUMMY_PR_DATA

    # Mock args
    repo_name = "another/repo"
    pr_nums = [45, 67]
    base_filename = "multi_pr_out.txt"
    args_list = [repo_name, str(pr_nums[0]), str(pr_nums[1]), "--output", base_filename]

    mocker.patch('argparse.ArgumentParser.parse_args',
                 return_value=main.argparse.Namespace(
                     repo=repo_name,
                     pr_numbers=pr_nums,
                     output=base_filename,
                     token='fake-token', # Simulate token provided
                     public=False
                 ))

    # --- Execute ---
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        main.main()
    finally:
        os.chdir(original_cwd)

    # --- Assert ---
    # 1. Check directory creation
    expected_dir_path = tmp_path / EXPECTED_TIMESTAMP_DIR
    assert expected_dir_path.is_dir(), f"Directory '{EXPECTED_TIMESTAMP_DIR}' not found in {tmp_path}"

    # 2. Check files for each PR
    expected_filename_1 = f"pr_{pr_nums[0]}_{base_filename}"
    expected_file_path_1 = expected_dir_path / expected_filename_1
    assert expected_file_path_1.is_file(), f"File '{expected_filename_1}' not found in '{expected_dir_path}'"
    assert expected_file_path_1.read_text(encoding='utf-8') == DUMMY_PR_DATA

    expected_filename_2 = f"pr_{pr_nums[1]}_{base_filename}"
    expected_file_path_2 = expected_dir_path / expected_filename_2
    assert expected_file_path_2.is_file(), f"File '{expected_filename_2}' not found in '{expected_dir_path}'"
    assert expected_file_path_2.read_text(encoding='utf-8') == DUMMY_PR_DATA

    # 3. Check calls to format_pr_data_for_llm
    assert mock_format_pr.call_count == len(pr_nums)
    mock_format_pr.assert_any_call(repo_name, pr_nums[0], mock_github)
    mock_format_pr.assert_any_call(repo_name, pr_nums[1], mock_github)

    # 4. Check Github Authentication call (since token was provided)
    mock_github.get_user.assert_called_once()