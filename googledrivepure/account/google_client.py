import requests
import os
import json
import time


class FileSystemTokenBackend:
    def __init__(self, token_path, token_filename):
        self.token_path = token_path
        self.token_filename = token_filename
        self.token_path = os.path.join(self.token_path, self.token_filename)

        if not os.path.exists(self.token_path):
            os.mkdir(self.token_path)

        if os.path.exists(self.token_path):
            with open(self.token_path, "r") as f:
                self.config = json.load(f)
        else:
            self.config = {}

    def update_config(self, config):
        self.config.update(config)
        with open(self.token_path, "w") as f:
            f.write(json.dumps(self.config))


class GoogleAccount:
    def __init__(self, client, token_backend=None, proxies=None):
        self.base_auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.exchange_url = "https://oauth2.googleapis.com/token"
        self.token_url = "https://oauth2.googleapis.com/token"
        self.client_id, self.client_secret = client
        self.token_backend = token_backend
        if not self.token_backend:
            self.token_backend = FileSystemTokenBackend(
                token_path="./", token_filename="gd_token.json"
            )
        self.proxies = proxies

    def authenticate(self, scope, redirect_url):
        url = self._get_auth_url(scope, redirect_url)
        print(url)
        print("Please enter the code here:")
        code = input()
        config = self._exchange_token(code, scope, redirect_url)
        config["get_time"] = int(time.time())
        self.token_backend.update_config(config)
        print("Auth flow finished, now you can use api.")
        return self

    @property
    def token_expired(self):
        if not self.token_backend.config:
            raise ValueError("Hasn't authenticate yet.")
        else:
            expired_time = self.token_backend.config.get(
                "expires_in"
            ) + self.token_backend.config.get("get_time")
            return expired_time <= int(time.time())

    def get_token(self):
        if self.token_expired:
            self._refresh_token()
        return self.token_backend.config.get("access_token")

    def _get_auth_url(self, scope, redirect_url):
        params = {
            "scope": scope,
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_url,
            "state": "state",
        }
        formated_url = (
            self.base_auth_url
            + "?"
            + "".join(
                ["{}={}&".format(key, value) for key, value in params.items()]
            ).rstrip("&")
        )
        return formated_url

    def _exchange_token(self, code, scope, redirect_url):
        data = {
            "code": code,
            "redirect_uri": redirect_url,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": scope,
            "grant_type": "authorization_code",
        }
        r = requests.post(self.exchange_url, data=data, proxies=self.proxies)
        return r.json()

    def _refresh_token(self):
        refresh_token = self.token_backend.config.get("refresh_token")
        data = {
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
        }
        r = requests.post(self.token_url, data=data, proxies=self.proxies)
        self.token_backend.update_config({**r.json(), **{"get_time": int(time.time())}})
