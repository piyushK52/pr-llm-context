import os
import datetime
import pytest
from unittest.mock import patch, MagicMock, call
import main

# --- Test Constants ---
FIXED_DATETIME = datetime.datetime(2024, 10, 20, 15, 30, 45)
EXPECTED_TIMESTAMP_DIR = FIXED_DATETIME.strftime("output_%Y_%m_%d_%H%M%S")
DUMMY_PR_DATA = "### GitHub Pull Request Analysis ###\nFake PR data content."
DUMMY_ISSUE_DATA = "### GitHub Issue Analysis ###\nFake Issue data content."
DUMMY_COMMIT_DATA = "### GitHub Commit Analysis ###\nFake Commit data content."
REPO_NAME = "owner/repo"
COMMIT_SHA_FULL = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
COMMIT_SHA_SHORT = COMMIT_SHA_FULL[:7]

# --- Mock Fixtures ---

@pytest.fixture
def mock_github_objects(mocker):
    """Provides mock Github, Repo, and other objects."""
    mock_g = MagicMock(spec=main.Github)
    mock_repo = MagicMock()
    mock_user = MagicMock()
    mock_user.login = 'testuser'

    mock_g.get_user.return_value = mock_user
    mock_g.get_repo.return_value = mock_repo
    mock_repo.full_name = REPO_NAME

    return {"g": mock_g, "repo": mock_repo}

# --- Test Functions ---

@patch('main.datetime')
@patch('main.Github')
@patch('main.format_pr_data_for_llm')
@patch('main.format_issue_data_for_llm')
@patch('main.format_commit_data_for_llm')
def test_single_item_pr_output(mock_format_commit, mock_format_issue, mock_format_pr, mock_Github, mock_datetime, tmp_path, mocker, mock_github_objects):
    """Tests output for a single PR number."""
    mock_datetime.datetime.now.return_value = FIXED_DATETIME
    mock_Github.return_value = mock_github_objects["g"]
    mock_format_pr.return_value = DUMMY_PR_DATA

    item_num = '123'
    output_prefix = "context_pr"

    mock_issue_obj = MagicMock(spec=main.Issue)
    mock_issue_obj.pull_request = {'html_url': 'fake_url'}
    mock_github_objects["repo"].get_issue.return_value = mock_issue_obj

    mocker.patch('argparse.ArgumentParser.parse_args', return_value=main.argparse.Namespace(
        repo=REPO_NAME, items=[item_num], output=output_prefix, token=None, public=True
    ))

    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        main.main()
    finally:
        os.chdir(original_cwd)

    expected_file = tmp_path / EXPECTED_TIMESTAMP_DIR / f"{output_prefix}_pr_{item_num}.txt"
    assert expected_file.is_file()
    assert expected_file.read_text(encoding='utf-8') == DUMMY_PR_DATA
    mock_format_pr.assert_called_once_with(mock_github_objects["repo"], int(item_num))
    mock_format_issue.assert_not_called()
    mock_format_commit.assert_not_called()


@patch('main.datetime')
@patch('main.Github')
@patch('main.format_pr_data_for_llm')
@patch('main.format_issue_data_for_llm')
@patch('main.format_commit_data_for_llm')
def test_single_item_issue_output(mock_format_commit, mock_format_issue, mock_format_pr, mock_Github, mock_datetime, tmp_path, mocker, mock_github_objects):
    """Tests output for a single Issue number."""
    mock_datetime.datetime.now.return_value = FIXED_DATETIME
    mock_Github.return_value = mock_github_objects["g"]
    mock_format_issue.return_value = DUMMY_ISSUE_DATA

    item_num = '456'
    output_prefix = "context_issue"

    mock_issue_obj = MagicMock(spec=main.Issue)
    mock_issue_obj.pull_request = None
    mock_github_objects["repo"].get_issue.return_value = mock_issue_obj

    mocker.patch('argparse.ArgumentParser.parse_args', return_value=main.argparse.Namespace(
        repo=REPO_NAME, items=[item_num], output=output_prefix, token=None, public=True
    ))

    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        main.main()
    finally:
        os.chdir(original_cwd)

    expected_file = tmp_path / EXPECTED_TIMESTAMP_DIR / f"{output_prefix}_issue_{item_num}.txt"
    assert expected_file.is_file()
    assert expected_file.read_text(encoding='utf-8') == DUMMY_ISSUE_DATA
    mock_format_issue.assert_called_once_with(mock_github_objects["repo"], mock_issue_obj)
    mock_format_pr.assert_not_called()
    mock_format_commit.assert_not_called()


