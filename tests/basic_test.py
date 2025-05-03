import os
import datetime
import pytest
from unittest.mock import patch, MagicMock, ANY, call # Import 'call'
# Assuming your script is named main.py
import main # Import the script to be tested

# --- Test Constants ---
FIXED_DATETIME = datetime.datetime(2024, 10, 20, 15, 30, 45)
EXPECTED_TIMESTAMP_DIR = FIXED_DATETIME.strftime("output_%Y_%m_%d_%H%M%S")
DUMMY_PR_DATA = "### GitHub Pull Request Analysis ###\nFake PR data content."
DUMMY_ISSUE_DATA = "### GitHub Issue Analysis ###\nFake Issue data content."
REPO_NAME = "owner/repo"

# --- Mock Fixtures ---

@pytest.fixture
def mock_github_objects(mocker):
    """Provides mock Github, Repo, Issue, PR, and User objects."""
    mock_g = MagicMock(spec=main.Github)
    mock_repo = MagicMock()
    mock_user = MagicMock()
    mock_issue = MagicMock(spec=main.Issue)
    mock_pr = MagicMock() # Can be simpler if only used as marker/for get_pull

    mock_user.login = 'testuser'
    mock_g.get_user.return_value = mock_user
    mock_g.get_repo.return_value = mock_repo
    mock_repo.full_name = REPO_NAME # Set the full_name attribute used in formatting

    # Store mocks for easy access in tests
    return {
        "g": mock_g,
        "repo": mock_repo,
        "user": mock_user,
        "issue": mock_issue,
        "pr": mock_pr,
    }

# --- Test Functions ---

# Use pytest's tmp_path fixture for a temporary directory
# Use mocker fixture provided by pytest-mock
@patch('main.datetime')
@patch('main.Github')
@patch('main.format_pr_data_for_llm')
@patch('main.format_issue_data_for_llm') # Mock the new function
def test_single_item_pr_output(mock_format_issue, mock_format_pr, mock_Github, mock_datetime, tmp_path, mocker, mock_github_objects):
    """
    Tests the script's output for a single item number identified as a PR.
    """
    # --- Setup Mocks ---
    mock_datetime.datetime.now.return_value = FIXED_DATETIME
    mock_Github.return_value = mock_github_objects["g"] # Use the fixture
    mock_format_pr.return_value = DUMMY_PR_DATA
    # Mock format_issue just in case, should not be called
    mock_format_issue.return_value = "Should not be called for PR"

    item_num = 123
    output_prefix = "context_pr"

    # Configure repo mock to return an "issue" that IS a pull request
    mock_issue_obj_for_pr = MagicMock(spec=main.Issue)
    mock_issue_obj_for_pr.number = item_num
    # Key: Set pull_request attribute to something non-None to identify as PR
    mock_issue_obj_for_pr.pull_request = {'html_url': 'fake_url'} # Presence indicates PR

    # Configure get_issue to return this mock issue when called with item_num
    mock_github_objects["repo"].get_issue.return_value = mock_issue_obj_for_pr
    # Configure get_pull to return a mock PR object (needed by format_pr_data)
    mock_github_objects["repo"].get_pull.return_value = mock_github_objects["pr"]

    # Mock argparse
    mocker.patch('argparse.ArgumentParser.parse_args',
                 return_value=main.argparse.Namespace(
                     repo=REPO_NAME,
                     item_numbers=[item_num], # Use new arg name
                     output=output_prefix,   # Use new arg name/meaning
                     token=None,
                     public=True
                 ))

    # --- Execute ---
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        main.main()
    finally:
        os.chdir(original_cwd)

    # --- Assert ---
    expected_dir_path = tmp_path / EXPECTED_TIMESTAMP_DIR
    assert expected_dir_path.is_dir()

    # Check filename uses prefix, type, and number
    expected_filename = f"{output_prefix}_pr_{item_num}.txt"
    expected_file_path = expected_dir_path / expected_filename
    assert expected_file_path.is_file(), f"File '{expected_filename}' not found"
    assert expected_file_path.read_text(encoding='utf-8') == DUMMY_PR_DATA

    # Check correct functions were called
    mock_github_objects["repo"].get_issue.assert_called_once_with(item_num)
    # format_pr_data is called with repo object and pr_number
    mock_format_pr.assert_called_once_with(mock_github_objects["repo"], item_num)
    mock_format_issue.assert_not_called()


