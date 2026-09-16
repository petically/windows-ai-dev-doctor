You are also responsible for maintaining the Git repository and publishing the project to GitHub.

First inspect the current Git state.

If this directory is not yet a Git repository, initialize it using `main` as the default branch.

Throughout development:

- use meaningful Git commits
- commit at logical milestones rather than after every tiny change
- inspect `git status` and `git diff` before committing
- never commit secrets, API keys, access tokens, credentials, local caches, build artifacts, virtual environments, IDE state, or machine-specific files
- maintain an appropriate `.gitignore`
- run relevant tests before important commits
- do not use `git push --force`
- do not rewrite published history unless explicitly instructed
- do not delete remote branches or repositories
- do not modify GitHub account settings

Before the first GitHub push, perform a security review of all tracked files and verify that no secrets or personal information are included.

If GitHub CLI (`gh`) is authenticated, create the GitHub repository automatically if no remote repository exists.

Repository name:

`windows-ai-dev-doctor`

Default visibility:

`public`

Use the current authenticated GitHub account.

If appropriate, use:

```bash
gh repo create windows-ai-dev-doctor --public --source=. --remote=origin --push
```

If the repository already exists remotely, do not create a duplicate. Inspect the existing remote configuration and use it.

After each meaningful development milestone:

1. run the appropriate tests
2. inspect changed files
3. commit with a conventional and meaningful commit message
4. push the commit to GitHub

Examples:

```text
chore: initialize project structure
feat: add diagnostic framework
feat: add Windows system diagnostics
feat: add network and proxy diagnostics
feat: add AI application diagnostics
feat: add report generation
test: expand diagnostic test coverage
docs: complete project documentation
ci: add Windows build workflow
```

Before publishing a release:

- ensure the working tree is clean
- run the complete test suite
- run linting and type checking
- build the Windows executable
- verify the packaged executable
- inspect the repository for accidental secrets
- ensure README and CHANGELOG are current

When the project reaches the planned `v0.1.0` milestone, create an annotated Git tag and GitHub Release if the GitHub CLI authentication and repository permissions allow it.

Do not publish a release if tests or packaging fail.

At completion, report:

- GitHub repository URL
- current branch
- latest commit
- release/tag created
- whether the working tree is clean
- whether all tests passed