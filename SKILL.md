---
name: klutch
description: OpenClaw skill for Klutch programmable credit card API integration. Manage virtual cards, check balances, view transactions with session-based or autonomous modes.
metadata:
  openclaw:
    emoji: 💳
    requires:
      env:
        - KLUTCH_EMAIL
        - KLUTCH_PASSWORD
      optional_env:
        - KLUTCH_API_TOKEN
    install:
      - id: pip
        kind: pip
        requirements: requirements.txt
---

# Klutch Skill

OpenClaw skill for Klutch programmable credit card API integration.

## Overview

This skill provides a command-line interface and automation capabilities for managing Klutch programmable credit cards. It supports both session-based (interactive) and autonomous modes for card management, balance checking, and transaction monitoring.

## Prerequisites

1. **Klutch Account**: You must have an active Klutch account
2. **API Access**: Register for API credentials through the Klutch developer portal at https://developer.klutchcard.com
3. **Python 3.10+**: Required for running the scripts

## Configuration

### Environment Variables

Set one of the following authentication methods:

**Option 1: Email/Password (recommended for initial setup)**
```bash
export KLUTCH_EMAIL="your@email.com"
export KLUTCH_PASSWORD="your_password"
```

**Option 2: API Token (for automated/scripted usage)**
```bash
export KLUTCH_API_TOKEN="your_jwt_token"
```

### Configuration File

The skill stores configuration and state in `~/.config/klutch/`:

```bash
~/.config/klutch/
├── config.json      # User preferences and autonomous settings
├── token.json       # Cached JWT token (auto-managed)
└── audit.log        # Audit trail of card operations
```

### Autonomous Mode Configuration

Edit `~/.config/klutch/config.json` to customize autonomous behavior:

```json
{
  "autonomous": {
    "enabled": false,
    "max_per_card": 200,
    "max_daily_total": 500,
    "allowed_merchants": [],
    "blocked_categories": ["gambling", "cryptocurrency", "adult"],
    "require_approval_above": 100
  },
  "notifications": {
    "every_transaction": false,
    "threshold_amount": 25
  }
}
```

## Commands Reference

### Balance

```bash
# Check current account balance
python scripts/klutch.py balance

# Example output:
# Current Balance: $1,234.56
# Available Credit: $5,000.00
```

### Transactions

```bash
# List recent transactions (default: 10)
python scripts/klutch.py transactions

# List more transactions
python scripts/klutch.py transactions --limit 25

# Example output:
# ID          Date       Merchant          Amount    Status
# ----------  ---------  ----------------  --------  --------
# txn_abc123  2024-01-15 Starbucks         $5.67     settled
# txn_def456  2024-01-14 Amazon            $45.23    pending
```

### Card Management

#### Create Virtual Card

```bash
# Basic virtual card
python scripts/klutch.py card create --name "Online Shopping" --limit 100

# Merchant-locked card
python scripts/klutch.py card create --name "Netflix" --limit 15.99 --merchant "Netflix"

# Category-restricted card
python scripts/klutch.py card create --name "Groceries" --limit 200 --category "grocery"

# Autonomous mode (bypass approval prompts)
python scripts/klutch.py card create --name "Subscription" --limit 10 --yolo
```

#### List Cards

```bash
# Show all virtual cards
python scripts/klutch.py card list

# Example output:
# ID           Name              Limit     Spent    Status
# -----------  ----------------  --------  -------  --------
# card_abc123  Online Shopping   $100.00   $23.45   active
# card_def456  Netflix           $15.99    $15.99   active
```

#### Pause Card

```bash
# Temporarily pause a card
python scripts/klutch.py card pause card_abc123

# Requires confirmation in session mode
# Use --yolo for autonomous operation
```

#### Terminate Card

```bash
# Permanently terminate a card (requires --force)
python scripts/klutch.py card terminate card_abc123 --force

# Autonomous mode
python scripts/klutch.py card terminate card_abc123 --force --yolo
```

### Configuration Management

```bash
# Get configuration value
python scripts/klutch.py config get autonomous.max_per_card

# Set configuration value
python scripts/klutch.py config set autonomous.max_per_card 150

# View all configuration
python scripts/klutch.py config get
```

## Safety Guardrails

### Hardcoded Protections

The following restrictions are **non-configurable** and enforced regardless of user settings:

| Category | Behavior |
|----------|----------|
| Blocked Categories | `gambling`, `cryptocurrency`, `adult` - cannot be overridden |
| Card Termination | Requires explicit `--force` flag to prevent accidental deletion |
| Audit Logging | All card creation operations are logged to `~/.local/share/klutch/audit.log` |

### Configurable Limits

| Setting | Default | Description |
|---------|---------|-------------|
| `max_per_card` | $200 | Maximum spending limit for any single card |
| `max_daily_total` | $500 | Maximum total spending across all cards per day |
| `require_approval_above` | $100 | Transactions above this amount require explicit approval |

### Session vs Autonomous Modes

**Session Mode (default):**
- Prompts for approval on card creation > $100
- Prompts for confirmation on card termination
- Interactive confirmation for all significant operations

**Autonomous Mode (`--yolo`):**
- Bypasses approval prompts
- Respects all safety limits
- Suitable for trusted automation workflows
- Enable with `--yolo` flag or `autonomous.enabled: true` in config

### Audit Logging

All card creation operations are logged to `~/.local/share/klutch/audit.log`:

```
[2024-01-15T09:23:45] CARD_CREATED: card_id=card_abc123, name="Online Shopping", limit=100.00, created_by=session
[2024-01-15T10:15:22] CARD_TERMINATED: card_id=card_def456, reason=user_request
```

## Error Handling

The skill handles common error scenarios:

- **Authentication failures**: Prompts to re-authenticate
- **Rate limiting**: Automatic retry with exponential backoff
- **Network errors**: Clear error messages with retry suggestions
- **Invalid operations**: Pre-validation before API calls

## Integration with OpenClaw

### Using from OpenClaw Sessions

```bash
# OpenClaw can invoke the skill directly
klutch balance
klutch transactions --limit 5
klutch card create --name "Test" --limit 50
```

### Cron Automation

Set up automated balance checks:

```json
{
  "cron": [{
    "schedule": "0 9 * * *",
    "command": "klutch balance",
    "channel": "telegram"
  }]
}
```

## Troubleshooting

### Authentication Issues

If you receive authentication errors:
1. Verify your credentials with `python scripts/klutch.py config get`
2. Delete `~/.config/klutch/token.json` to force re-authentication
3. Check that your API token hasn't expired

### Rate Limiting

The Klutch API has rate limits. The skill implements:
- Automatic retry with backoff
- Request caching for non-mutating operations
- Clear messaging when limits are hit

### Permission Denied

Ensure the scripts are executable:
```bash
chmod +x scripts/klutch.py
```

## Security Notes

- Never commit credentials to version control
- The skill stores tokens in `~/.config/klutch/token.json` with 600 permissions
- API tokens are refreshed automatically before expiration
- Consider using 1Password CLI for credential injection in CI/CD environments
