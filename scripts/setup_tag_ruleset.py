#!/usr/bin/env python3
"""
Setup GitHub tag ruleset to enforce version tag formats.

This script creates a GitHub repository ruleset that restricts tag creation
to only allow tags matching configurable version patterns.

Supported formats:
  - vXX.ZZZ: Two-part versioning (major.patch) [default]
  - vXX.YY.ZZZ: Three-part semantic versioning (major.minor.patch)

Usage:
    uv run python ~/.claude/scripts/setup_tag_ruleset.py --owner OWNER --repo REPO
    uv run python ~/.claude/scripts/setup_tag_ruleset.py --owner OWNER --repo REPO --format vXX.YY.ZZZ

Requirements:
    - GitHub CLI (gh) must be installed and authenticated
    - User must have admin access to the repository
"""

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass


@dataclass
class VersionFormat:
    """Configuration for a version format."""

    name: str
    description: str
    segment_max_digits: list[int]  # Max digits for each segment
    examples_valid: list[str]
    examples_invalid: list[str]


VERSION_FORMATS = {
    "vXX.ZZZ": VersionFormat(
        name="vXX.ZZZ",
        description="Two-part versioning (major.patch)",
        segment_max_digits=[2, 3],  # XX.ZZZ
        examples_valid=["v0.0", "v1.2", "v12.345", "v99.999"],
        examples_invalid=["v1.2.3", "v100.1", "v1.1000"],
    ),
    "vXX.YY.ZZZ": VersionFormat(
        name="vXX.YY.ZZZ",
        description="Three-part semantic versioning (major.minor.patch)",
        segment_max_digits=[2, 2, 3],  # XX.YY.ZZZ
        examples_valid=["v0.0.1", "v1.2.3", "v12.34.567", "v99.99.999"],
        examples_invalid=["v1.2", "v1.2.3.4", "v100.1.1", "v1.2.1000"],
    ),
}


def generate_digit_patterns(max_digits: int) -> list[str]:
    """
    Generate fnmatch patterns for 1 to max_digits digits.

    Example: max_digits=3 returns ["[0-9]", "[0-9][0-9]", "[0-9][0-9][0-9]"]
    """
    return ["[0-9]" * i for i in range(1, max_digits + 1)]


def generate_version_patterns(version_format: VersionFormat) -> list[str]:
    """
    Generate all fnmatch patterns for a given version format.

    For vXX.YY.ZZZ (max digits [2, 2, 3]): 2 * 2 * 3 = 12 patterns
    For vXX.ZZZ (max digits [2, 3]): 2 * 3 = 6 patterns
    """
    segment_patterns = [
        generate_digit_patterns(max_digits)
        for max_digits in version_format.segment_max_digits
    ]

    # Generate all combinations using itertools-like approach
    def product(*iterables):
        """Cartesian product of input iterables."""
        result = [[]]
        for pool in iterables:
            result = [x + [y] for x in result for y in pool]
        return result

    combinations = product(*segment_patterns)

    patterns = []
    for combo in combinations:
        version_part = ".".join(combo)
        pattern = f"refs/tags/v{version_part}"
        patterns.append(pattern)

    return patterns


def create_ruleset_payload(
    name: str, version_format: VersionFormat
) -> dict:
    """Create the JSON payload for the ruleset API."""

    exclude_patterns = generate_version_patterns(version_format)

    payload = {
        "name": name,
        "target": "tag",
        "enforcement": "active",
        "bypass_actors": [],  # No one can bypass
        "conditions": {
            "ref_name": {
                "include": ["refs/tags/*"],  # Target all tags
                "exclude": exclude_patterns,  # Except valid version patterns
            }
        },
        "rules": [
            {
                "type": "creation"  # Restrict creation of non-matching tags
            }
        ],
    }

    return payload