@patch('main.datetime')
@patch('main.Github')
@patch('main.format_pr_data_for_llm')
@patch('main.format_issue_data_for_llm')
def test_single_item_issue_output(mock_format_issue, mock_format_pr, mock_Github, mock_datetime, tmp_path, mocker, mock_github_objects):
    """
    Tests the script's output for a single item number identified as an Issue.
    """
    # --- Setup Mocks ---
    mock_datetime.datetime.now.return_value = FIXED_DATETIME
    mock_Github.return_value = mock_github_objects["g"]
    mock_format_issue.return_value = DUMMY_ISSUE_DATA
    mock_format_pr.return_value = "Should not be called for Issue" # Should not be called

    item_num = 456
    output_prefix = "context_issue"

    # Configure repo mock to return an "issue" that is NOT a pull request
    mock_issue_obj = MagicMock(spec=main.Issue)
    mock_issue_obj.number = item_num
    mock_issue_obj.pull_request = None # Key: Set pull_request to None

    mock_github_objects["repo"].get_issue.return_value = mock_issue_obj

    # Mock argparse
    mocker.patch('argparse.ArgumentParser.parse_args',
                 return_value=main.argparse.Namespace(
                     repo=REPO_NAME,
                     item_numbers=[item_num],
                     output=output_prefix,
                     token=None,
                     public=True
                 ))

    # --- Execute ---
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        main.main()
    finally:
        os.chdir(original_cwd)

    # --- Assert ---
    expected_dir_path = tmp_path / EXPECTED_TIMESTAMP_DIR
    assert expected_dir_path.is_dir()

    expected_filename = f"{output_prefix}_issue_{item_num}.txt"
    expected_file_path = expected_dir_path / expected_filename
    assert expected_file_path.is_file(), f"File '{expected_filename}' not found"
    assert expected_file_path.read_text(encoding='utf-8') == DUMMY_ISSUE_DATA

    # Check correct functions were called
    mock_github_objects["repo"].get_issue.assert_called_once_with(item_num)
    # format_issue_data is called with repo object and the issue object
    mock_format_issue.assert_called_once_with(mock_github_objects["repo"], mock_issue_obj)
    mock_format_pr.assert_not_called()
    mock_github_objects["repo"].get_pull.assert_not_called() # Should not be called for issue

