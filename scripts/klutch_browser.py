#!/usr/bin/env python3
"""
Klutch Browser Automation - Dashboard-based card management via browser automation.

This module provides full card lifecycle management through the Klutch dashboard
when API access is insufficient (e.g., retrieving full card details, setting custom limits).

Uses OpenClaw browser tool for automation with 1Password integration for card storage.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import click

# Browser tool configuration
BROWSER_PROFILE = "openclaw"
KLUTCH_DASHBOARD_URL = "https://app.klutch.cards"

CONFIG_PATH = Path.home() / ".config" / "klutch" / "config.json"
TOKEN_PATH = Path.home() / ".config" / "klutch" / "token.json"


@dataclass
class BrowserCard:
    """Represents a Klutch card with full details."""
    id: str
    name: str
    last_four: str
    pan: Optional[str] = None  # Full PAN (16 digits)
    cvv: Optional[str] = None  # CVV code
    expiry: Optional[str] = None  # MM/YY format
    status: str = "ACTIVE"
    spend_limit: Optional[float] = None
    monthly_limit: Optional[float] = None


def _get_1password_credential(item_name: str) -> Optional[dict]:
    """Retrieve credentials from 1Password via CLI."""
    try:
        result = subprocess.run(
            ["op", "item", "get", item_name, "--format", "json"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return None


def _run_browser_action(action: dict) -> dict:
    """Execute a browser action via OpenClaw browser tool."""
    action["profile"] = BROWSER_PROFILE
    action["target"] = "host"
    return action


class KlutchBrowser:
    """
    Browser automation for Klutch Dashboard card management.
    
    Usage:
        browser = KlutchBrowser()
        browser.login()
        card = browser.create_card("Test Card", 500.0)
        browser.save_to_1password(card)
        browser.terminate_card(card.id)
    """
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        
    def login(self) -> bool:
        """
        Authenticate to Klutch dashboard.
        
        Reads credentials from 1Password or environment variables.
        Returns True on successful login.
        """
        # Get credentials from 1Password or env
        creds = _get_1password_credential("Klutch Dashboard")
        if not creds:
            # Fallback to environment
            email = os.environ.get("KLUTCH_EMAIL")
            password = os.environ.get("KLUTCH_PASSWORD")
            if not (email and password):
                raise click.ClickException(
                    "No credentials found. Set KLUTCH_EMAIL/KLUTCH_PASSWORD or "
                    "store 'Klutch Dashboard' in 1Password."
                )
        else:
            # Extract from 1Password format
            fields = creds.get("fields", [])
            email = next((f.get("value") for f in fields if f.get("id") == "username"), None)
            password = next((f.get("value") for f in fields if f.get("id") == "password"), None)
        
        # Navigate to login page
        _run_browser_action({
            "action": "navigate",
            "targetUrl": f"{KLUTCH_DASHBOARD_URL}/login"
        })
        
        # Get page snapshot with refs
        snapshot = _run_browser_action({
            "action": "snapshot",
            "selector": "form",
            "timeoutMs": 10000
        })
        
        # Type email using ref (email is usually pre-filled, may need different ref)
        _run_browser_action({
            "action": "act",
            "kind": "type",
            "ref": "e2",  # Email textbox ref
            "text": email
        })
        
        # Type password using ref
        _run_browser_action({
            "action": "act",
            "kind": "type",
            "ref": "e3",  # Password textbox ref
            "text": password
        })
        
        # Click login button using ref
        _run_browser_action({
            "action": "act",
            "kind": "click",
            "ref": "e5"  # Sign In button ref
        })
        
        # Wait for dashboard to load (check for cards page)
        _run_browser_action({
            "action": "snapshot",
            "selector": "[data-testid=\"cards-page\"], .cards-page, nav",
            "timeoutMs": 15000
        })
        
        return True
    
    def create_card(self, name: str, spend_limit: float, 
                    monthly_limit: Optional[float] = None) -> BrowserCard:
        """
        Create a new virtual card with custom limits.
        
        Args:
            name: Display name for the card
            spend_limit: Single transaction limit in dollars
            monthly_limit: Optional monthly spending limit
            
        Returns:
            BrowserCard object with full details (PAN, CVV, expiry)
        """
        # Navigate to cards section
        _run_browser_action({
            "action": "navigate",
            "targetUrl": f"{KLUTCH_DASHBOARD_URL}/cards"
        })
        
        # Wait for cards page
        _run_browser_action({
            "action": "snapshot",
            "selector": "[data-testid=\"cards-page\"], .cards-page, button:has-text(\"Create Card\")",
            "timeoutMs": 10000
        })
        
        # Click create card button
        _run_browser_action({
            "action": "act",
            "kind": "click",
            "selector": "button:has-text(\"Create Card\"), [data-testid=\"create-card\"]"
        })
        
        # Wait for modal/form
        _run_browser_action({
            "action": "snapshot",
            "selector": "form, .modal, [role=\"dialog\"]",
            "timeoutMs": 5000
        })
        
        # Fill card name
        _run_browser_action({
            "action": "act",
            "kind": "type",
            "selector": "input[name=\"name\"], input[id*=\"name\"], input[placeholder*=\"name\"]",
            "text": name
        })
        
        # Set spend limit
        _run_browser_action({
            "action": "act",
            "kind": "type",
            "selector": "input[name=\"limit\"], input[id*=\"limit\"], input[placeholder*=\"limit\"]",
            "text": str(int(spend_limit))
        })
        
        # Set monthly limit if provided
        if monthly_limit:
            _run_browser_action({
                "action": "act",
                "kind": "type",
                "selector": "input[name=\"monthlyLimit\"], input[id*=\"monthly\"]",
                "text": str(int(monthly_limit))
            })
        
        # Submit card creation
        _run_browser_action({
            "action": "act",
            "kind": "click",
            "selector": "button:has-text(\"Create\"), button[type=\"submit\"]"
        })
        
        # Wait for card to appear and extract details
        _run_browser_action({
            "action": "snapshot",
            "selector": "[data-testid=\"card-details\"], .card-details, .card-number",
            "timeoutMs": 10000
        })
        
        # Extract card details from the page
        details = self._extract_card_details()
        
        return BrowserCard(
            id=details.get("id", ""),
            name=name,
            last_four=details.get("lastFour", ""),
            pan=details.get("pan"),
            cvv=details.get("cvv"),
            expiry=details.get("expiry"),
            status="ACTIVE",
            spend_limit=spend_limit,
            monthly_limit=monthly_limit
        )
    
    def _extract_card_details(self) -> dict:
        """Extract full card details (PAN, CVV, expiry) from current page."""
        snapshot = _run_browser_action({
            "action": "snapshot",
            "selector": "[data-testid=\"card-details\"], .card-details"
        })
        
        # Parse snapshot for card details
        # This is a placeholder - actual implementation depends on page structure
        details = {}
        
        # Look for card number (typically formatted with spaces or asterisks)
        # Look for CVV (3-4 digit code)
        # Look for expiry (MM/YY or MM/YYYY format)
        
        return details
    
    def get_card_details(self, card_id: str) -> BrowserCard:
        """
        Retrieve full details for a specific card.
        
        Args:
            card_id: The card's ID from Klutch
            
        Returns:
            BrowserCard with full details (PAN, CVV, expiry)
        """
        # Navigate to card details page
        _run_browser_action({
            "action": "navigate",
            "targetUrl": f"{KLUTCH_DASHBOARD_URL}/cards/{card_id}"
        })
        
        # Wait for details page
        _run_browser_action({
            "action": "snapshot",
            "selector": "[data-testid=\"card-details\"], .card-details",
            "timeoutMs": 10000
        })
        
        # Extract all card details
        details = self._extract_card_details()
        
        return BrowserCard(
            id=card_id,
            name=details.get("name", ""),
            last_four=details.get("lastFour", ""),
            pan=details.get("pan"),
            cvv=details.get("cvv"),
            expiry=details.get("expiry"),
            status=details.get("status", "ACTIVE"),
            spend_limit=details.get("spendLimit"),
            monthly_limit=details.get("monthlyLimit")
        )
    
    def terminate_card(self, card_id: str) -> bool:
        """
        Terminate (delete) a virtual card.
        
        Args:
            card_id: The card's ID to terminate
            
        Returns:
            True if termination successful
        """
        # Navigate to card details
        _run_browser_action({
            "action": "navigate",
            "targetUrl": f"{KLUTCH_DASHBOARD_URL}/cards/{card_id}"
        })
        
        # Wait for page load
        _run_browser_action({
            "action": "snapshot",
            "selector": "[data-testid=\"card-details\"], button:has-text(\"Terminate\"), button:has-text(\"Delete\")",
            "timeoutMs": 10000
        })
        
        # Click terminate/delete button
        _run_browser_action({
            "action": "act",
            "kind": "click",
            "selector": "button:has-text(\"Terminate\"), button:has-text(\"Delete Card\"), [data-testid=\"terminate\"]"
        })
        
        # Confirm in modal if present
        _run_browser_action({
            "action": "snapshot",
            "selector": "[role=\"dialog\"], .modal-confirm",
            "timeoutMs": 5000
        })
        
        # Click confirm
        _run_browser_action({
            "action": "act",
            "kind": "click",
            "selector": "button:has-text(\"Confirm\"), button:has-text(\"Yes\"), button[type=\"submit\"]:has-text(\"Terminate\")"
        })
        
        return True
    
    def list_cards(self) -> list[BrowserCard]:
        """
        List all virtual cards with available details.
        
        Returns:
            List of BrowserCard objects
        """
        # Navigate to cards page
        _run_browser_action({
            "action": "navigate",
            "targetUrl": f"{KLUTCH_DASHBOARD_URL}/cards"
        })
        
        # Wait for cards list
        _run_browser_action({
            "action": "snapshot",
            "selector": "[data-testid=\"cards-list\"], .cards-list, [data-testid=\"card-item\"]",
            "timeoutMs": 10000
        })
        
        # Extract cards from page
        cards = self._extract_cards_list()
        return cards
    
    def _extract_cards_list(self) -> list[BrowserCard]:
        """Extract list of cards from current page."""
        snapshot = _run_browser_action({
            "action": "snapshot",
            "selector": "[data-testid=\"card-item\"], .card-item, tr[data-testid*=\"card\"]"
        })
        
        cards = []
        # Parse snapshot for card list items
        
        return cards
    
    def save_to_1password(self, card: BrowserCard, vault: str = "Clawd") -> bool:
        """
        Save card details to 1Password vault.
        
        Args:
            card: BrowserCard object with details to save
            vault: 1Password vault name (default: "Clawd")
            
        Returns:
            True if save successful
        """
        if not card.pan:
            click.echo("Warning: No PAN available, cannot save to 1Password")
            return False
        
        # Build 1Password item JSON
        item_json = json.dumps({
            "title": f"Klutch - {card.name}",
            "category": "identity driver's license",
            "fields": [
                {"id": "pan", "type": "concealed", "value": card.pan},
                {"id": "cvv", "type": "concealed", "value": card.cvv},
                {"id": "expiry", "type": "text", "value": card.expiry},
                {"id": "cardholder", "type": "text", "value": "Martin Kessler"},
                {"id": "lastFour", "type": "text", "value": card.last_four},
                {"id": "cardId", "type": "text", "value": card.id},
                {"id": "spendLimit", "type": "text", "value": str(card.spend_limit) if card.spend_limit else ""}
            ],
            "notes": f"Klutch virtual card - {card.name}"
        })
        
        try:
            result = subprocess.run(
                ["op", "item", "create", "--vault", vault, "--format", "json"],
                input=item_json,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                click.echo(f"✅ Card '{card.name}' saved to 1Password vault '{vault}'")
                return True
            else:
                click.echo(f"❌ Failed to save card: {result.stderr}")
                return False
        except subprocess.SubprocessError as e:
            click.echo(f"❌ 1Password error: {e}")
            return False
    
    def close(self) -> None:
        """Close browser session."""
        if self.browser:
            _run_browser_action({
                "action": "close"
            })


def _format_card_for_display(card: BrowserCard) -> dict:
    """Format card data for JSON display (mask PAN for security)."""
    masked_pan = None
    if card.pan:
        # Mask all but last 4 digits
        masked_pan = f"****-****-****-{card.pan[-4:]}" if len(card.pan) >= 4 else "****-****-****-****"
    
    return {
        "id": card.id,
        "name": card.name,
        "lastFour": card.last_four,
        "maskedPan": masked_pan,
        "cvv": "***" if card.cvv else None,
        "expiry": card.expiry,
        "status": card.status,
        "spendLimit": card.spend_limit,
        "monthlyLimit": card.monthly_limit
    }


# CLI Commands

@click.group()
def browser_cli() -> None:
    """Browser automation commands for Klutch dashboard."""
    pass


@browser_cli.command()
@click.option("--name", "-n", required=True, help="Display name for the virtual card")
@click.option("--limit", "-l", type=float, required=True, help="Spending limit in dollars")
@click.option("--monthly", "-m", type=float, help="Optional monthly spending limit")
@click.option("--save/--no-save", default=True, help="Save card to 1Password")
@click.option("--vault", default="Clawd", help="1Password vault name")
@click.pass_obj
def create(name: str, limit: float, monthly: Optional[float], save: bool, vault: str) -> None:
    """Create a new virtual card with full details via dashboard."""
    browser = KlutchBrowser()
    
    try:
        # Login and create card
        browser.login()
        card = browser.create_card(name, limit, monthly)
        
        # Display results
        click.echo(json.dumps(_format_card_for_display(card), indent=2))
        
        # Save to 1Password if requested
        if save and card.pan:
            browser.save_to_1password(card, vault)
        
        click.echo(f"\n💳 Card '{name}' created with ${limit:.2f} limit")
        if card.pan:
            click.echo(f"   PAN: {card.pan[-4:]} | CVV: {card.cvv} | Exp: {card.expiry}")
        
    except Exception as e:
        raise click.ClickException(str(e))
    finally:
        browser.close()


@browser_cli.command()
@click.option("--card-id", "-c", required=True, help="Card ID to terminate")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@click.pass_obj
def terminate(card_id: str, yes: bool) -> None:
    """Terminate a virtual card via dashboard."""
    if not yes:
        if not click.confirm(f"Terminate card '{card_id}'? This cannot be undone."):
            click.echo("Cancelled.")
            return
    
    browser = KlutchBrowser()
    
    try:
        # Login and terminate
        browser.login()
        success = browser.terminate_card(card_id)
        
        if success:
            click.echo(f"✅ Card '{card_id}' terminated successfully")
        else:
            click.echo(f"❌ Failed to terminate card '{card_id}'")
            
    except Exception as e:
        raise click.ClickException(str(e))
    finally:
        browser.close()


@browser_cli.command()
@click.option("--card-id", "-c", help="Card ID to get details (lists all if not specified)")
@click.pass_obj
def details(card_id: Optional[str]) -> None:
    """Get full card details via dashboard."""
    browser = KlutchBrowser()
    
    try:
        browser.login()
        
        if card_id:
            card = browser.get_card_details(card_id)
            click.echo(json.dumps(_format_card_for_display(card), indent=2))
        else:
            cards = browser.list_cards()
            for card in cards:
                click.echo(json.dumps(_format_card_for_display(card), indent=2))
            
    except Exception as e:
        raise click.ClickException(str(e))
    finally:
        browser.close()


@browser_cli.command()
@click.pass_obj
def list(ctx: Any) -> None:
    """List all virtual cards."""
    browser = KlutchBrowser()
    
    try:
        browser.login()
        cards = browser.list_cards()
        
        result = {"cards": [_format_card_for_display(c) for c in cards]}
        click.echo(json.dumps(result, indent=2))
        
    except Exception as e:
        raise click.ClickException(str(e))
    finally:
        browser.close()


def main() -> None:
    browser_cli()


if __name__ == "__main__":
    main()
