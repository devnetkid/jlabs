# src/jlabs/eveng.py

import os
import sys
import requests
import urllib3

# Suppress insecure request warnings for EVE-NG Pro's self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class EveNgClient:
    def __init__(self):
        # Fetch environment variables on instantiation
        eve_target = os.getenv("JLABS_EVENG_IP")
        if not eve_target:
            print("You must define your EVE-NG IP or URL in the environment variable JLABS_EVENG_IP.")
            sys.exit(1)

        self.username = os.getenv("JLABS_EVENG_USER", "admin")
        self.password = os.getenv("JLABS_EVENG_PASS", "eve")

        # Determine version based on the presence of 'https'
        self.is_pro = eve_target.lower().startswith("https")

        # Safely construct the base URL
        if eve_target.startswith("http"):
            self.base_url = f"{eve_target.rstrip('/')}/api"
        else:
            self.base_url = f"http://{eve_target}/api"

        # Initialize session and disable SSL verification globally
        self.session = requests.Session()
        self.session.verify = False
       
        # Store the user's specific folder path (populated during login)
        self.user_folder = ""

    def login(self, username=None, password=None):
        """Logs in and queries the server for the user's specific home folder."""
        user = username or self.username
        pwd = password or self.password
       
        # Perform the actual login (POST request)
        login_url = f"{self.base_url}/auth/login"
        payload = {
            "username": user, 
            "password": pwd,
            "html5": "-1"
        }

        response = self.session.post(login_url, json=payload)
        response.raise_for_status()
       
        # Query the EVE-NG server for the logged-in user's profile (GET request)
        # This returns a payload containing {"email", "folder", "role", "username", etc.}
        auth_info_url = f"{self.base_url}/auth"
        auth_info_response = self.session.get(auth_info_url)
       
        if auth_info_response.status_code == 200:
            session_data = auth_info_response.json().get("data", {})
            self.user_folder = session_data.get("folder", "")
        else:
            self.user_folder = ""
           
        if username:
            self.username = username
           
        return response.json()

    def logout(self):
        """Logs out and clears the session."""
        url = f"{self.base_url}/auth/logout"
        response = self.session.get(url)
        response.raise_for_status()
        self.session.cookies.clear()
        self.user_folder = ""
        return response.json()

    def get_lab_endpoint(self, lab_path_or_name, sub_endpoint=""):
        """
        Dynamically builds the lab path. If the user provides a path with slashes,
        it trusts the input. Otherwise, it uses the folder extracted during login.
        """
        # Ensure it ends with .unl
        if not lab_path_or_name.endswith(".unl"):
            lab_path_or_name = f"{lab_path_or_name}.unl"

        # Clean leading slashes
        lab_path_or_name = lab_path_or_name.lstrip("/")

        # If you passed a direct path (e.g., "labs/user Labs/my_lab"), trust it!
        if "/" in lab_path_or_name:
            base_path = f"labs/{lab_path_or_name}"
           
        # Otherwise, rely on the dynamic user folder logic
        else:
            folder = self.user_folder.strip("/")
            if self.is_pro and folder:
                base_path = f"labs/{folder}/{lab_path_or_name}"
            else:
                base_path = f"labs/{lab_path_or_name}"

        # Append sub-endpoints like 'nodes' or 'topology' if requested
        if sub_endpoint:
            return f"{base_path}/{sub_endpoint.lstrip('/')}"
           
        return base_path
       
    def get(self, endpoint):
        # EVE-NG handles URL encoding for spaces automatically via the requests library
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def post(self, endpoint, data=None):
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

    def put(self, endpoint, data=None):
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        response = self.session.put(url, json=data)
        response.raise_for_status()
        return response.json()

    def delete(self, endpoint):
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        response = self.session.delete(url)
        response.raise_for_status()
        return response.status_code
