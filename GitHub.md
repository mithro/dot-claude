# GitHub Repository Default Settings

This file contains the default settings for new GitHub repositories and the GitHub CLI commands to configure them.

## Quick Setup Commands

After creating a new repository, run these commands to apply the default settings:

```bash
# Set the repository name (replace with your actual repo)
REPO="owner/repo-name"

# Tag the first commit as v0.0 (enables git describe to work)
git tag v0.0 $(git rev-list --max-parents=0 HEAD)
git push origin v0.0

# Disable wiki and projects
gh repo edit $REPO --enable-wiki=false --enable-projects=false

# Disable discussions (requires GraphQL API - REST API doesn't support this)
REPO_ID=$(gh api graphql -f query="query { repository(owner: \"${REPO%/*}\", name: \"${REPO#*/}\") { id } }" --jq '.data.repository.id')
gh api graphql -f query="mutation { updateRepository(input: { repositoryId: \"$REPO_ID\", hasDiscussionsEnabled: false }) { repository { hasDiscussionsEnabled } } }"

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

# Note: "Include Git LFS objects in archives" is UI-only
# No API endpoint available - must be set manually at:
# https://github.com/$REPO/settings (under "Archives" section)

# Protect the default branch (usually 'main' or 'master')
DEFAULT_BRANCH=$(gh repo view $REPO --json defaultBranchRef --jq .defaultBranchRef.name)
gh api repos/$REPO/branches/$DEFAULT_BRANCH/protection -X PUT -f required_status_checks=null \
  -f enforce_admins=false \
  -f required_pull_request_reviews=null \
  -f restrictions=null \
  -f allow_force_pushes=false \
  -f allow_deletions=false

# Create initial tag for git-describe
FIRST_COMMIT=$(git log --reverse --format=%H | head -1)
git tag v0.0 $FIRST_COMMIT
git push origin v0.0
```

## Individual Setting Details

### 1. Tag the First Commit as v0.0

```bash
# Tag the first commit with v0.0 to enable git describe
git tag v0.0 $(git rev-list --max-parents=0 HEAD)
git push origin v0.0
```

**Purpose**: Adding a `v0.0` tag to the first commit ensures that `git describe` works properly from the start of the repository. Without any tags, `git describe` will fail with "fatal: No names found, cannot describe anything."

**Note**: This should be done after the initial commit but before extensive development. The tag marks the repository's starting point and allows version-based commands to function correctly.

### 2. Enable Secrets Detection

```bash
# Enable secret scanning
gh api repos/$REPO -X PATCH -f security_and_analysis[secret_scanning][status]=enabled

# Enable secret scanning push protection (prevents committing secrets)
gh api repos/$REPO -X PATCH -f security_and_analysis[secret_scanning_push_protection][status]=enabled
```

**Note**: Secret scanning is automatically available for public repositories. For private repositories, it requires GitHub Advanced Security to be enabled for your organization.

### 3. Prevent Force Pushing the Default Branch

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

### 4. Disable Wiki, Projects, and Discussions

```bash
# Disable wiki and projects
gh repo edit $REPO --enable-wiki=false --enable-projects=false

# Disable discussions (requires GraphQL API - REST API doesn't support this parameter)
REPO_ID=$(gh api graphql -f query="query { repository(owner: \"${REPO%/*}\", name: \"${REPO#*/}\") { id } }" --jq '.data.repository.id')
gh api graphql -f query="mutation { updateRepository(input: { repositoryId: \"$REPO_ID\", hasDiscussionsEnabled: false }) { repository { hasDiscussionsEnabled } } }"
```

### 5. Disable Everything But Merge Pull Requests

```bash
# Only allow merge commits (disable squash and rebase merge)
gh repo edit $REPO \
  --allow-squash-merge=false \
  --allow-rebase-merge=false \
  --allow-merge-commit=true
```

### 6. Enable Always Suggest Updating Pull Request Branches

```bash
# Enable the "Update branch" button on pull requests
gh api repos/$REPO -X PATCH -f allow_update_branch=true
```

### 7. Enable Automatically Delete Head Branches

```bash
# Automatically delete head branches after PR merge
gh repo edit $REPO --delete-branch-on-merge=true
```

### 8. Enable Include Git LFS Objects in Archives

**Note:** This setting is **UI-only** and cannot be configured via API (neither REST nor GraphQL).

To enable this setting:
1. Navigate to `https://github.com/$REPO/settings`
2. Scroll to the "Archives" section
3. Check "Include Git LFS objects in archives"

**References:**
- [GitHub Docs: Managing Git LFS objects in archives](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/managing-git-lfs-objects-in-archives-of-your-repository)
- No API parameter exists for this setting (verified via REST API docs and GraphQL introspection)

### 8. Create Initial Tag for git-describe

Create an initial version tag on the first commit to enable `git-describe` to work properly:

```bash
# Find the first commit
FIRST_COMMIT=$(git log --reverse --format=%H | head -1)

# Create tag v0.0 on the first commit
git tag v0.0 $FIRST_COMMIT

# Push the tag to remote
git push origin v0.0

# Verify git-describe works
git describe --tags
```

**Why this is needed:**
- `git-describe` requires at least one tag to generate version strings
- Creating `v0.0` on the first commit provides a base reference point
- Enables automatic version numbering based on commits since the initial tag
- Useful for package version management and build identification

**Example output:**
```
v0.0-37-g3a3ceb5
```
This means: 37 commits after tag v0.0, current commit hash g3a3ceb5

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