def check_existing_rulesets(owner: str, repo: str) -> list[dict]:
    """Check for existing rulesets in the repository."""
    result = subprocess.run(
        [
            "gh", "api",
            "-H", "Accept: application/vnd.github+json",
            "-H", "X-GitHub-Api-Version: 2022-11-28",
            f"/repos/{owner}/{repo}/rulesets",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"Error checking existing rulesets: {result.stderr}", file=sys.stderr)
        return []

    return json.loads(result.stdout)


def delete_ruleset(owner: str, repo: str, ruleset_id: int) -> bool:
    """Delete an existing ruleset."""
    result = subprocess.run(
        [
            "gh", "api",
            "--method", "DELETE",
            "-H", "Accept: application/vnd.github+json",
            "-H", "X-GitHub-Api-Version: 2022-11-28",
            f"/repos/{owner}/{repo}/rulesets/{ruleset_id}",
        ],
        capture_output=True,
        text=True,
    )

    return result.returncode == 0


def create_ruleset(owner: str, repo: str, payload: dict) -> tuple[bool, str]:
    """Create the ruleset via GitHub API."""

    payload_json = json.dumps(payload)

    result = subprocess.run(
        [
            "gh", "api",
            "--method", "POST",
            "-H", "Accept: application/vnd.github+json",
            "-H", "X-GitHub-Api-Version: 2022-11-28",
            f"/repos/{owner}/{repo}/rulesets",
            "--input", "-",
        ],
        input=payload_json,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        return True, result.stdout
    else:
        return False, result.stderr


def main():
    parser = argparse.ArgumentParser(
        description="Setup GitHub tag ruleset for version tag enforcement",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Supported formats:
  vXX.ZZZ     Two-part versioning (major.patch) [default]
              XX: 1-2 digits, ZZZ: 1-3 digits
              Examples: v1.2, v12.345, v99.999

  vXX.YY.ZZZ  Three-part semantic versioning (major.minor.patch)
              XX: 1-2 digits, YY: 1-2 digits, ZZZ: 1-3 digits
              Examples: v1.2.3, v12.34.567, v99.99.999
""",
    )
    parser.add_argument(
        "--owner",
        required=True,
        help="GitHub repository owner (user or organization)",
    )
    parser.add_argument(
        "--repo",
        required=True,
        help="GitHub repository name",
    )
    parser.add_argument(
        "--format",
        choices=list(VERSION_FORMATS.keys()),
        default="vXX.ZZZ",
        dest="version_format",
        help="Version format to enforce (default: vXX.ZZZ)",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Name for the ruleset (default: 'Enforce <format> version tags')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the payload without creating the ruleset",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing ruleset with the same name",
    )

    args = parser.parse_args()

    # Get the version format configuration
    version_format = VERSION_FORMATS[args.version_format]

    # Set default name if not provided
    ruleset_name = args.name or f"Enforce {version_format.name} version tags"

    # Generate the payload
    payload = create_ruleset_payload(ruleset_name, version_format)

    if args.dry_run:
        print(f"Format: {version_format.name}")
        print(f"Description: {version_format.description}")
        print()
        print("Dry run - would create ruleset with payload:")
        print(json.dumps(payload, indent=2))
        print("\nExclude patterns (valid version tags that will be ALLOWED):")
        for pattern in payload["conditions"]["ref_name"]["exclude"]:
            # Strip refs/tags/ prefix for readability
            print(f"  {pattern.replace('refs/tags/', '')}")
        print(f"\nValid tag examples: {', '.join(version_format.examples_valid)}")
        print(f"Blocked tag examples: {', '.join(version_format.examples_invalid)}")
        return

    # Check for existing rulesets
    existing = check_existing_rulesets(args.owner, args.repo)
    for ruleset in existing:
        if ruleset.get("name") == ruleset_name:
            if args.replace:
                print(f"Deleting existing ruleset '{ruleset_name}' (id: {ruleset['id']})...")
                if delete_ruleset(args.owner, args.repo, ruleset["id"]):
                    print("  Deleted successfully")
                else:
                    print("  Failed to delete", file=sys.stderr)
                    sys.exit(1)
            else:
                print(
                    f"Error: Ruleset '{ruleset_name}' already exists. "
                    "Use --replace to update it.",
                    file=sys.stderr,
                )
                sys.exit(1)

    # Create the ruleset
    print(f"Creating tag ruleset for {args.owner}/{args.repo}...")
    print(f"Format: {version_format.name} ({version_format.description})")
    success, output = create_ruleset(args.owner, args.repo, payload)

    if success:
        response = json.loads(output)
        print(f"\nSuccessfully created ruleset '{ruleset_name}' (id: {response.get('id')})")
        print("\nRuleset configuration:")
        print("  - Targets: All tags (refs/tags/*)")
        print(f"  - Excludes: {len(payload['conditions']['ref_name']['exclude'])} valid version patterns")
        print("  - Rule: Restrict creation (blocks non-matching tags)")
        print(f"\nValid tag examples: {', '.join(version_format.examples_valid)}")
        print(f"Blocked tag examples: {', '.join(version_format.examples_invalid)}")
    else:
        print(f"Failed to create ruleset: {output}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