@patch('main.datetime')
@patch('main.Github')
@patch('main.format_pr_data_for_llm')
@patch('main.format_issue_data_for_llm')
@patch('main.format_commit_data_for_llm')
def test_single_item_commit_output(mock_format_commit, mock_format_issue, mock_format_pr, mock_Github, mock_datetime, tmp_path, mocker, mock_github_objects):
    """Tests output for a single commit SHA."""
    mock_datetime.datetime.now.return_value = FIXED_DATETIME
    mock_Github.return_value = mock_github_objects["g"]
    mock_format_commit.return_value = DUMMY_COMMIT_DATA

    output_prefix = "context_commit"

    mocker.patch('argparse.ArgumentParser.parse_args', return_value=main.argparse.Namespace(
        repo=REPO_NAME, items=[COMMIT_SHA_FULL], output=output_prefix, token=None, public=True
    ))

    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        main.main()
    finally:
        os.chdir(original_cwd)

    expected_file = tmp_path / EXPECTED_TIMESTAMP_DIR / f"{output_prefix}_commit_{COMMIT_SHA_SHORT}.txt"
    assert expected_file.is_file()
    assert expected_file.read_text(encoding='utf-8') == DUMMY_COMMIT_DATA
    mock_format_commit.assert_called_once_with(mock_github_objects["repo"], COMMIT_SHA_FULL)


@patch('main.datetime')
@patch('main.Github')
@patch('main.format_pr_data_for_llm')
@patch('main.format_issue_data_for_llm')
@patch('main.format_commit_data_for_llm')
def test_multiple_items_mixed_output(mock_format_commit, mock_format_issue, mock_format_pr, mock_Github, mock_datetime, tmp_path, mocker, mock_github_objects):
    """Tests output for a mix of PR, Issue, and Commit items."""
    mock_datetime.datetime.now.return_value = FIXED_DATETIME
    mock_Github.return_value = mock_github_objects["g"]
    mock_format_pr.return_value = DUMMY_PR_DATA
    mock_format_issue.return_value = DUMMY_ISSUE_DATA
    mock_format_commit.return_value = DUMMY_COMMIT_DATA

    pr_num = '78'
    issue_num = '90'
    commit_sha = COMMIT_SHA_FULL
    items = [pr_num, issue_num, commit_sha]
    output_prefix = "multi_context"

    mock_issue_for_pr = MagicMock(spec=main.Issue, pull_request={'html_url': 'pr_url'})
    mock_issue_for_issue = MagicMock(spec=main.Issue, pull_request=None)
    mock_github_objects["repo"].get_issue.side_effect = lambda num: mock_issue_for_pr if num == int(pr_num) else mock_issue_for_issue
    mock_github_objects["repo"].get_commit.return_value = MagicMock(spec=main.Commit)

    mocker.patch('argparse.ArgumentParser.parse_args', return_value=main.argparse.Namespace(
        repo=REPO_NAME, items=items, output=output_prefix, token='fake-token', public=False
    ))

    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        main.main()
    finally:
        os.chdir(original_cwd)

    expected_dir = tmp_path / EXPECTED_TIMESTAMP_DIR
    # PR
    pr_file = expected_dir / f"{output_prefix}_pr_{pr_num}.txt"
    assert pr_file.is_file()
    assert pr_file.read_text('utf-8') == DUMMY_PR_DATA
    # Issue
    issue_file = expected_dir / f"{output_prefix}_issue_{issue_num}.txt"
    assert issue_file.is_file()
    assert issue_file.read_text('utf-8') == DUMMY_ISSUE_DATA
    # Commit
    commit_file = expected_dir / f"{output_prefix}_commit_{COMMIT_SHA_SHORT}.txt"
    assert commit_file.is_file()
    assert commit_file.read_text('utf-8') == DUMMY_COMMIT_DATA

    mock_format_pr.assert_called_once_with(mock_github_objects["repo"], int(pr_num))
    mock_format_issue.assert_called_once_with(mock_github_objects["repo"], mock_issue_for_issue)
    mock_format_commit.assert_called_once_with(mock_github_objects["repo"], commit_sha)