import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from shipmybox.client import ShipMyBoxClient

class TestShipMyBoxParser(unittest.TestCase):
    def setUp(self):
        # We patch _load_session to not read actual file
        with patch.object(ShipMyBoxClient, '_load_session'):
            self.client = ShipMyBoxClient()
        self.dumps_dir = Path(__file__).parent.parent / "page_dumps"

    @patch("shipmybox.client.requests.Session.get")
    def test_get_address_and_codes(self, mock_get):
        html_path = self.dumps_dir / "Addressa and code page.html"
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        mock_response = MagicMock()
        mock_response.text = html_content
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        data = self.client.get_address_and_codes()

        self.assertEqual(data["customer_id"], "00022GG")
        self.assertEqual(data["alternative_id"], "AAACCGG")
        self.assertIn("Shipmybox.eu   00022GG", data["shipping_address"])
        self.assertIn("30-740 Kraków, Poland", data["shipping_address"])

    @patch("shipmybox.client.requests.Session.get")
    def test_get_parcels(self, mock_get):
        html_path = self.dumps_dir / "my_parcels.html"
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        mock_response = MagicMock()
        mock_response.text = html_content
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        parcels = self.client.get_parcels()

        self.assertTrue(len(parcels) > 0)
        first_parcel = parcels[0]
        self.assertEqual(first_parcel["number"], "1/04/2018")
        self.assertEqual(first_parcel["status"], "Delivered")
        self.assertEqual(first_parcel["price_eur"], "12.50")

if __name__ == "__main__":
    unittest.main()
