# OpenClaw Klutch Skill

💳 OpenClaw skill for Klutch programmable credit card API integration.

## Features

- **Balance Management**: Check current balance and available credit
- **Transaction History**: View and filter transaction history
- **Virtual Cards**: Create, pause, and terminate programmable virtual cards
- **Safety Guardrails**: Built-in limits and blocked categories for safe automation
- **Session & Autonomous Modes**: Interactive or automated operation
- **Audit Logging**: Complete trail of all card operations

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/martin@kessler.io/openclaw-skill-klutch.git
cd openclaw-skill-klutch

# Install dependencies
pip install -r requirements.txt

# Or using uv
uv pip install -r requirements.txt
```

### Via OpenClaw

Add to your OpenClaw configuration:

```json
{
  "skills": [{
    "name": "klutch",
    "source": "https://github.com/martin@kessler.io/openclaw-skill-klutch"
  }]
}
```

## Quick Start

1. **Get API Credentials**:
   - Sign up at https://klutchcard.com
   - Access the developer portal at https://developer.klutchcard.com
   - Generate API credentials

2. **Configure Authentication**:
   ```bash
   export KLUTCH_EMAIL="your@email.com"
   export KLUTCH_PASSWORD="your_password"
   ```

3. **Test the Connection**:
   ```bash
   python scripts/klutch.py balance
   ```

## Usage Examples

### Check Balance
```bash
python scripts/klutch.py balance
```

### Create a Virtual Card
```bash
# Basic card
python scripts/klutch.py card create --name "Online Shopping" --limit 100

# Merchant-locked card for subscriptions
python scripts/klutch.py card create --name "Netflix" --limit 15.99 --merchant "Netflix"
```

### List Transactions
```bash
python scripts/klutch.py transactions --limit 20
```

### Manage Cards
```bash
# List all cards
python scripts/klutch.py card list

# Pause a card
python scripts/klutch.py card pause card_abc123

# Terminate a card (requires --force)
python scripts/klutch.py card terminate card_abc123 --force
```

## Configuration

The skill stores configuration in `~/.config/klutch/`:

```bash
~/.config/klutch/
├── config.json      # User preferences
├── token.json       # Cached authentication token
└── audit.log        # Operation audit trail
```

### Autonomous Mode

Enable autonomous operation (bypasses approval prompts):

```bash
# Via flag
python scripts/klutch.py card create --name "Test" --limit 50 --yolo

# Via config
python scripts/klutch.py config set autonomous.enabled true
```

### Safety Limits

Configure spending limits and restrictions:

```bash
python scripts/klutch.py config set autonomous.max_per_card 250
python scripts/klutch.py config set autonomous.max_daily_total 750
python scripts/klutch.py config set autonomous.require_approval_above 50
```

See `config/klutch.example.json` for full configuration options.

## Safety Guardrails

This skill implements several safety measures:

| Feature | Default | Description |
|---------|---------|-------------|
| Blocked Categories | gambling, cryptocurrency, adult | Hardcoded, cannot be overridden |
| Max Per-Card Limit | $200 | Maximum spending limit per card |
| Max Daily Total | $500 | Maximum total daily spending |
| Approval Threshold | $100 | Amount above which approval is required |
| Termination Protection | Required | `--force` flag required to terminate cards |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `KLUTCH_EMAIL` | Yes* | Your Klutch account email |
| `KLUTCH_PASSWORD` | Yes* | Your Klutch account password |
| `KLUTCH_API_TOKEN` | No | Pre-authenticated JWT token |

*Either email/password or API token required.

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/
```

### Project Structure

```
openclaw-skill-klutch/
├── SKILL.md                 # Skill definition for OpenClaw
├── README.md               # This file
├── requirements.txt        # Python dependencies
├── config/
│   └── klutch.example.json # Example configuration
└── scripts/
    └── klutch.py          # Main CLI script
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feat/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see LICENSE file for details.

## Disclaimer

This is an unofficial integration. Use at your own risk. Always verify card operations in the official Klutch app.
