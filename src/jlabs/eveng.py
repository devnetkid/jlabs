# src/jlabs/eveng.py

import os
import sys
import requests
import urllib3

# Suppress insecure request warnings for EVE-NG Pro's self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class EveNgClient:
    def __init__(self):
        # 1. Fetch environment variables on instantiation
        eve_target = os.getenv("JLABS_EVENG_IP")
        if not eve_target:
            print("❌ You must define your EVE-NG IP or URL in the environment variable JLABS_EVENG_IP.")
            sys.exit(1)

        self.username = os.getenv("JLABS_EVENG_USER", "admin")
        self.password = os.getenv("JLABS_EVENG_PASS", "eve")

        # 2. Determine version based on the presence of 'https'
        self.is_pro = eve_target.lower().startswith("https")

        # 3. Safely construct the base URL
        if eve_target.startswith("http"):
            self.base_url = f"{eve_target.rstrip('/')}/api"
        else:
            # Fallback for Community if they only provided a raw IP address
            self.base_url = f"http://{eve_target}/api"

        # 4. Initialize session and disable SSL verification globally
        self.session = requests.Session()
        self.session.verify = False  # Applies to all get/post/put/delete calls

    def login(self, username=None, password=None):
        """Logs in using session-based authentication."""
        user = username or self.username
        pwd = password or self.password
        
        url = f"{self.base_url}/auth/login"
        payload = {"username": user, "password": pwd}

        # Inject Pro-specific parameter if HTTPS is detected
        if self.is_pro:
            payload["html5"] = "-1"

        response = self.session.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    def logout(self):
        """Logs out and clears the session."""
        url = f"{self.base_url}/auth/logout"
        response = self.session.get(url)
        response.raise_for_status()
        self.session.cookies.clear()
        return response.json()

    def get(self, endpoint):
        url = f"{self.base_url}/{endpoint}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def post(self, endpoint, data=None):
        url = f"{self.base_url}/{endpoint}"
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

    def put(self, endpoint, data=None):
        url = f"{self.base_url}/{endpoint}"
        response = self.session.put(url, json=data)
        response.raise_for_status()
        return response.json()

    def delete(self, endpoint):
        url = f"{self.base_url}/{endpoint}"
        response = self.session.delete(url)
        response.raise_for_status()
        return response.status_code


























































