import os
import argparse
import datetime
from github import Github, GithubException, UnknownObjectException, Repository, Issue, Commit # Added Issue and Commit import
from dotenv import load_dotenv

load_dotenv(override=True)

# --- Configuration ---
# Maximum combined additions and deletions for a file's diff to be included (for PRs and Commits)
MAX_DIFF_LINES = 500
# Environment variable name for the GitHub token
GITHUB_TOKEN_ENV_VAR = os.getenv('GITHUB_TOKEN_ENV_VAR', 'YOUR_GITHUB_TOKEN')
# Default *base* output filename prefix (will be placed inside the timestamped folder)
DEFAULT_OUTPUT_PREFIX = 'item'

# --- Formatting Functions ---

def format_commit_data_for_llm(repo: Repository, commit_sha: str):
    """
    Fetches Commit details and file changes, then formats them into
    a text string suitable for an LLM.
    """
    commit = repo.get_commit(commit_sha)
    output_lines = []

    # --- Commit Details ---
    output_lines.append(f"### GitHub Commit Analysis ###")
    output_lines.append(f"Repository: {repo.full_name}")
    output_lines.append(f"SHA: {commit.sha}")
    if commit.author:
        output_lines.append(f"Author: {commit.author.login} ({commit.commit.author.name})")
    if commit.committer:
        output_lines.append(f"Committer: {commit.committer.login} ({commit.commit.committer.name})")
    output_lines.append(f"Date: {commit.commit.author.date}")
    output_lines.append("\n---\n")

    # --- Commit Message ---
    output_lines.append(f"### Commit Message ###")
    output_lines.append(commit.commit.message if commit.commit.message else "[No commit message]")
    output_lines.append("\n---\n")

    # --- File Changes (Diffs) ---
    output_lines.append(f"### File Changes (Ignoring files with >{MAX_DIFF_LINES} lines changed) ###\n")

    files_in_commit = list(commit.files)
    total_files = len(files_in_commit)

    if total_files > 0:
        file_count = 0
        for file in files_in_commit:
            file_count += 1
            output_lines.append(f"--- File {file_count}/{total_files}: {file.filename} ---")
            output_lines.append(f"Status: {file.status}")
            output_lines.append(f"Changes: +{file.additions} / -{file.deletions}")

            total_changes = file.additions + file.deletions
            if total_changes > MAX_DIFF_LINES:
                output_lines.append(f"[Diff skipped: Exceeds line limit ({total_changes} > {MAX_DIFF_LINES} lines)]")
            elif file.patch:
                 output_lines.append("```diff")
                 output_lines.append(file.patch)
                 output_lines.append("```")
            else:
                output_lines.append("[No diff available or applicable]")
            output_lines.append("\n")
    else:
        output_lines.append("[No files changed in this commit]")

    output_lines.append("\n### End of Commit Analysis ###")
    return "\n".join(output_lines)

def format_issue_data_for_llm(repo: Repository, issue: Issue):
    """
    Fetches Issue details and conversation, then formats them into
    a text string suitable for an LLM.

    Args:
        repo (Repository): The PyGithub Repository object.
        issue (Issue): The PyGithub Issue object.

    Returns:
        str: A formatted string containing the Issue data.
    """
    output_lines = []

    # --- Issue Details ---
    output_lines.append(f"### GitHub Issue Analysis ###")
    output_lines.append(f"Repository: {repo.full_name}")
    output_lines.append(f"Issue Number: #{issue.number}")
    output_lines.append(f"Title: {issue.title}")
    output_lines.append(f"Author: {issue.user.login}")
    output_lines.append(f"State: {issue.state}")
    output_lines.append(f"Created At: {issue.created_at}")
    if issue.closed_at:
        output_lines.append(f"Closed At: {issue.closed_at} by {issue.closed_by.login if issue.closed_by else 'unknown'}")

    # --- Labels, Assignees, Milestone ---
    if issue.labels:
        output_lines.append(f"Labels: {', '.join([label.name for label in issue.labels])}")
    if issue.assignees:
        output_lines.append(f"Assignees: {', '.join([assignee.login for assignee in issue.assignees])}")
    if issue.milestone:
        output_lines.append(f"Milestone: {issue.milestone.title}")

    output_lines.append("\n---\n")

    # --- Issue Description (Body) ---
    output_lines.append(f"### Issue Description ###")
    output_lines.append(issue.body if issue.body else "[No description provided]")
    output_lines.append("\n---\n")

    # --- Conversation History ---
    output_lines.append(f"### Conversation History ###\n")
    comments = issue.get_comments()
    if comments.totalCount > 0:
        for comment in comments:
            output_lines.append(f"\n* Comment by {comment.user.login} at {comment.created_at}:")
            output_lines.append(f"    ```\n    {comment.body}\n    ```")
    else:
        output_lines.append("[No comments]")
    output_lines.append("\n---\n")

    output_lines.append("\n### End of Issue Analysis ###")
    return "\n".join(output_lines)


