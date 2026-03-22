import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from shipmybox.exceptions import LoginError, DataExtractionError

logger = logging.getLogger(__name__)

class ShipMyBoxClient:
    BASE_URL = "https://shipmybox.eu"
    SESSION_FILE = Path.home() / ".config" / "shipmybox" / "session.json"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        self._load_session()

    def _load_session(self):
        """Load session cookies from file if it exists."""
        if self.SESSION_FILE.exists():
            try:
                with open(self.SESSION_FILE, "r") as f:
                    cookies = json.load(f)
                    self.session.cookies.update(cookies)
            except Exception as e:
                logger.debug(f"Failed to load session: {e}")

    def _save_session(self):
        """Save session cookies to file."""
        self.SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(self.SESSION_FILE, "w") as f:
            json.dump(self.session.cookies.get_dict(), f)

    def login(self, email: str, password: str) -> bool:
        """Authenticate with ShipMyBox."""
        login_url = f"{self.BASE_URL}/login"
        data = {
            "mk_login": email,
            "mk_haslo": password,
            "logowanie": "yes",
            "submit": "Log in"
        }
        
        response = self.session.post(login_url, data=data)
        response.raise_for_status()

        # Verify login by checking if 'wyloguj' (logout) is in the response text or 'log out' button exists
        if 'name="wyloguj"' not in response.text and "log out" not in response.text.lower():
            raise LoginError("Login failed. Please check your credentials.")
        
        self._save_session()
        return True

    def get_address_and_codes(self) -> Dict[str, str]:
        """Extract user address and unique codes."""
        # Typically the codes are on the login redirect page or the main account page
        # The user provided a dump from `https://shipmybox.eu/login` which shows the address right there.
        # This implies that after login, the /login page acts as the dashboard.
        url = f"{self.BASE_URL}/login"
        response = self.session.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        prawy_div = soup.find("div", id="prawy")
        
        if not prawy_div:
            if "log out" not in response.text.lower():
                raise LoginError("Session expired. Please log in again.")
            raise DataExtractionError("Could not find address information on the page.")

        data = {}
        
        h5_tags = prawy_div.find_all("h5")
        if len(h5_tags) >= 2:
            data["customer_id"] = h5_tags[0].get_text(strip=True)
            # Sometimes it's inside the text, e.g. "Alternative version of Customer ID: AAACCGG"
            data["alternative_id"] = h5_tags[1].get_text(strip=True).replace("Alternative version of Customer ID: ", "").replace("Alternative version:", "").strip()
        
        if len(h5_tags) >= 4:
            address_lines = [line.strip() for line in h5_tags[2].stripped_strings if line.strip()]
            data["shipping_address"] = "\n".join(address_lines)

            alt_address_lines = [line.strip() for line in h5_tags[3].stripped_strings if line.strip()]
            data["alternative_address"] = "\n".join(alt_address_lines)

        return data

    def get_parcels(self) -> List[Dict[str, str]]:
        """Extract a list of parcels."""
        url = f"{self.BASE_URL}/my-parcels"
        response = self.session.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table", class_="tab")
        
        if not table:
            if "log out" not in response.text.lower() and 'name="wyloguj"' not in response.text:
                raise LoginError("Session expired. Please log in again.")
            return []

        parcels = []
        tbody = table.find("tbody")
        if not tbody:
            return []

        rows = tbody.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 10:
                parcel = {
                    "number": cols[0].get_text(strip=True),
                    "length_cm": cols[1].get_text(strip=True),
                    "width_cm": cols[2].get_text(strip=True),
                    "height_cm": cols[3].get_text(strip=True),
                    "weight_kg": cols[4].get_text(strip=True),
                    "status": cols[5].get_text(strip=True),
                    "price_eur": cols[6].get_text(strip=True),
                    "payment_status": cols[9].get_text(strip=True)
                }
                parcels.append(parcel)

        return parcels
