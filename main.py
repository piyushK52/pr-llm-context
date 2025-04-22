import os
import argparse
from github import Github, GithubException, UnknownObjectException

# --- Configuration ---
# Maximum combined additions and deletions for a file's diff to be included
MAX_DIFF_LINES = 500
# Environment variable name for the GitHub token
GITHUB_TOKEN_ENV_VAR = 'GITHUB_TOKEN'
# Default output filename
DEFAULT_OUTPUT_FILE = 'pr_llm_context.txt'

def format_pr_data_for_llm(repo_name, pr_number, g):
    """
    Fetches PR details, conversation, and filtered file changes,
    then formats them into a text string suitable for an LLM.

    Args:
        repo_name (str): The repository name in 'owner/repo' format.
        pr_number (int): The pull request number.
        g (Github): An authenticated PyGithub instance.

    Returns:
        str: A formatted string containing the PR data, or None on error.
    """
    try:
        repo = g.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
    except UnknownObjectException:
        print(f"Error: Repository '{repo_name}' or PR #{pr_number} not found.")
        return None
    except GithubException as e:
        print(f"Error accessing GitHub: {e}")
        return None

    output_lines = []

    # --- PR Details ---
    output_lines.append(f"### GitHub Pull Request Analysis ###")
    output_lines.append(f"Repository: {repo_name}")
    output_lines.append(f"PR Number: #{pr_number}")
    output_lines.append(f"Title: {pr.title}")
    output_lines.append(f"Author: {pr.user.login}")
    output_lines.append(f"State: {pr.state}")
    output_lines.append(f"Created At: {pr.created_at}")
    if pr.merged:
        output_lines.append(f"Merged At: {pr.merged_at} by {pr.merged_by.login}")
    elif pr.closed_at:
        output_lines.append(f"Closed At: {pr.closed_at}")
    output_lines.append("\n---\n") # Separator

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
            output_lines.append(f"\n* Comment by {comment.user.login} at {comment.created_at} on {comment.path} (line ~{comment.line}):") # Position might be more complex
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
        for file in files_changed:
            output_lines.append(f"--- File: {file.filename} ---")
            output_lines.append(f"Status: {file.status}") # added, modified, removed, renamed
            output_lines.append(f"Changes: +{file.additions} / -{file.deletions}")

            total_changes = file.additions + file.deletions
            if total_changes >= MAX_DIFF_LINES:
                output_lines.append(f"[Diff skipped: Exceeds line limit ({total_changes} lines)]")
            elif file.patch: # Check if patch exists (might be None for binary files etc.)
                 output_lines.append("```diff")
                 # Indent patch lines slightly for readability if needed, but LLMs often handle raw diffs well
                 output_lines.append(file.patch)
                 output_lines.append("```")
            else:
                output_lines.append("[No diff available or applicable (e.g., binary file)]")
            output_lines.append("\n") # Add newline separation between files
    else:
        output_lines.append("[No files changed in this PR]")

    output_lines.append("\n### End of PR Analysis ###")

    return "\n".join(output_lines)

def main():
    parser = argparse.ArgumentParser(description="Fetch GitHub PR conversation and file changes for LLM input.")
    parser.add_argument("repo", help="Repository name in 'owner/repo' format.")
    parser.add_argument("pr_number", type=int, help="Pull Request number.")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT_FILE,
                        help=f"Output text file name (default: {DEFAULT_OUTPUT_FILE}).")
    parser.add_argument("-t", "--token", help="GitHub Personal Access Token (optional for public repos).")
    parser.add_argument("--public", action="store_true", help="Force public repository mode (no token required).")

    args = parser.parse_args()

    # Get GitHub Token
    token = args.token or os.getenv(GITHUB_TOKEN_ENV_VAR)
    
    # Initialize GitHub client
    try:
        if token and not args.public:
            g = Github(token)
            # Trigger a simple API call to check authentication
            _ = g.get_user().login
            print("Successfully authenticated with GitHub.")
        else:
            # Initialize without authentication for public repos
            g = Github()
            print("Running in public repository mode (no authentication).")
            print("Note: Rate limits will be lower and some features may be restricted.")
            
        # Fetch and format data
        print(f"Fetching data for {args.repo} PR #{args.pr_number}...")
        formatted_data = format_pr_data_for_llm(args.repo, args.pr_number, g)

        if formatted_data:
            # Write to file
            try:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(formatted_data)
                print(f"Successfully wrote PR data to '{args.output}'")
            except IOError as e:
                print(f"Error writing to file '{args.output}': {e}")
                exit(1)
        else:
            print("Failed to generate PR data.")
            exit(1)
            
    except GithubException as e:
        if e.status == 401:  # Unauthorized
            print("Error: Invalid GitHub token.")
            print("For public repositories, you can run with the --public flag to skip authentication.")
            exit(1)
        elif e.status == 403:  # Forbidden/Rate limited
            print(f"Error: Rate limit exceeded or access forbidden.")
            print("Consider using a GitHub token with the -t option or GITHUB_TOKEN environment variable.")
            exit(1)
        else:
            print(f"Error connecting to GitHub: {e}")
            exit(1)

if __name__ == "__main__":
    main()