def format_pr_data_for_llm(repo: Repository, pr_number: int):
    """
    Fetches PR details, conversation, and filtered file changes,
    then formats them into a text string suitable for an LLM.

    Args:
        repo (Repository): The PyGithub Repository object.
        pr_number (int): The pull request number.

    Returns:
        str: A formatted string containing the PR data, or None on error (handled upstream).
    """
    pr = repo.get_pull(pr_number)

    output_lines = []

    # --- PR Details ---
    output_lines.append(f"### GitHub Pull Request Analysis ###")
    output_lines.append(f"Repository: {repo.full_name}")
    output_lines.append(f"PR Number: #{pr_number}")
    output_lines.append(f"Title: {pr.title}")
    output_lines.append(f"Author: {pr.user.login}")
    output_lines.append(f"State: {pr.state}")
    output_lines.append(f"Created At: {pr.created_at}")
    if pr.merged:
        output_lines.append(f"Merged At: {pr.merged_at} by {pr.merged_by.login if pr.merged_by else 'unknown'}")
    elif pr.closed_at:
        output_lines.append(f"Closed At: {pr.closed_at}")
    output_lines.append(f"Changed Files: {pr.changed_files}")
    output_lines.append(f"Additions: {pr.additions}")
    output_lines.append(f"Deletions: {pr.deletions}")


    output_lines.append("\n---\n")

    # --- PR Description (Body) ---
    output_lines.append(f"### PR Description ###")
    output_lines.append(pr.body if pr.body else "[No description provided]")
    output_lines.append("\n---\n")

    # --- Conversation History ---
    output_lines.append(f"### Conversation History ###\n")

    # 1. Issue Comments (General PR comments)
    output_lines.append("--- General Comments ---")
    comments = pr.get_issue_comments()
    if comments.totalCount > 0:
        for comment in comments:
            output_lines.append(f"\n* Comment by {comment.user.login} at {comment.created_at}:")
            output_lines.append(f"    ```\n    {comment.body}\n    ```")
    else:
        output_lines.append("[No general comments]")
    output_lines.append("\n")

    # 2. Review Comments (Inline code comments)
    output_lines.append("--- Review Comments (Inline) ---")
    review_comments = pr.get_review_comments()
    if review_comments.totalCount > 0:
        for comment in review_comments:
            output_lines.append(f"\n* Comment by {comment.user.login} at {comment.created_at} on {comment.path} (line ~{comment.line}):")
            output_lines.append(f"    Relevant Code Diff:\n    ```diff\n{comment.diff_hunk}\n    ```")
            output_lines.append(f"    Comment:\n    ```\n    {comment.body}\n    ```")
    else:
        output_lines.append("[No inline review comments]")
    output_lines.append("\n")

    # 3. Reviews (Approval, Request Changes, General Review Comments)
    output_lines.append("--- Reviews (Approve/Request Changes/Comment) ---")
    reviews = pr.get_reviews()
    if reviews.totalCount > 0:
        for review in reviews:
            # Skip reviews that only consist of inline comments (already captured)
            if review.body or review.state != 'COMMENTED':
                 output_lines.append(f"\n* Review by {review.user.login} at {review.submitted_at}")
                 output_lines.append(f"    State: {review.state}") # e.g., APPROVED, CHANGES_REQUESTED, COMMENTED
                 if review.body:
                     output_lines.append(f"    Comment:\n    ```\n    {review.body}\n    ```")
                 else:
                     output_lines.append("    [No general review comment]")

    else:
        output_lines.append("[No formal reviews submitted]")
    output_lines.append("\n---\n")

    # --- File Changes (Diffs) ---
    output_lines.append(f"### File Changes (Ignoring files with >{MAX_DIFF_LINES} lines changed) ###\n")
    files_changed = pr.get_files()
    if files_changed.totalCount > 0:
        file_count = 0
        for file in files_changed:
            file_count += 1
            output_lines.append(f"--- File {file_count}/{files_changed.totalCount}: {file.filename} ---")
            output_lines.append(f"Status: {file.status}") # added, modified, removed, renamed
            output_lines.append(f"Changes: +{file.additions} / -{file.deletions}")

            total_changes = file.additions + file.deletions
            if total_changes > MAX_DIFF_LINES: # Use > instead of >=
                output_lines.append(f"[Diff skipped: Exceeds line limit ({total_changes} > {MAX_DIFF_LINES} lines)]")
            elif file.patch: # Check if patch exists (might be None for binary files etc.)
                 output_lines.append("```diff")
                 # Indent patch lines slightly for readability if needed, but LLMs often handle raw diffs well
                 output_lines.append(file.patch)
                 output_lines.append("```")
            else:
                output_lines.append("[No diff available or applicable]")
            output_lines.append("\n") # Add newline separation between files
    else:
        output_lines.append("[No files changed in this PR]")

    output_lines.append("\n### End of PR Analysis ###")

    return "\n".join(output_lines)

# --- Main Execution ---

