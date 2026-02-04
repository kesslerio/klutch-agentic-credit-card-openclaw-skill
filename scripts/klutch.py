#!/usr/bin/env python3
"""
Klutch CLI - OpenClaw skill for Klutch programmable credit card API integration.

This script provides a command-line interface for managing Klutch virtual cards,
checking balances, and viewing transactions with session-based or autonomous modes.
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict

import click
import requests
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

# Configuration paths
CONFIG_DIR = Path.home() / ".config" / "klutch"
DATA_DIR = Path.home() / ".local" / "share" / "klutch"
CONFIG_FILE = CONFIG_DIR / "config.json"
TOKEN_FILE = CONFIG_DIR / "token.json"
AUDIT_LOG = DATA_DIR / "audit.log"

# Default configuration
DEFAULT_CONFIG = {
    "autonomous": {
        "enabled": False,
        "max_per_card": 200,
        "max_daily_total": 500,
        "allowed_merchants": [],
        "blocked_categories": ["gambling", "cryptocurrency", "adult"],
        "require_approval_above": 100
    },
    "notifications": {
        "every_transaction": False,
        "threshold_amount": 25
    },
    "api": {
        "base_url": "https://api.klutchcard.com/graphql",
        "timeout": 30,
        "max_retries": 3
    }
}

# Hardcoded blocked categories (cannot be overridden)
HARDCODED_BLOCKED_CATEGORIES = {"gambling", "cryptocurrency", "adult"}


@dataclass
class KlutchConfig:
    """Configuration for Klutch skill."""
    autonomous_enabled: bool
    max_per_card: float
    max_daily_total: float
    allowed_merchants: List[str]
    blocked_categories: List[str]
    require_approval_above: float
    api_base_url: str
    api_timeout: int
    api_max_retries: int


class KlutchAPI:
    """Client for Klutch GraphQL API."""
    
    def __init__(self, config: KlutchConfig):
        self.config = config
        self.token = None
        self.token_expiry = None
        self._load_token()
        self._setup_client()
    
    def _load_token(self):
        """Load cached token or authenticate."""
        # Check environment variable first
        env_token = os.environ.get("KLUTCH_API_TOKEN")
        if env_token:
            self.token = env_token
            self.token_expiry = datetime.now() + timedelta(hours=24)
            return
        
        # Check cached token
        if TOKEN_FILE.exists():
            try:
                with open(TOKEN_FILE) as f:
                    data = json.load(f)
                self.token = data.get("token")
                self.token_expiry = datetime.fromisoformat(data.get("expiry", "2000-01-01"))
                
                # Refresh if expired or about to expire
                if datetime.now() >= self.token_expiry - timedelta(minutes=5):
                    self._authenticate()
            except (json.JSONDecodeError, KeyError, ValueError):
                self._authenticate()
        else:
            self._authenticate()
    
    def _authenticate(self):
        """Authenticate with email/password to get JWT token."""
        email = os.environ.get("KLUTCH_EMAIL")
        password = os.environ.get("KLUTCH_PASSWORD")
        
        if not email or not password:
            raise click.UsageError(
                "Authentication required. Set KLUTCH_EMAIL and KLUTCH_PASSWORD "
                "environment variables, or KLUTCH_API_TOKEN for token-based auth."
            )
        
        # GraphQL mutation for login
        mutation = gql("""
            mutation Login($email: String!, $password: String!) {
                login(email: $email, password: $password) {
                    token
                    expiresAt
                }
            }
        """)
        
        try:
            transport = RequestsHTTPTransport(
                url=self.config.api_base_url,
                headers={"Content-Type": "application/json"}
            )
            client = Client(transport=transport, fetch_schema_from_transport=False)
            result = client.execute(mutation, {"email": email, "password": password})
            
            self.token = result["login"]["token"]
            expiry_str = result["login"].get("expiresAt")
            if expiry_str:
                self.token_expiry = datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
            else:
                self.token_expiry = datetime.now() + timedelta(hours=24)
            
            # Cache token
            self._save_token()
            
        except Exception as e:
            raise click.ClickException(f"Authentication failed: {e}")
    
    def _save_token(self):
        """Save token to cache file."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(json.dumps({
            "token": self.token,
            "expiry": self.token_expiry.isoformat()
        }))
        # Restrict permissions
        os.chmod(TOKEN_FILE, 0o600)
    
    def _setup_client(self):
        """Set up GraphQL client with authentication."""
        transport = RequestsHTTPTransport(
            url=self.config.api_base_url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}"
            },
            timeout=self.config.api_timeout
        )
        self.client = Client(transport=transport, fetch_schema_from_transport=False)
    
    def execute(self, query, variables=None):
        """Execute GraphQL query with retry logic."""
        for attempt in range(self.config.api_max_retries):
            try:
                return self.client.execute(query, variables)
            except Exception as e:
                if "Unauthorized" in str(e) or "token" in str(e).lower():
                    # Token expired, re-authenticate
                    self._authenticate()
                    self._setup_client()
                elif attempt < self.config.api_max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise click.ClickException(f"API error: {e}")


