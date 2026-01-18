import flet as ft
import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

# Import the actual Pydantic models from the library
try:
    from omnis import UserInfo, Loan, BookDetails
except ImportError:
    # Create dummy classes if omnis-py is not installed for local testing
    class UserInfo(BaseModel):
        pass

    class Loan(BaseModel):
        pass

    class BookDetails(BaseModel):
        pass


# --- CONSTANTS ---
CACHE_DIR = "storage/cache"


# --- HELPER FUNCTIONS ---
def slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    import re

    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    value = re.sub(r"[-\s]+", "-", value)
    return value


def get_account_cache_path(account_name: str) -> str:
    """Generates the full path for an account's cache file."""
    return os.path.join(CACHE_DIR, f"{slugify(account_name)}.json")


def mask_text(text, visible_start=2, visible_end=2):
    if not text:
        return "---"
    s_text = str(text).strip()
    if len(s_text) <= (visible_start + visible_end):
        return "*" * len(s_text)
    return (
        s_text[:visible_start]
        + "*" * (len(s_text) - visible_start - visible_end)
        + s_text[-visible_end:]
    )


def format_date(date_str):
    if not date_str or len(date_str) != 8:
        return date_str
    return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"


class LoanWithDetails(Loan):
    """A Loan with optional, lazily-loaded book details."""

    book_details: Optional[BookDetails] = None

    class Config:
        extra = "allow"  # Allow adding attributes not defined in the model


@dataclass
class CachedData:
    """A wrapper for all cached data for a single account."""

    last_updated: datetime
    user_info: UserInfo
    loans: List[LoanWithDetails]
    personal_settings: Dict[str, Any]


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
        os.makedirs(CACHE_DIR, exist_ok=True)

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
        if index < len(self.accounts):
            account_to_remove = self.accounts[index]
            cache_path = get_account_cache_path(account_to_remove.name)
            if os.path.exists(cache_path):
                os.remove(cache_path)
        self.accounts.pop(index)
        await self.save_accounts()

    def save_account_data_to_cache(
        self,
        account: Account,
        user_info: UserInfo,
        loans: List[LoanWithDetails],
        personal_settings: Dict[str, Any],
    ):
        """Serializes all account data and saves it to a file-based cache."""
        cache_path = get_account_cache_path(account.name)
        try:
            full_cache_content = {
                "last_updated": datetime.now().isoformat(),
                "user_info": user_info.model_dump(by_alias=True),
                "loans": [loan.model_dump(by_alias=True) for loan in loans],
                "personal_settings": personal_settings,
            }
            with open(cache_path, "w") as f:
                json.dump(full_cache_content, f, indent=4)
            print(f"Successfully cached data for {account.name}")
        except Exception as e:
            print(f"Error saving cache for {account.name}: {e}")

    def load_account_data_from_cache(self, account: Account) -> Optional[CachedData]:
        """Loads and deserializes all account data from the file-based cache."""
        cache_path = get_account_cache_path(account.name)
        if not os.path.exists(cache_path):
            return None

        try:
            with open(cache_path, "r") as f:
                cached_content = json.load(f)

            last_updated = datetime.fromisoformat(cached_content["last_updated"])
            personal_settings = cached_content.get("personal_settings", {})

            # This logic supports both Pydantic v1 and v2
            pydantic_v2 = hasattr(UserInfo, "model_validate")

            if pydantic_v2:
                user_info = UserInfo.model_validate(cached_content["user_info"])
                loans = [
                    LoanWithDetails.model_validate(loan_data)
                    for loan_data in cached_content.get("loans", [])
                ]
            else:  # Fallback for Pydantic v1
                user_info = UserInfo.parse_obj(cached_content["user_info"])
                loans = [
                    LoanWithDetails.parse_obj(loan_data)
                    for loan_data in cached_content.get("loans", [])
                ]

            print(f"Successfully loaded data from cache for {account.name}")
            return CachedData(
                last_updated=last_updated,
                user_info=user_info,
                loans=loans,
                personal_settings=personal_settings,
            )
        except Exception as e:
            print(f"Error loading cache for {account.name}: {e}")
            return None


# Global state
class AppState:
    def __init__(self):
        # These caches are now for transient UI state, not for fetched data
        self.loans_cache = {}
        self.dashboard_data = {}
        self.visible_accounts = set()


app_state = AppState()
