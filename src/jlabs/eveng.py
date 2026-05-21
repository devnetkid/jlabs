# src/jlabs/eveng.py

import json

import requests


class EveNgClient:
    def __init__(self, host):
        self.base_url = f"http://{host}/api"
        self.session = requests.Session()

    def login(self, username="admin", password="eve"):
        """Logs in using session-based authentication."""
        url = f"{self.base_url}/auth/login"
        payload = {"username": username, "password": password, "html5": "-1"}
        response = self.session.post(url, json=payload)
        response.raise_for_status()

    def logout(self):
        """Logs out and clears the session."""
        url = f"{self.base_url}/auth/logout"
        response = self.session.get(url)
        response.raise_for_status()
        self.session.cookies.clear()

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
