import os
import requests as _requests

def _headers():
    key = os.getenv("SUPABASE_KEY", "")
    return {
        "apikey":        key,
        "Authorization": f"Bearer {key}",
        "Content-Type":  "application/json",
        "Prefer":        "return=minimal",
    }

def _url(table):
    base = os.getenv("SUPABASE_URL", "").rstrip("/")
    return f"{base}/rest/v1/{table}"

class _Table:
    def __init__(self, table):
        self._table = table
        self._filters = []
        self._order   = None
        self._limit   = None
        self._select  = "*"

    def select(self, cols="*"):
        self._select = cols
        return self

    def insert(self, data):
        self._insert_data = data
        self._op = "insert"
        return self

    def update(self, data):
        self._update_data = data
        self._op = "update"
        return self

    def delete(self):
        self._op = "delete"
        return self

    def eq(self, col, val):
        self._filters.append(f"{col}=eq.{val}")
        return self

    def order(self, col, desc=False):
        self._order = f"{col}.{'desc' if desc else 'asc'}"
        return self

    def limit(self, n):
        self._limit = n
        return self

    def execute(self):
        op = getattr(self, "_op", "select")
        url = _url(self._table)
        params = {}

        if self._filters:
            for f in self._filters:
                k, v = f.split("=", 1)
                params[k] = v

        if op == "insert":
            r = _requests.post(url, json=self._insert_data,
                               headers={**_headers(), "Prefer": "return=minimal"},
                               timeout=10)
            r.raise_for_status()
            return type("R", (), {"data": []})()

        if op == "update":
            r = _requests.patch(url, json=self._update_data,
                                headers={**_headers(), "Prefer": "return=minimal"},
                                params=params, timeout=10)
            r.raise_for_status()
            return type("R", (), {"data": []})()

        if op == "delete":
            r = _requests.delete(url, headers=_headers(),
                                 params=params, timeout=10)
            r.raise_for_status()
            return type("R", (), {"data": []})()

        # select
        headers = {**_headers(), "Prefer": "return=representation"}
        headers["Accept"] = "application/json"
        if self._order:
            params["order"] = self._order
        if self._limit:
            params["limit"] = self._limit
        if self._select != "*":
            params["select"] = self._select
        r = _requests.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        return type("R", (), {"data": r.json()})()

class _Client:
    def table(self, name):
        return _Table(name)

def get_client():
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")
    if not url or not key:
        raise EnvironmentError("SUPABASE_URL and SUPABASE_KEY must be set")
    return _Client()