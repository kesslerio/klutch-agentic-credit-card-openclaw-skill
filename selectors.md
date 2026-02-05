# Klutch Dashboard - Browser Selectors

This document contains verified UI selectors for browser automation of the Klutch Dashboard.

**Verified:** 2026-02-04  
**URL:** `https://app.klutch.cards`

---

## Login Page

| Element | Verified Selector | Ref |
|---------|-----------------|-----|
| Email input | `textbox "Email Address"` | e2 |
| Password input | `textbox "Password"` | e3 |
| Sign In button | `button "Sign In"` | e5 |

---

## Cards List Page (`/cards`)

| Element | Verified Selector | Ref |
|---------|-----------------|-----|
| Heading | `heading "Cards"` | e6 |
| New Virtual Card button | `button "New Virtual card"` | e8 |
| New Physical Card button | `button "New Physical card"` | e10 |
| Search box | `textbox "Search Cards"` | e15 |
| Card row (Test) | `Dashboard Test Card (5722)...` | e18 |
| Card row (Main) | `Martin Kessler (9237)...` | e19 |

**Card URL pattern:** `/cards/{card_id}`

---

## Card Creation Form (`/cards/add?media=VIRTUAL`)

| Element | Verified Selector | Ref |
|---------|-----------------|-----|
| Card Name | `textbox "CARD NAME"` | e1 |
| Spending Limit Amount | `textbox "Spending Limit Amount"` | e2 |
| Create Card button | `button "CREATE CARD"` | e3 |

**Note:** The spending limit field appears to be disabled by default. May need to enable it first.

---

## Card Details Page (`/cards/{card_id}`)

| Element | Verified Selector | Ref |
|---------|-----------------|-----|
| Back button | `button "Back to Cards"` | e6 |
| Card Name | `textbox "CARD NAME"` | e8 |
| Spending Limit | `textbox "Spending Limit Amount"` | e9 |
| Save button | `button "SAVE"` | e10 |
| Delete button | `button "DELETE"` | e11 |

**Card number display format:** `•••• •••• •••• 9374`

---

## URL Patterns (Verified)

| Page | URL |
|------|-----|
| Login | `https://app.klutch.cards/login` |
| Cards list | `https://app.klutch.cards/cards` |
| Create virtual card | `https://app.klutch.cards/cards/add?media=VIRTUAL` |
| Create physical card | `https://app.klutch.cards/cards/add?media=PLASTIC` |
| Card details | `https://app.klutch.cards/cards/{card_id}` |

---

## Browser Automation Usage

### Using refs (recommended)
```python
# Get refs from snapshot
snapshot = browser.snapshot()
# refs like "e1", "e2" are returned

# Type using ref
browser.act({"kind": "type", "ref": "e1", "text": "My Card"})

# Click using ref
browser.act({"kind": "click", "ref": "e3"})
```

---

## 1Password Integration

| Action | Command |
|--------|---------|
| Get credential | `op item get "Klutch Dashboard" --format json` |
| Save card | `op item create --vault "Clawd"` |

Fields for card storage:
- `pan` (concealed) - Full card number
- `cvv` (concealed) - Security code  
- `expiry` (text) - MM/YY format
- `cardholder` (text) - Cardholder name
- `lastFour` (text) - Last 4 digits
- `cardId` (text) - Klutch card ID
