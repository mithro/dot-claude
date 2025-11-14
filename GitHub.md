# GitHub Repository Default Settings

This file contains the default settings for new GitHub repositories and the GitHub CLI commands to configure them.

## Quick Setup Commands

After creating a new repository, run these commands to apply the default settings:

```bash
# Set the repository name (replace with your actual repo)
REPO="owner/repo-name"

# Disable wiki, projects, and discussions
gh repo edit $REPO --enable-wiki=false --enable-projects=false

# Note: Discussions can only be disabled via web UI or API
gh api repos/$REPO -X PATCH -f has_discussions=false

# Configure merge options - only allow merge commits
gh repo edit $REPO \
  --allow-squash-merge=false \
  --allow-rebase-merge=false \
  --allow-merge-commit=true

# Enable automatic deletion of head branches after merge
gh repo edit $REPO --delete-branch-on-merge=true

# Enable secret scanning (requires GitHub Advanced Security for private repos)
gh api repos/$REPO -X PATCH -f security_and_analysis[secret_scanning][status]=enabled

# Enable secret scanning push protection
gh api repos/$REPO -X PATCH -f security_and_analysis[secret_scanning_push_protection][status]=enabled

# Enable always suggest updating pull request branches
gh api repos/$REPO -X PATCH -f allow_update_branch=true

# Enable Git LFS objects in archives
gh api repos/$REPO -X PATCH -f has_downloads=true

# Protect the default branch (usually 'main' or 'master')
DEFAULT_BRANCH=$(gh repo view $REPO --json defaultBranchRef --jq .defaultBranchRef.name)
gh api repos/$REPO/branches/$DEFAULT_BRANCH/protection -X PUT -f required_status_checks=null \
  -f enforce_admins=false \
  -f required_pull_request_reviews=null \
  -f restrictions=null \
  -f allow_force_pushes=false \
  -f allow_deletions=false
```

## Individual Setting Details

### 1. Enable Secrets Detection

```bash
# Enable secret scanning
gh api repos/$REPO -X PATCH -f security_and_analysis[secret_scanning][status]=enabled

# Enable secret scanning push protection (prevents committing secrets)
gh api repos/$REPO -X PATCH -f security_and_analysis[secret_scanning_push_protection][status]=enabled
```

**Note**: Secret scanning is automatically available for public repositories. For private repositories, it requires GitHub Advanced Security to be enabled for your organization.

### 2. Prevent Force Pushing the Default Branch

```bash
# Get the default branch name
DEFAULT_BRANCH=$(gh repo view $REPO --json defaultBranchRef --jq .defaultBranchRef.name)

# Apply branch protection to prevent force pushes
gh api repos/$REPO/branches/$DEFAULT_BRANCH/protection -X PUT -f required_status_checks=null \
  -f enforce_admins=false \
  -f required_pull_request_reviews=null \
  -f restrictions=null \
  -f allow_force_pushes=false \
  -f allow_deletions=false
```

### 3. Disable Wiki, Projects, and Discussions

```bash
# Disable wiki and projects
gh repo edit $REPO --enable-wiki=false --enable-projects=false

# Disable discussions (requires API call)
gh api repos/$REPO -X PATCH -f has_discussions=false
```

### 4. Disable Everything But Merge Pull Requests

```bash
# Only allow merge commits (disable squash and rebase merge)
gh repo edit $REPO \
  --allow-squash-merge=false \
  --allow-rebase-merge=false \
  --allow-merge-commit=true
```

### 5. Enable Always Suggest Updating Pull Request Branches

```bash
# Enable the "Update branch" button on pull requests
gh api repos/$REPO -X PATCH -f allow_update_branch=true
```

### 6. Enable Automatically Delete Head Branches

```bash
# Automatically delete head branches after PR merge
gh repo edit $REPO --delete-branch-on-merge=true
```

### 7. Enable Include Git LFS Objects in Archives

```bash
# This is controlled by the has_downloads setting
gh api repos/$REPO -X PATCH -f has_downloads=true
```

## Verification Commands

To verify the settings have been applied:

```bash
# View current repository settings
gh repo view $REPO --json hasWikiEnabled,hasProjectsEnabled,hasDiscussionsEnabled,deleteBranchOnMerge

# View merge settings
gh repo view $REPO --json squashMergeAllowed,mergeCommitAllowed,rebaseMergeAllowed

# View branch protection rules
gh api repos/$REPO/branches/$DEFAULT_BRANCH/protection

# View security settings
gh api repos/$REPO --jq '.security_and_analysis'
```

## Notes

- Replace `$REPO` with your repository in the format `owner/repo-name`
- Some settings may require specific permissions or organization/account features
- Secret scanning for private repos requires GitHub Advanced Security
- Branch protection rules can be customized further based on your needs
