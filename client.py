"""
Lightweight Python client for the Code Review Environment HTTP API.

Usage:
    from client import CodeReviewClient

    client = CodeReviewClient("http://localhost:7860")
    obs = client.reset()
    result = client.step("Use enumerate instead of range(len(...))")
    print(result)
"""

import requests
from typing import Any


class CodeReviewClient:
    def __init__(self, base_url: str = "http://localhost:7860"):
        self.base_url = base_url.rstrip("/")

    def reset(self) -> dict[str, Any]:
        resp = requests.post(f"{self.base_url}/reset")
        resp.raise_for_status()
        return resp.json()

    def step(self, review: str) -> dict[str, Any]:
        resp = requests.post(f"{self.base_url}/step", json={"review": review})
        resp.raise_for_status()
        return resp.json()

    def state(self) -> dict[str, Any]:
        resp = requests.get(f"{self.base_url}/state")
        resp.raise_for_status()
        return resp.json()
