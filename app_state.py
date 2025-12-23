import flet as ft
import json
from dataclasses import dataclass

# --- DATA MODELS ---
class Account:
    def __init__(self, name, username, password, tenant_index):
        self.name = name
        self.username = username
        self.password = password
        self.tenant_index = tenant_index

    def to_dict(self):
        return {
            "name": self.name,
            "username": self.username,
            "password": self.password,
            "tenant_index": self.tenant_index,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

class AccountManager:
    def __init__(self, page: ft.Page):
        self.page = page
        self.accounts = []

    async def load_accounts(self):
        try:
            data = await self.page.client_storage.get_async("accounts")
            if data:
                self.accounts = [Account.from_dict(a) for a in json.loads(data)]
        except Exception as e:
            print(f"Error loading accounts: {e}")

    async def save_accounts(self):
        data = json.dumps([a.to_dict() for a in self.accounts])
        await self.page.client_storage.set_async("accounts", data)

    async def add_account(self, account):
        self.accounts.append(account)
        await self.save_accounts()
    
    async def update_account(self, index, account):
        self.accounts[index] = account
        await self.save_accounts()

    async def remove_account(self, index):
        self.accounts.pop(index)
        await self.save_accounts()

# Global state
class AppState:
    def __init__(self):
        self.loans_cache = {}
        self.dashboard_data = {}
        self.visible_accounts = set()

app_state = AppState()

# --- HELPER FUNCTIONS ---
def mask_text(text, visible_start=2, visible_end=2):
    if not text: return "---"
    s_text = str(text).strip()
    if len(s_text) <= (visible_start + visible_end):
        return "*" * len(s_text)
    return s_text[:visible_start] + "*" * (len(s_text) - visible_start - visible_end) + s_text[-visible_end:]

def format_date(date_str):
    if not date_str or len(date_str) != 8: return date_str
    return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
