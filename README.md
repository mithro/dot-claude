# dot-claude

Personal [Claude Code](https://claude.com/claude-code) configuration.

## Overview

This repository contains my personal Claude Code configuration files, including global instructions, custom agents, and hook configurations.

## Contents

- **CLAUDE.md** - Global instructions that Claude Code follows across all projects
- **agents/** - Custom specialized agents for various development tasks
- **settings.json** - Hook configurations and personal preferences
- **.gitignore** - Files to exclude from version control

## Setup

To use this configuration:

```bash
# Clone this repository
git clone https://github.com/mithro/dot-claude.git ~/github/mithro/dot-claude

# Create symlink (backup existing config first if needed)
mv ~/.claude ~/.claude.backup
ln -s ~/github/mithro/dot-claude ~/.claude
```

## Notification System

This configuration uses [claude-notify-gnome](https://github.com/mithro/claude-notify-gnome) for desktop notifications. The hooks in `settings.json` point to the notification tool at its installed location.

To set up the notification system:

```bash
# Clone and set up the notification tool
git clone https://github.com/mithro/claude-notify-gnome.git ~/github/mithro/claude-notify-gnome
cd ~/github/mithro/claude-notify-gnome
# Follow setup instructions in that repository's README
```

## Configuration

### CLAUDE.md

Contains global instructions that override default Claude Code behavior:
- Prefer Python over bash for complex scripts (to avoid escaping issues)
- Use temporary directories in project directory instead of /tmp
- Always verify assumptions and double-check work
- Provide detailed proof for claims

### Custom Agents

The `agents/` directory contains specialized agents for various tasks. These agents are automatically available in Claude Code for handling specific types of work.

### Hooks

The `settings.json` file configures hooks that trigger at various points:
- **Notification** - When Claude sends a notification
- **UserPromptSubmit** - When user submits a prompt
- **PreToolUse** - Before Claude uses a tool
- **PostToolUse** - After Claude uses a tool
- **Stop** - When Claude stops generating

All hooks currently point to the [claude-notify-gnome](https://github.com/mithro/claude-notify-gnome) notification tool.

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for the full license text.

## Author

Tim 'mithro' Ansell