def load_config() -> KlutchConfig:
    """Load configuration from file or defaults."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            data = json.load(f)
    else:
        data = DEFAULT_CONFIG
    
    # Merge blocked categories (hardcoded ones cannot be removed)
    blocked = set(data.get("autonomous", {}).get("blocked_categories", []))
    blocked.update(HARDCODED_BLOCKED_CATEGORIES)
    
    return KlutchConfig(
        autonomous_enabled=data.get("autonomous", {}).get("enabled", False),
        max_per_card=data.get("autonomous", {}).get("max_per_card", 200),
        max_daily_total=data.get("autonomous", {}).get("max_daily_total", 500),
        allowed_merchants=data.get("autonomous", {}).get("allowed_merchants", []),
        blocked_categories=list(blocked),
        require_approval_above=data.get("autonomous", {}).get("require_approval_above", 100),
        api_base_url=data.get("api", {}).get("base_url", "https://api.klutchcard.com/graphql"),
        api_timeout=data.get("api", {}).get("timeout", 30),
        api_max_retries=data.get("api", {}).get("max_retries", 3)
    )


def save_config(config: KlutchConfig):
    """Save configuration to file."""
    data = {
        "autonomous": {
            "enabled": config.autonomous_enabled,
            "max_per_card": config.max_per_card,
            "max_daily_total": config.max_daily_total,
            "allowed_merchants": config.allowed_merchants,
            "blocked_categories": [c for c in config.blocked_categories if c not in HARDCODED_BLOCKED_CATEGORIES],
            "require_approval_above": config.require_approval_above
        },
        "api": {
            "base_url": config.api_base_url,
            "timeout": config.api_timeout,
            "max_retries": config.api_max_retries
        }
    }
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2))


def log_audit(action: str, details: Dict[str, Any]):
    """Write to audit log."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().isoformat()
    details_str = ", ".join(f"{k}={v}" for k, v in details.items())
    log_entry = f"[{timestamp}] {action}: {details_str}\n"
    with open(AUDIT_LOG, "a") as f:
        f.write(log_entry)


def check_safety_limits(config: KlutchConfig, amount: float, category: Optional[str] = None, 
                        yolo: bool = False) -> bool:
    """Check if operation is within safety limits."""
    # Check blocked categories
    if category and category.lower() in [c.lower() for c in config.blocked_categories]:
        raise click.ClickException(f"Category '{category}' is blocked by safety policy")
    
    # Check per-card limit
    if amount > config.max_per_card:
        raise click.ClickException(
            f"Amount ${amount:.2f} exceeds max per-card limit of ${config.max_per_card:.2f}"
        )
    
    # Check approval threshold
    if not yolo and not config.autonomous_enabled and amount > config.require_approval_above:
        return False  # Requires explicit approval
    
    return True


# CLI Commands
@click.group()
@click.option("--yolo", is_flag=True, help="Enable autonomous mode (skip approval prompts)")
@click.pass_context
def cli(ctx, yolo):
    """Klutch CLI - Manage programmable credit cards."""
    ctx.ensure_object(dict)
    ctx.obj["yolo"] = yolo
    ctx.obj["config"] = load_config()


@cli.command()
@click.pass_context
def balance(ctx):
    """Show current account balance."""
    config = ctx.obj["config"]
    api = KlutchAPI(config)
    
    query = gql("""
        query GetBalance {
            account {
                currentBalance
                availableCredit
                totalCredit
            }
        }
    """)
    
    try:
        result = api.execute(query)
        account = result.get("account", {})
        
        click.echo(f"Current Balance: ${account.get('currentBalance', 0):.2f}")
        click.echo(f"Available Credit: ${account.get('availableCredit', 0):.2f}")
        click.echo(f"Total Credit: ${account.get('totalCredit', 0):.2f}")
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(f"Failed to fetch balance: {e}")