def main():
    parser = argparse.ArgumentParser(description="Fetch GitHub Issue, PR, or Commit data for LLM input, saving into a timestamped folder.")
    parser.add_argument("repo", help="Repository name in 'owner/repo' format.")
    # Changed argument name and help text
    parser.add_argument("items", nargs='+', type=str, help="Issue/PR numbers or Commit SHAs (space separated).")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT_PREFIX,
                        help=f"Base output filename prefix to use within the timestamped folder (default: {DEFAULT_OUTPUT_PREFIX}).")
    parser.add_argument("-t", "--token", help="GitHub Personal Access Token (optional for public repos).")
    parser.add_argument("--public", action="store_true", help="Force public repository mode (no token required).")

    args = parser.parse_args()

    token = args.token or GITHUB_TOKEN_ENV_VAR
    now = datetime.datetime.now()
    timestamp_str = now.strftime("output_%Y_%m_%d_%H%M%S")
    output_dir = timestamp_str

    try:
        os.makedirs(output_dir, exist_ok=True)
        print(f"Created output directory: '{output_dir}'")
    except OSError as e:
        print(f"Error creating directory '{output_dir}': {e}")
        exit(1)

    g = None
    try:
        if token and not args.public:
            g = Github(token)
            _ = g.get_user().login
            print("Successfully authenticated with GitHub token.")
        else:
            g = Github()
            print("Running in public repository mode (no authentication).")
            if not args.public and not token:
                 print(f"Tip: Provide a token via -t or the {GITHUB_TOKEN_ENV_VAR} env var for higher rate limits.")
            print("Note: Rate limits will be lower and some features might be restricted.")

        repo = g.get_repo(args.repo)
        print(f"Accessing repository: {repo.full_name}")

    except GithubException as e:
        if e.status == 401:  # Unauthorized
            print("Error: Invalid GitHub token or token lacks permissions for this repository.")
            print("Please provide a valid Personal Access Token with 'repo' scope.")
            print(f"Use the -t option or set the {GITHUB_TOKEN_ENV_VAR} environment variable.")
            if not token:
                 print("For public repositories, you can try running with the --public flag.")
            exit(1)
        elif e.status == 404: # Not Found (Repo)
             print(f"Error: Repository '{args.repo}' not found or not accessible with the provided token/permissions.")
             exit(1)
        elif e.status == 403: # Forbidden/Rate limited
            print(f"Error: Rate limit exceeded or access forbidden (status code 403).")
            print("Consider using a GitHub token if you aren't already.")
            print("If using a token, check its permissions or wait for the rate limit to reset.")
            exit(1)
        else:
            print(f"Error connecting to GitHub or getting repository: {e}")
            exit(1)
    except Exception as e: # Catch other potential errors like network issues during connection
        print(f"An unexpected error occurred during GitHub connection: {e}")
        exit(1)


    # --- Process Each Item ---
    for item_str in args.items:
        print(f"\nProcessing {args.repo} Item '{item_str}'...")
        formatted_data = None
        item_type = "unknown"
        item_id_for_filename = item_str # Use the original string for filename

        try:
            # Try to convert to int. If it works, it's an Issue or PR number.
            item_number = int(item_str)
            issue = repo.get_issue(item_number)
            if issue.pull_request:
                print(f"Item #{item_number} is a Pull Request.")
                item_type = "pr"
                formatted_data = format_pr_data_for_llm(repo, item_number)
            else:
                print(f"Item #{item_number} is an Issue.")
                item_type = "issue"
                formatted_data = format_issue_data_for_llm(repo, issue)

        except ValueError:
            # If conversion to int fails, treat it as a commit SHA.
            print(f"Item '{item_str}' appears to be a Commit SHA.")
            item_type = "commit"
            try:
                formatted_data = format_commit_data_for_llm(repo, item_str)
                # Use short SHA for cleaner filename
                item_id_for_filename = item_str[:7]
            except UnknownObjectException:
                print(f"Error: Commit with SHA '{item_str}' not found in '{repo.full_name}'. Skipping.")
                continue
            except Exception as e:
                print(f"An unexpected error occurred processing Commit '{item_str}': {e}. Skipping.")
                continue

        except UnknownObjectException:
            print(f"Error: Item #{item_number} not found in repository '{repo.full_name}'. Skipping.")
            continue
        except GithubException as e:
            print(f"Error fetching details for Item '{item_str}': {e}. Skipping.")
            continue
        except Exception as e:
             print(f"An unexpected error occurred processing Item '{item_str}': {e}. Skipping.")
             continue

        # --- Write Output File ---
        if formatted_data:
            base_filename = f"{args.output}_{item_type}_{item_id_for_filename}.txt"
            full_output_path = os.path.join(output_dir, base_filename)

            try:
                with open(full_output_path, 'w', encoding='utf-8') as f:
                    f.write(formatted_data)
                print(f"Successfully wrote {item_type.upper()} data to '{full_output_path}'")
            except IOError as e:
                print(f"Error writing to file '{full_output_path}': {e}")
                continue
        else:
            print(f"Failed to generate formatted data for Item '{item_str}'.")


if __name__ == "__main__":
    main()