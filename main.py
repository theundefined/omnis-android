import flet as ft
import asyncio

# Import models, managers, and views from the new modules
from app_state import AccountManager, app_state, Account
from views.home_view import build_home_view
from views.settings_view import build_settings_view
from views.form_view import build_account_form_view
from views.book_view import build_book_details_view
from views.status_view import build_status_view
from views.details_view import build_account_details_view

async def main(page: ft.Page):
    page.title = "Moje Biblioteki"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.primary_color = ft.Colors.BLUE_700
    
    # Initialize the account manager
    am = AccountManager(page)
    await am.load_accounts()
    if not app_state.visible_accounts:
        app_state.visible_accounts = set(range(len(am.accounts)))

    # Define navigation and snackbar functions to pass to views
    def navigate_to(route):
        page.go(route)

    def show_snack(text, color=None):
        page.snack_bar = ft.SnackBar(ft.Text(text), bgcolor=color)
        page.snack_bar.open = True
        page.update()

    # Define the view handler (router)
    async def view_handler(e):
        page.views.clear()
        route = page.route

        # Pass necessary objects and functions to the view builders
        common_args = {
            "page": page,
            "am": am,
            "app_state": app_state,
            "navigate_to": navigate_to,
            "show_snack": show_snack
        }

        if route == "/": 
            page.views.append(await build_home_view(**common_args))
        elif route == "/settings": 
            page.views.append(await build_settings_view(**common_args))
        elif route == "/add": 
            page.views.append(await build_account_form_view(index=None, **common_args))
        elif route.startswith("/edit/"):
            index = int(route.split("/")[-1])
            page.views.append(await build_account_form_view(index=index, **common_args))
        elif route.startswith("/book/"):
            uid = route.split("/")[-1]
            page.views.append(await build_book_details_view(uid=uid, **common_args))
        elif route.startswith("/status/"):
            index = int(route.split("/")[-1])
            page.views.append(await build_status_view(index=index, **common_args))
        elif route.startswith("/details/"):
            index = int(route.split("/")[-1])
            page.views.append(await build_account_details_view(index=index, **common_args))
        
        page.update()

    page.on_route_change = view_handler
    await view_handler(None)

ft.app(target=main)
