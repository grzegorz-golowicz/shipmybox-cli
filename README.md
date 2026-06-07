# ShipMyBox CLI

A Python command-line utility designed to automatically extract and format real-time delivery information from your ShipMyBox account.

### Purpose
ShipMyBox is a specialized company providing warehouse addresses in Poland for forwarding packages to your address in Malta.
This CLI tool allows you to instantly retrieve your **unique personal shipping codes, warehouse forwarding address, and status of all your parcels** without needing to manually open a browser and log in to the web panel. It offers beautifully formatted terminal tables as well as JSON output for scripting and automation.

---

## 🚀 The Easiest Way to Run It

You don't need to download the source code or install the package permanently. Using [`uvx`](https://docs.astral.sh/uv/) (or `pipx`), you can execute the tool directly from this GitHub repository!

**Run a command directly (e.g. `info`):**
```bash
uvx --from git+https://github.com/grzegorz-golowicz/shipmybox-cli shipmybox info
```
*(If you use `pipx`, run: `pipx run --spec git+https://github.com/grzegorz-golowicz/shipmybox-cli shipmybox info`)*

---

## ⬇️ Permanent Installation

If you prefer to install it globally on your system so you can just type `shipmybox` anytime:

### Using `uv` (Recommended)
```bash
uv tool install git+https://github.com/grzegorz-golowicz/shipmybox-cli
# Now you can run `shipmybox` from anywhere!
```

### Using `pipx`
```bash
pipx install git+https://github.com/grzegorz-golowicz/shipmybox-cli
```

---

## 🛠 Usage Guide

### 1. Login
Before retrieving data, you must authenticate with your ShipMyBox account.
```bash
shipmybox login
```
*If running via `uvx` without installing: `uvx --from git+https://github.com/grzegorz-golowicz/shipmybox-cli shipmybox login`*

This will securely prompt for your email and password, and save a session cookie to `~/.config/shipmybox/session.json`.

### 2. View Info (Address & Codes)
View your unique IDs and the warehouse forwarding address:
```bash
shipmybox info
```
Add `--json` for JSON output.

### 3. View Parcels
List all your parcels along with status, price, and dimensions in a neat table:
```bash
shipmybox parcels
```
- Add `--last` to only display the most recently added parcel.
- Add `--json` for JSON output that can be piped into `jq` or other tools.

### 4. Monitor & Send Notifications (`check`)
Check if a new parcel has appeared or if the status of your last parcel has changed since the previous check, and send a notification. This is ideal for running as a background cronjob.

```bash
shipmybox check
```

- Add `--dry-run` to simulate the check, print notification output, and skip saving state or sending actual notifications.
- Add `--verbose` or `-v` to print execution logs.

#### Configuration (Pushover)
To receive notifications (currently supported via Pushover), you need to configure your credentials:

##### Option A: Configuration File
Create `~/.config/shipmybox/config.json`:
```json
{
  "notification_method": "pushover",
  "notifiers": {
    "pushover": {
      "token": "your_pushover_app_token",
      "user": "your_pushover_user_key"
    }
  }
}
```

##### Option B: Environment Variables
Alternatively, you can set the configuration using environment variables:
```bash
export PUSHOVER_TOKEN="your_pushover_app_token"
export PUSHOVER_USER="your_pushover_user_key"
```

#### Running as a Linux Cronjob
You can schedule checks to run automatically. Since cron runs in a minimal environment, it is best to pass environment variables directly or use the config file.

For example, to run every hour:
```cron
0 * * * * PUSHOVER_TOKEN="your_token" PUSHOVER_USER="your_user" /usr/local/bin/shipmybox check
```
*(Ensure you use the absolute path to `shipmybox` / `python` executable in your system.)*
