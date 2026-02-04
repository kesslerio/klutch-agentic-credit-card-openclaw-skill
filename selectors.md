# Klutch Dashboard - Browser Selectors

This document contains UI selectors for browser automation of the Klutch Dashboard.

**Note:** Selectors may change with UI updates. Update this file when testing reveals changes.

---

## Login Page

| Element | Selector | Description |
|---------|----------|-------------|
| Email input | `input[type="email"]`, `input[name="email"]`, `input[id*="email"]` | Email/username field |
| Password input | `input[type="password"]`, `input[name="password"]` | Password field |
| Sign in button | `button[type="submit"]`, `button:has-text("Sign in")`, `button:has-text("Log in")` | Submit login form |

---

## Dashboard / Cards List Page

| Element | Selector | Description |
|---------|----------|-------------|
| Dashboard container | `[data-testid="dashboard"]`, `.dashboard`, `nav` | Main dashboard area |
| Cards page | `[data-testid="cards-page"]`, `.cards-page` | Cards listing page |
| Cards list | `[data-testid="cards-list"]`, `.cards-list` | Container for all cards |
| Card item | `[data-testid="card-item"]`, `.card-item`, `tr[data-testid*="card"]` | Individual card row/item |
| Create Card button | `button:has-text("Create Card")`, `[data-testid="create-card"]` | Button to open card creation modal |

---

## Card Creation Modal/Form

| Element | Selector | Description |
|---------|----------|-------------|
| Form container | `form`, `.modal`, `[role="dialog"]` | Card creation form |
| Card name input | `input[name="name"]`, `input[id*="name"]`, `input[placeholder*="name"]` | Card display name |
| Spend limit input | `input[name="limit"]`, `input[id*="limit"]`, `input[placeholder*="limit"]` | Single transaction limit |
| Monthly limit input | `input[name="monthlyLimit"]`, `input[id*="monthly"]` | Optional monthly limit |
| Create button | `button:has-text("Create")`, `button[type="submit"]` | Submit card creation |

---

## Card Details Page

| Element | Selector | Description |
|---------|----------|-------------|
| Card details container | `[data-testid="card-details"]`, `.card-details` | Full card details section |
| Card number/PAN | `.card-number`, `[data-testid="card-number"]` | Full card number display |
| Card CVV | `.card-cvv`, `[data-testid="cvv"]` | CVV code |
| Card expiry | `.card-expiry`, `[data-testid="expiry"]` | Expiration date |
| Card status | `.card-status`, `[data-testid="status"]` | ACTIVE/TERMINATED status |
| Terminate button | `button:has-text("Terminate")`, `button:has-text("Delete Card")`, `[data-testid="terminate"]` | Delete card button |

---

## Confirmation Dialogs

| Element | Selector | Description |
|---------|----------|-------------|
| Confirm modal | `[role="dialog"]`, `.modal-confirm` | Confirmation dialog |
| Confirm button | `button:has-text("Confirm")`, `button:has-text("Yes")` | Confirm action |
| Cancel button | `button:has-text("Cancel")`, `button:has-text("No")` | Cancel action |

---

## Common Patterns

### Waiting for Elements
```python
# Wait up to 10 seconds for element to appear
_action = {
    "action": "snapshot",
    "selector": "<selector>",
    "timeoutMs": 10000
}
```

### Clicking Elements
```python
_action = {
    "action": "act",
    "kind": "click",
    "selector": "<selector>"
}
```

### Typing Text
```python
_action = {
    "action": "act",
    "kind": "type",
    "selector": "<input-selector>",
    "text": "text to type"
}
```

---

## URL Patterns

| Page | URL |
|------|-----|
| Login | `https://dashboard.klutchcard.com/login` |
| Cards list | `https://dashboard.klutchcard.com/cards` |
| Card details | `https://dashboard.klutchcard.com/cards/{card_id}` |

---

## Testing Notes

When selectors change, update this file and run verification:
1. Navigate to the page
2. Take a snapshot to find new selectors
3. Update the table above
4. Test the automation flow

---

## 1Password Integration

| Action | Command |
|--------|---------|
| Get credential | `op item get "Klutch Dashboard" --format json` |
| Save card | `op item create --vault "Clawd"` |

Fields to include when saving cards:
- `pan` (concealed) - Full card number
- `cvv` (concealed) - Security code
- `expiry` (text) - MM/YY format
- `cardholder` (text) - Cardholder name
- `lastFour` (text) - Last 4 digits
- `cardId` (text) - Klutch card ID
- `spendLimit` (text) - Spending limit
