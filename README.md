# PR Context

A simple python script to pull github PR/Issue context (diff + comments) that can be fed into LLMs.

# Usage

1. Go to https://github.com/settings/tokens and create a personal token. Set it inside main.py for GITHUB_TOKEN_ENV_VAR.

2. Make sure you have UV installed, then run:
   ```
   uv run main.py author_name/repo_name pr_number1 pr_number2 issue_number_1 ...
   ```

   e.g.
   ```
   uv run main.py pytorch/pytorch 151848
   ```

# TODO
- [ ] Convert into a python package
- [ ] Add support for function context trees (big one!)