@cli.command()
@click.option("--limit", "-n", default=10, help="Number of transactions to show")
@click.pass_context
def transactions(ctx, limit):
    """List recent transactions."""
    config = ctx.obj["config"]
    api = KlutchAPI(config)
    
    query = gql("""
        query GetTransactions($limit: Int!) {
            transactions(limit: $limit) {
                id
                date
                merchant
                amount
                status
                cardId
            }
        }
    """)
    
    try:
        result = api.execute(query, {"limit": limit})
        transactions = result.get("transactions", [])
        
        if not transactions:
            click.echo("No transactions found.")
            return
        
        # Header
        click.echo(f"{'ID':<15} {'Date':<12} {'Merchant':<20} {'Amount':>10} {'Status':<10}")
        click.echo("-" * 75)
        
        for txn in transactions:
            date = txn.get("date", "N/A")[:10]  # Just the date part
            click.echo(
                f"{txn.get('id', 'N/A')[:14]:<15} "
                f"{date:<12} "
                f"{txn.get('merchant', 'N/A')[:19]:<20} "
                f"${txn.get('amount', 0):>9.2f} "
                f"{txn.get('status', 'N/A'):<10}"
            )
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(f"Failed to fetch transactions: {e}")


@cli.group()
def card():
    """Manage virtual cards."""
    pass


@card.command(name="create")
@click.option("--name", "-n", required=True, help="Card name")
@click.option("--limit", "-l", "spend_limit", type=float, required=True, help="Spending limit")
@click.option("--merchant", "-m", help="Lock to specific merchant")
@click.option("--category", "-c", help="Category restriction")
@click.pass_context
def card_create(ctx, name, spend_limit, merchant, category):
    """Create a new virtual card."""
    config = ctx.obj["config"]
    yolo = ctx.obj["yolo"]
    
    # Safety checks
    requires_approval = not check_safety_limits(config, spend_limit, category, yolo)
    
    if requires_approval:
        if not click.confirm(f"Create card with limit ${spend_limit:.2f}?"):
            click.echo("Cancelled.")
            return
    
    # Check blocked categories
    if category and category.lower() in HARDCODED_BLOCKED_CATEGORIES:
        raise click.ClickException(f"Category '{category}' is blocked by safety policy")
    
    api = KlutchAPI(config)
    
    mutation = gql("""
        mutation CreateVirtualCard($input: VirtualCardInput!) {
            createVirtualCard(input: $input) {
                id
                name
                limit
                status
            }
        }
    """)
    
    variables = {
        "input": {
            "name": name,
            "limit": spend_limit,
            **({"merchant": merchant} if merchant else {}),
            **({"category": category} if category else {})
        }
    }
    
    try:
        result = api.execute(mutation, variables)
        card_data = result.get("createVirtualCard", {})
        
        # Log to audit
        log_audit("CARD_CREATED", {
            "card_id": card_data.get("id"),
            "name": name,
            "limit": spend_limit,
            "created_by": "autonomous" if (yolo or config.autonomous_enabled) else "session"
        })
        
        click.echo(f"✓ Created virtual card: {card_data.get('name')}")
        click.echo(f"  ID: {card_data.get('id')}")
        click.echo(f"  Limit: ${card_data.get('limit', 0):.2f}")
        click.echo(f"  Status: {card_data.get('status')}")
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(f"Failed to create card: {e}")


@card.command(name="list")
@click.pass_context
def card_list(ctx):
    """List all virtual cards."""
    config = ctx.obj["config"]
    api = KlutchAPI(config)
    
    query = gql("""
        query GetVirtualCards {
            virtualCards {
                id
                name
                limit
                spent
                status
            }
        }
    """)
    
    try:
        result = api.execute(query)
        cards = result.get("virtualCards", [])
        
        if not cards:
            click.echo("No virtual cards found.")
            return
        
        # Header
        click.echo(f"{'ID':<15} {'Name':<20} {'Limit':>10} {'Spent':>10} {'Status':<10}")
        click.echo("-" * 70)
        
        for card in cards:
            click.echo(
                f"{card.get('id', 'N/A')[:14]:<15} "
                f"{card.get('name', 'N/A')[:19]:<20} "
                f"${card.get('limit', 0):>9.2f} "
                f"${card.get('spent', 0):>9.2f} "
                f"{card.get('status', 'N/A'):<10}"
            )
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(f"Failed to fetch cards: {e}")