@patch('main.datetime')
@patch('main.Github')
@patch('main.format_pr_data_for_llm')
@patch('main.format_issue_data_for_llm')
def test_multiple_items_mixed_output(mock_format_issue, mock_format_pr, mock_Github, mock_datetime, tmp_path, mocker, mock_github_objects):
    """
    Tests the script's output for multiple item numbers (mix of PR and Issue).
    """
     # --- Setup Mocks ---
    mock_datetime.datetime.now.return_value = FIXED_DATETIME
    mock_Github.return_value = mock_github_objects["g"]
    mock_format_pr.return_value = DUMMY_PR_DATA
    mock_format_issue.return_value = DUMMY_ISSUE_DATA

    pr_num = 78
    issue_num = 90
    item_nums = [pr_num, issue_num]
    output_prefix = "multi_context"

    # Configure mocks for items
    mock_issue_obj_for_pr = MagicMock(spec=main.Issue)
    mock_issue_obj_for_pr.number = pr_num
    mock_issue_obj_for_pr.pull_request = {'html_url': 'fake_pr_url'} # It's a PR

    mock_issue_obj_for_issue = MagicMock(spec=main.Issue)
    mock_issue_obj_for_issue.number = issue_num
    mock_issue_obj_for_issue.pull_request = None # It's an Issue

    # Use side_effect to return different mocks based on input number
    def get_issue_side_effect(number):
        if number == pr_num:
            return mock_issue_obj_for_pr
        elif number == issue_num:
            return mock_issue_obj_for_issue
        else:
            raise main.UnknownObjectException(404, "Not Found", {}) # Simulate not found for others

    mock_github_objects["repo"].get_issue.side_effect = get_issue_side_effect
    mock_github_objects["repo"].get_pull.return_value = mock_github_objects["pr"] # Needed for the PR path

    # Mock argparse
    mocker.patch('argparse.ArgumentParser.parse_args',
                 return_value=main.argparse.Namespace(
                     repo=REPO_NAME,
                     item_numbers=item_nums,
                     output=output_prefix,
                     token='fake-token', # Simulate token
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
    expected_dir_path = tmp_path / EXPECTED_TIMESTAMP_DIR
    assert expected_dir_path.is_dir()

    # Assert PR file
    expected_filename_pr = f"{output_prefix}_pr_{pr_num}.txt"
    expected_file_path_pr = expected_dir_path / expected_filename_pr
    assert expected_file_path_pr.is_file()
    assert expected_file_path_pr.read_text(encoding='utf-8') == DUMMY_PR_DATA

    # Assert Issue file
    expected_filename_issue = f"{output_prefix}_issue_{issue_num}.txt"
    expected_file_path_issue = expected_dir_path / expected_filename_issue
    assert expected_file_path_issue.is_file()
    assert expected_file_path_issue.read_text(encoding='utf-8') == DUMMY_ISSUE_DATA

    # Check function calls
    assert mock_github_objects["repo"].get_issue.call_count == len(item_nums)
    mock_github_objects["repo"].get_issue.assert_has_calls([call(pr_num), call(issue_num)], any_order=True)

    mock_format_pr.assert_called_once_with(mock_github_objects["repo"], pr_num)
    mock_format_issue.assert_called_once_with(mock_github_objects["repo"], mock_issue_obj_for_issue)

    # Check auth call because token was provided
    mock_github_objects["g"].get_user.assert_called_once()


@patch('main.datetime')
@patch('main.Github')
@patch('main.format_pr_data_for_llm')
@patch('main.format_issue_data_for_llm')
def test_nonexistent_item_skipped(mock_format_issue, mock_format_pr, mock_Github, mock_datetime, tmp_path, mocker, mock_github_objects, capsys):
    """
    Tests that a non-existent item number is skipped gracefully.
    """
    # --- Setup Mocks ---
    mock_datetime.datetime.now.return_value = FIXED_DATETIME
    mock_Github.return_value = mock_github_objects["g"]

    non_existent_num = 999
    output_prefix = "context_skip"

    # Configure get_issue to raise UnknownObjectException for the number
    mock_github_objects["repo"].get_issue.side_effect = main.UnknownObjectException(404, "Not Found", {})

    # Mock argparse
    mocker.patch('argparse.ArgumentParser.parse_args',
                 return_value=main.argparse.Namespace(
                     repo=REPO_NAME,
                     item_numbers=[non_existent_num],
                     output=output_prefix,
                     token=None,
                     public=True
                 ))

    # --- Execute ---
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        main.main()
    finally:
        os.chdir(original_cwd)

    # --- Assert ---
    expected_dir_path = tmp_path / EXPECTED_TIMESTAMP_DIR
    assert expected_dir_path.is_dir() # Directory should still be created

    # Check that NO file was created for the non-existent item
    expected_filename = f"{output_prefix}_unknown_{non_existent_num}.txt" # Or any name, it shouldn't exist
    expected_file_path = expected_dir_path / expected_filename
    all_files = list(expected_dir_path.glob('*'))
    assert not any(f.name.endswith(f"_{non_existent_num}.txt") for f in all_files), "File for non-existent item was created"

    # Check that format functions were NOT called
    mock_format_pr.assert_not_called()
    mock_format_issue.assert_not_called()

    # Check that get_issue was called
    mock_github_objects["repo"].get_issue.assert_called_once_with(non_existent_num)

    # Check console output for skipping message (using capsys fixture)
    captured = capsys.readouterr()
    assert f"Error: Item #{non_existent_num} not found" in captured.out
    assert "Skipping." in captured.out