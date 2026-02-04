#!/usr/bin/env python3
"""Klutch CLI - OpenClaw skill for Klutch programmable credit card API."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import click
import requests

from auth import get_token

CONFIG_PATH = Path.home() / ".config" / "klutch" / "config.json"
TOKEN_PATH = Path.home() / ".config" / "klutch" / "token.json"

DEFAULT_TIMEOUT = 30
DEFAULT_CONFIG: dict[str, Any] = {
    "api": {
        "endpoint": "https://graphql.klutchcard.com/graphql",
        "timeout": DEFAULT_TIMEOUT,
    }
}


@dataclass
class Context:
    yolo: bool


def _load_config() -> dict[str, Any]:
    if CONFIG_PATH.exists():
        try:
            user_cfg = json.loads(CONFIG_PATH.read_text())
            cfg = DEFAULT_CONFIG.copy()
            cfg.update(user_cfg)
            return cfg
        except (json.JSONDecodeError, IOError):
            pass
    return DEFAULT_CONFIG.copy()


def _save_config(cfg: dict[str, Any]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))


def _api_request(query: str, endpoint: str, token: str, variables: Optional[dict] = None) -> dict[str, Any]:
    """Make a GraphQL API request to Klutch."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload: dict[str, Any] = {"query": query}
    if variables:
        payload["variables"] = variables
    
    response = requests.post(endpoint, json=payload, headers=headers, timeout=DEFAULT_TIMEOUT)
    
    if response.status_code >= 400:
        raise click.ClickException(f"API error ({response.status_code}): {response.text}")
    
    try:
        result = response.json()
    except json.JSONDecodeError:
        return {"raw": response.text}
    
    if "errors" in result:
        raise click.ClickException(f"GraphQL error: {result['errors']}")
    
    return result.get("data", {})


@click.group()
@click.option("--yolo", is_flag=True, help="Bypass confirmation prompts for autonomous mode.")
@click.pass_context
def cli(ctx: click.Context, yolo: bool) -> None:
    ctx.obj = Context(yolo=yolo)


@cli.command()
@click.pass_obj
def balance(ctx: Context) -> None:
    """Check card information."""
    cfg = _load_config()
    endpoint = cfg["api"]["endpoint"]
    token = get_token(endpoint)
    
    card_query = "{ cards { id name status } }"
    card_data = _api_request(card_query, endpoint, token)
    cards = card_data.get("cards", [])
    
    result = {
        "cards": cards,
        "note": "Use 'klutch transactions' for transaction details",
    }
    click.echo(json.dumps(result, indent=2))


@cli.command()
@click.option("--limit", type=int, default=10, show_default=True)
@click.pass_obj
def transactions(ctx: Context, limit: int) -> None:
    """List recent transactions."""
    cfg = _load_config()
    endpoint = cfg["api"]["endpoint"]
    token = get_token(endpoint)
    
    query = """
    query($filter: TransactionFilter) {
        transactions(filter: $filter) {
            id
            amount
            merchantName
            transactionStatus
        }
    }
    """
    
    now = datetime.now()
    start_date = (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end_date = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    variables = {
        "filter": {
            "startDate": start_date,
            "endDate": end_date,
            "transactionStatus": ["SETTLED", "PENDING"],
        }
    }
    
    data = _api_request(query, endpoint, token, variables)
    transactions_list = data.get("transactions", [])
    
    if limit and len(transactions_list) > limit:
        transactions_list = transactions_list[:limit]
    
    click.echo(json.dumps({"transactions": transactions_list}, indent=2))


@cli.group()
def card() -> None:
    """Manage cards and view card info."""


@card.command("list")
@click.pass_obj
def card_list(ctx: Context) -> None:
    """List all cards."""
    cfg = _load_config()
    endpoint = cfg["api"]["endpoint"]
    token = get_token(endpoint)
    
    query = "{ cards { id name status } }"
    data = _api_request(query, endpoint, token)
    
    click.echo(json.dumps(data, indent=2))


@card.command("categories")
@click.pass_obj
def card_categories(ctx: Context) -> None:
    """List transaction categories."""
    cfg = _load_config()
    endpoint = cfg["api"]["endpoint"]
    token = get_token(endpoint)
    
    query = "{ transactionCategories { id name mccs } }"
    data = _api_request(query, endpoint, token)
    
    click.echo(json.dumps(data, indent=2))


@card.command("spending")
@click.pass_obj
def card_spending(ctx: Context) -> None:
    """View spending grouped by category."""
    cfg = _load_config()
    endpoint = cfg["api"]["endpoint"]
    token = get_token(endpoint)
    
    now = datetime.now()
    start_date = now.replace(day=1).strftime("%Y-%m-%dT%H:%M:%SZ")
    end_date = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    query = """
    query($filter: TransactionFilter, $groupBy: TransactionGroupByProperty, $operation: GroupByOperation) {
        groupTransactions(filter: $filter, groupByProperty: $groupBy, operation: $operation) {
            key
            value
        }
    }
    """
    
    variables = {
        "filter": {
            "startDate": start_date,
            "endDate": end_date,
            "transactionStatus": ["SETTLED"],
            "transactionTypes": ["CHARGE"],
        },
        "groupBy": "CATEGORY",
        "operation": "SUM",
    }
    
    data = _api_request(query, endpoint, token, variables)
    click.echo(json.dumps(data, indent=2))


@cli.group()
def config() -> None:
    """Manage configuration."""


@config.command("get")
@click.argument("key", required=False)
def config_get(key: Optional[str]) -> None:
    """Get configuration value."""
    cfg = _load_config()
    if not key:
        click.echo(json.dumps(cfg, indent=2, sort_keys=True))
        return
    
    keys = key.split(".")
    value = cfg
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            raise click.ClickException(f"Unknown config key: {key}")
    click.echo(json.dumps(value, indent=2))


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str) -> None:
    """Set configuration value."""
    cfg = _load_config()
    
    if value.lower() == "true":
        parsed_value = True
    elif value.lower() == "false":
        parsed_value = False
    elif value.isdigit():
        parsed_value = int(value)
    else:
        try:
            parsed_value = float(value)
        except ValueError:
            parsed_value = value
    
    keys = key.split(".")
    target = cfg
    for k in keys[:-1]:
        if k not in target:
            target[k] = {}
        target = target[k]
    target[keys[-1]] = parsed_value
    
    _save_config(cfg)
    click.echo(f"Set {key} = {parsed_value}")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