@card.command(name="pause")
@click.argument("card_id")
@click.pass_context
def card_pause(ctx, card_id):
    """Pause a virtual card."""
    config = ctx.obj["config"]
    yolo = ctx.obj["yolo"]
    
    if not yolo and not config.autonomous_enabled:
        if not click.confirm(f"Pause card {card_id}?"):
            click.echo("Cancelled.")
            return
    
    api = KlutchAPI(config)
    
    mutation = gql("""
        mutation PauseVirtualCard($id: ID!) {
            pauseVirtualCard(id: $id) {
                id
                status
            }
        }
    """)
    
    try:
        result = api.execute(mutation, {"id": card_id})
        card_data = result.get("pauseVirtualCard", {})
        click.echo(f"✓ Paused card: {card_data.get('id')} (Status: {card_data.get('status')})")
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(f"Failed to pause card: {e}")


@card.command(name="terminate")
@click.argument("card_id")
@click.option("--force", is_flag=True, required=True, help="Required flag to confirm termination")
@click.pass_context
def card_terminate(ctx, card_id, force):
    """Terminate a virtual card (permanent - requires --force)."""
    if not force:
        raise click.UsageError("Termination requires --force flag for safety")
    
    config = ctx.obj["config"]
    yolo = ctx.obj["yolo"]
    
    # Extra confirmation unless in yolo mode
    if not yolo and not config.autonomous_enabled:
        if not click.confirm(f"⚠️  Permanently terminate card {card_id}? This cannot be undone."):
            click.echo("Cancelled.")
            return
    
    api = KlutchAPI(config)
    
    mutation = gql("""
        mutation TerminateVirtualCard($id: ID!) {
            terminateVirtualCard(id: $id) {
                id
                status
            }
        }
    """)
    
    try:
        result = api.execute(mutation, {"id": card_id})
        card_data = result.get("terminateVirtualCard", {})
        
        # Log to audit
        log_audit("CARD_TERMINATED", {
            "card_id": card_id,
            "reason": "user_request"
        })
        
        click.echo(f"✓ Terminated card: {card_data.get('id')} (Status: {card_data.get('status')})")
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(f"Failed to terminate card: {e}")


@cli.group()
def config_cmd():
    """Manage configuration."""
    pass


@config_cmd.command(name="get")
@click.argument("key", required=False)
@click.pass_context
def config_get(ctx, key):
    """Get configuration value(s)."""
    config = load_config()
    
    if key:
        # Handle nested keys like "autonomous.max_per_card"
        parts = key.split(".")
        value = asdict(config)
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                raise click.ClickException(f"Unknown config key: {key}")
        click.echo(f"{key} = {value}")
    else:
        # Show all config
        click.echo(json.dumps(asdict(config), indent=2))


@config_cmd.command(name="set")
@click.argument("key")
@click.argument("value")
@click.pass_context
def config_set(ctx, key, value):
    """Set configuration value."""
    config = load_config()
    
    # Convert value types
    if value.lower() in ("true", "false"):
        value = value.lower() == "true"
    elif "." in value:
        try:
            value = float(value)
        except ValueError:
            pass
    else:
        try:
            value = int(value)
        except ValueError:
            pass
    
    # Handle nested keys
    parts = key.split(".")
    if len(parts) == 1:
        setattr(config, key, value)
    elif parts[0] == "autonomous":
        if parts[1] == "enabled":
            config.autonomous_enabled = value
        elif parts[1] == "max_per_card":
            config.max_per_card = value
        elif parts[1] == "max_daily_total":
            config.max_daily_total = value
        elif parts[1] == "require_approval_above":
            config.require_approval_above = value
        elif parts[1] == "allowed_merchants":
            config.allowed_merchants = value.split(",") if isinstance(value, str) else value
        elif parts[1] == "blocked_categories":
            # Merge with hardcoded
            user_cats = value.split(",") if isinstance(value, str) else value
            config.blocked_categories = list(set(user_cats) | HARDCODED_BLOCKED_CATEGORIES)
        else:
            raise click.ClickException(f"Unknown config key: {key}")
    elif parts[0] == "api":
        if parts[1] == "base_url":
            config.api_base_url = value
        elif parts[1] == "timeout":
            config.api_timeout = value
        elif parts[1] == "max_retries":
            config.api_max_retries = value
        else:
            raise click.ClickException(f"Unknown config key: {key}")
    else:
        raise click.ClickException(f"Unknown config key: {key}")
    
    save_config(config)
    click.echo(f"✓ Set {key} = {value}")


if __name__ == "__main__":
    cli()
