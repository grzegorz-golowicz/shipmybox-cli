---
name: shipmybox
description: >
  Use this skill when the user wants to check their ShipMyBox account — for example to get their
  warehouse shipping address, personal customer codes, or a list of parcels (with status, weight,
  dimensions, and price). Activate this skill for any request like "what is my ShipMyBox address?",
  "show me my parcels", "am I logged in to ShipMyBox?", or "what is my customer ID?".
---

# ShipMyBox CLI Skill

ShipMyBox is a Polish warehouse forwarding service for packages destined for Malta.
This skill teaches you how to use the `shipmybox` CLI to retrieve account information
on behalf of the user.

## Prerequisites

The CLI must be installed. If the user has not installed it yet, use:

```bash
uv tool install git+https://github.com/grzegorz-golowicz/shipmybox-cli
```

Or run commands without installing by prefixing every command below with
`uvx --from git+https://github.com/grzegorz-golowicz/shipmybox-cli`.

## When to Use Each Command

### 1. Logging in (`shipmybox login`)

Use this when:
- The user asks to log in or authenticate with ShipMyBox.
- Any other command fails because the session is missing or expired
  (you will see an error like "Session expired. Please log in again.").

```bash
shipmybox login --email <email> --password <password>
```

Ask the user for their email and password if not already provided.
The session cookie is saved to `~/.config/shipmybox/session.json` and reused
automatically by subsequent commands — the user only needs to log in once.

### 2. Getting the shipping address and codes (`shipmybox info`)

Use this when:
- The user asks for their warehouse address, shipping address, or forwarding address.
- The user asks for their Customer ID or Alternative ID.
- The user wants to know where to send packages.

```bash
# Human-readable table (default)
shipmybox info

# Machine-readable JSON (useful for extracting a specific field)
shipmybox info --json
```

The JSON output contains:
- `customer_id` — primary unique code to include on parcels
- `alternative_id` — secondary code accepted by some shops
- `shipping_address` — primary Polish warehouse address
- `alternative_address` — alternative Polish warehouse address

### 3. Listing parcels (`shipmybox parcels`)

Use this when:
- The user asks about their packages, parcels, shipments, or deliveries.
- The user wants to know the status, price, or dimensions of a parcel.
- The user asks "what is my latest parcel?" or "has my package arrived?".

```bash
# Show all parcels as a table
shipmybox parcels

# Show only the most recently added parcel
shipmybox parcels --last

# JSON output (all parcels)
shipmybox parcels --json

# JSON output (last parcel only)
shipmybox parcels --last --json
```

Each parcel record contains:
- `number` — parcel tracking/reference number
- `length_cm`, `width_cm`, `height_cm` — dimensions in centimetres
- `weight_kg` — weight in kilograms
- `status` — current delivery status (e.g. "In warehouse", "Shipped")
- `price_eur` — forwarding fee in euros
- `payment_status` — whether the forwarding fee has been paid

## Workflow

```
User request
    │
    ├─ address / codes → shipmybox info
    │
    ├─ parcels / packages / status → shipmybox parcels [--last]
    │
    └─ login / session expired → shipmybox login
```

1. Run the appropriate command.
2. If the command fails with a session error, run `shipmybox login` first, then retry.
3. Present the output clearly to the user — use `--json` when you need to extract or
   format a specific field, otherwise the default table output is fine to show as-is.

## Guidelines

- Never store or log the user's password beyond passing it to `shipmybox login`.
- Always check the command output for error messages and report them to the user.
- If the user has not logged in and does not provide credentials, ask before running
  `shipmybox login`.
- Prefer `--last` when the user only asks about their most recent parcel, to keep the
  output concise.
