# Klutch Dashboard - Browser Selectors

This document contains UI selectors for browser automation of the Klutch Dashboard.

**Verified Selectors** (tested 2026-02-04):
- Login URL: `https://app.klutch.cards/login`

---

## Verified Login Page

| Element | Verified Selector | Description |
|---------|------------------|-------------|
| Email input | `textbox "Email Address"` | Email/username field |
| Password input | `textbox "Password"` | Password field |
| Sign In button | `button "Sign In"` | Submit login form |

---

## Hypothetical Selectors (Need Verification)

The following selectors are estimates based on typical SPA patterns. **Update when verified.**

### Dashboard / Cards List Page

| Element | Estimated Selector | Description |
|---------|-------------------|-------------|
| Cards page | `[data-testid="cards-page"]`, `.cards-page` | Cards listing page |
| Cards list | `[data-testid="cards-list"]`, `.cards-list` | Container for all cards |
| Card item | `[data-testid="card-item"]`, `.card-item` | Individual card row/item |
| Create Card button | `button:has-text("Create Card")`, `[data-testid="create-card"]` | Button to open card creation modal |

### Card Creation Modal/Form

| Element | Estimated Selector | Description |
|---------|-------------------|-------------|
| Form container | `form`, `.modal`, `[role="dialog"]` | Card creation form |
| Card name input | `textbox "Name"`, `input[name="name"]` | Card display name |
| Spend limit input | `textbox "Limit"`, `input[name="limit"]` | Single transaction limit |
| Monthly limit input | `textbox "Monthly Limit"`, `input[name="monthlyLimit"]` | Optional monthly limit |
| Create button | `button "Create"` | Submit card creation |

### Card Details Page

| Element | Estimated Selector | Description |
|---------|-------------------|-------------|
| Card details container | `[data-testid="card-details"]`, `.card-details` | Full card details section |
| Card number/PAN | `.card-number`, `[data-testid="card-number"]` | Full card number display |
| Card CVV | `.card-cvv`, `[data-testid="cvv"]` | CVV code |
| Card expiry | `.card-expiry`, `[data-testid="expiry"]` | Expiration date |
| Card status | `.card-status`, `[data-testid="status"]` | ACTIVE/TERMINATED status |
| Terminate button | `button "Terminate"`, `button:has-text("Delete Card")` | Delete card button |

### Confirmation Dialogs

| Element | Estimated Selector | Description |
|---------|-------------------|-------------|
| Confirm modal | `[role="dialog"]`, `.modal-confirm` | Confirmation dialog |
| Confirm button | `button "Confirm"`, `button:has-text("Yes")` | Confirm action |

---

## URL Patterns (Verified)

| Page | URL |
|------|-----|
| Login | `https://app.klutch.cards/login` |
| Cards | `https://app.klutch.cards/cards` |
| Card details | `https://app.klutch.cards/cards/{card_id}` |

---

## Browser Automation Patterns

### Using refs from snapshot (recommended)
```python
# Get refs from snapshot
snapshot = browser.snapshot()
# refs like "e1", "e2" are returned for elements

# Type using ref
browser.act({"kind": "type", "ref": "e2", "text": "email@example.com"})

# Click using ref
browser.act({"kind": "click", "ref": "e5"})
```

### Using text selectors (fallback)
```python
browser.act({"kind": "click", "selector": "button \"Sign In\""})
browser.act({"kind": "type", "selector": "textbox \"Password\"", "text": "secret"})
```

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

---

## Testing Notes

1. Navigate to the page
2. Take a snapshot to get element refs
3. Use refs for reliable interaction
4. Update this file with verified selectors
