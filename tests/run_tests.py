import unittest
import httpx
import asyncio
import sys
import os

# Add parent directory to path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

class TestPortfolio(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        transport = httpx.ASGITransport(app=app)
        self.client = httpx.AsyncClient(transport=transport, base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_read_root(self):
        """Test if the root endpoint returns 200 and correct content."""
        response = await self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("DevFolio", response.text)
        print("✅ Root endpoint (/) passed")

    async def test_api_status(self):
        """Test if the status endpoint returns 200 and online status."""
        response = await self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "online")
        print("✅ API Status (/api/status) passed")

    async def test_projects_sync(self):
        """Test if project sync returns 200."""
        response = await self.client.get("/projects/sync")
        self.assertEqual(response.status_code, 200)
        print("✅ Project Sync (/projects/sync) passed")

    async def test_404_handling(self):
        """Test how the app handles non-existent routes."""
        response = await self.client.get("/non-existent-route")
        self.assertEqual(response.status_code, 404)
        print(f"ℹ️ 404 Response: {response.json()}")
        if response.json().get("detail") == "Not Found":
             print("✅ Standard 404 handling confirmed")

if __name__ == "__main__":
    unittest.main(verbosity=2)
