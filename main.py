import flet as ft
from datetime import datetime
import asyncio
from typing import Optional

# Import models, managers, and views
from app_state import AccountManager, Account, CachedData, app_state
from views.home_view import build_home_view
from views.settings_view import build_settings_view
from views.form_view import build_account_form_view
from views.book_view import build_book_details_view
from views.status_view import build_status_view
from views.details_view import build_account_details_view

# Import Omnis client and config
from omnis import OmnisClient
from omnis.tenants import KNOWN_TENANTS


# --- DEBUG ---
DEBUG = False

def log_debug(page: ft.Page, message: str):
    if DEBUG:
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[DEBUG {timestamp}] {message}")
        # Optionally, could add to an on-screen console
        # if page.route == "/debug":
        #     page.controls.append(ft.Text(f"[{timestamp}] {message}"))


async def main(page: ft.Page):
    page.title = "Moje Biblioteki"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.primary_color = ft.Colors.BLUE_700

    am = AccountManager(page)
    await am.load_accounts()
    if not app_state.visible_accounts:
        app_state.visible_accounts = set(range(len(am.accounts)))

    async def get_data_for_account(
        account: Account, force_refresh: bool = False
    ) -> Optional[CachedData]:
        """
        Main function to get data for an account.
        It orchestrates caching and network fetching.
        """
        log_debug(page, f"get_data_for_account called for '{account.name}', force_refresh={force_refresh}")
        if not force_refresh:
            cached_data = am.load_account_data_from_cache(account)
            if cached_data:
                log_debug(page, f"Cache HIT for '{account.name}'")
                return cached_data
        
        log_debug(page, f"Cache MISS for '{account.name}'. Fetching from network.")
        show_snack(f"Pobieranie danych dla: {account.name}...", ft.Colors.BLUE_GREY)
        try:
            tenant = KNOWN_TENANTS[account.tenant_index]
            client = OmnisClient(base_url=tenant["base_url"])

            await client.login(
                username=account.username,
                password=account.password,
                institution=tenant["institution"],
                view=tenant["view"],
            )
            
            user_info = await client.get_user_info()
            loans = await client.get_loans()
            personal_settings = await client.get_personal_settings()

            am.save_account_data_to_cache(
                account, user_info, loans, personal_settings
            )
            log_debug(page, f"Network fetch SUCCESS for '{account.name}' and saved to cache.")
            show_snack(f"Dane dla {account.name} zostały odświeżone.", ft.Colors.GREEN)
            
            return am.load_account_data_from_cache(account)

        except Exception as e:
            error_message = f"Błąd logowania dla {account.name}: {e}"
            log_debug(page, error_message)
            show_snack(error_message, ft.Colors.ERROR)
            return None

    def navigate_to(route):
        log_debug(page, f"Navigating to: {route}")
        page.go(route)

    def show_snack(text, color=None):
        page.snack_bar = ft.SnackBar(ft.Text(text), bgcolor=color)
        page.snack_bar.open = True
        page.update()

    async def view_handler(e):
        log_debug(page, f"View handler triggered for route: {page.route}")
        page.views.clear()
        route = page.route

        base_common_args = {
            "page": page,
            "am": am,
            "app_state": app_state,
            "navigate_to": navigate_to,
            "show_snack": show_snack,
            "log_debug": log_debug, # Pass the logger
        }

        data_common_args = {
            **base_common_args,
            "get_data_for_account": get_data_for_account,
        }

        if route == "/":
            page.views.append(await build_home_view(**data_common_args))
        elif route == "/settings":
            page.views.append(await build_settings_view(**base_common_args))
        elif route == "/add":
            page.views.append(await build_account_form_view(index=None, **base_common_args))
        elif route.startswith("/edit/"):
            index = int(route.split("/")[-1])
            page.views.append(await build_account_form_view(index=index, **base_common_args))
        elif route.startswith("/book/"):
            uid = route.split("/")[-1]
            page.views.append(await build_book_details_view(uid=uid, **data_common_args))
        elif route.startswith("/status/"):
            index = int(route.split("/")[-1])
            page.views.append(await build_status_view(index=index, **data_common_args))
        elif route.startswith("/details/"):
            index = int(route.split("/")[-1])
            page.views.append(
                await build_account_details_view(index=index, **data_common_args)
            )

        page.update()

    page.on_route_change = view_handler
    # Running asyncio.to_thread in the main thread is not supported.
    # We need to run the app in a dedicated thread.
    await view_handler(None)


ft.app(target=main)
