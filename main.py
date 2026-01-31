import flet as ft
from datetime import datetime
import os
from typing import Optional

# Import models, managers, and views
from app_state import AccountManager, Account, CachedData, app_state, LoanWithDetails
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
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"


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

    # --- Initial Loading Screen ---
    status_text = ft.Text(
        "Inicjalizacja aplikacji...", size=16, color=ft.Colors.GREY_700
    )
    page.add(
        ft.Container(
            content=ft.Column(
                [
                    ft.ProgressRing(),
                    ft.Container(height=20),
                    status_text,
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            alignment=ft.alignment.center,
            expand=True,
        )
    )
    page.update()

    # --- Create Cache Directories ---
    try:
        status_text.value = "Sprawdzanie katalogów..."
        page.update()
        os.makedirs("assets/cache/images", exist_ok=True)
    except Exception as e:
        log_debug(page, f"Error creating directories: {e}")

    # --- Load Accounts ---
    am = AccountManager(page)
    try:
        status_text.value = "Wczytywanie kont..."
        page.update()
        await am.load_accounts()
        if not app_state.visible_accounts:
            app_state.visible_accounts = set(range(len(am.accounts)))
    except Exception as e:
        status_text.value = f"Błąd wczytywania kont: {e}"
        status_text.color = ft.Colors.RED
        log_debug(page, f"Error loading accounts: {e}")
        page.update()
        await asyncio.sleep(2)  # Give user time to read error

    async def download_and_cache_image(client: OmnisClient, cover_url: str, mmsid: str):
        """
        Downloads and caches a cover image if it doesn't already exist and is a valid image.
        """
        image_path = f"assets/cache/images/{mmsid}.jpg"
        if os.path.exists(image_path):
            return  # Image already cached

        log_debug(page, f"Downloading cover for MMSID {mmsid} from {cover_url}")
        try:
            response = await client.client.get(cover_url)
            response.raise_for_status()

            # Check if the image is a real image (larger than 1KB)
            if len(response.content) > 1024:
                with open(image_path, "wb") as f:
                    f.write(response.content)
                log_debug(page, f"Successfully cached cover for MMSID {mmsid}")
            else:
                log_debug(
                    page,
                    f"Downloaded cover for MMSID {mmsid} is too small ({len(response.content)} bytes). Skipping cache.",
                )

        except Exception as e:
            log_debug(page, f"Failed to download or save cover for MMSID {mmsid}: {e}")

    async def get_data_for_account(
        account: Account, force_refresh: bool = False
    ) -> Optional[CachedData]:
        """
        Main function to get data for an account.
        It orchestrates caching, network fetching, and enrichment.
        """
        log_debug(
            page,
            f"get_data_for_account called for '{account.name}', force_refresh={force_refresh}",
        )

        # --- Step 1: Try to load from cache ---
        if not force_refresh:
            cached_data = am.load_account_data_from_cache(account)
            if cached_data:
                log_debug(page, f"Cache HIT for '{account.name}'")

                # --- Step 1a: Check for missing book details in cached data ---
                if any(loan.book_details is None for loan in cached_data.loans):
                    log_debug(
                        page,
                        f"Found loans with missing details in cache for '{account.name}'. Enriching...",
                    )
                    show_snack(
                        f"Pobieranie szczegółów dla {account.name}...",
                        ft.Colors.BLUE_GREY,
                    )
                    client = None
                    try:
                        tenant = KNOWN_TENANTS[account.tenant_index]
                        client = OmnisClient(base_url=tenant["base_url"])
                        await client.login(
                            username=account.username,
                            password=account.password,
                            institution=tenant["institution"],
                            view=tenant["view"],
                        )
                        for loan in cached_data.loans:
                            if loan.book_details is None:
                                loan.book_details = await client.get_record_details(
                                    loan.mmsid
                                )
                                if loan.book_details and loan.book_details.cover_url:
                                    await download_and_cache_image(
                                        client, loan.book_details.cover_url, loan.mmsid
                                    )

                        am.save_account_data_to_cache(
                            account,
                            cached_data.user_info,
                            cached_data.loans,
                            cached_data.personal_settings,
                        )
                        log_debug(page, "Successfully enriched and re-cached data.")
                    except Exception as e:
                        log_debug(page, f"Error enriching cached data: {e}")
                    finally:
                        if client:
                            await client.close()

                return cached_data

        # --- Step 2: Fetch from network if cache miss or force_refresh ---
        log_debug(
            page,
            f"Cache MISS for '{account.name}' or force_refresh=True. Fetching from network.",
        )
        show_snack(f"Pobieranie danych dla: {account.name}...", ft.Colors.BLUE_GREY)
        client = None
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
            base_loans = await client.get_loans()
            personal_settings = await client.get_personal_settings()

            # --- DEBUG: Log initial loan data ---
            log_debug(page, "--- RAW LOAN DATA ---")
            for loan in base_loans:
                log_debug(page, f"  - Title: {loan.title}, MMSID: {loan.mmsid}")
            log_debug(page, "---------------------")

            loans_with_details = [
                LoanWithDetails(**loan.model_dump(by_alias=True)) for loan in base_loans
            ]

            # --- Step 2a: Enrich loans with BookDetails and cache covers ---
            log_debug(
                page, f"Enriching {len(loans_with_details)} loans with book details..."
            )
            for loan in loans_with_details:
                try:
                    loan.book_details = await client.get_record_details(loan.mmsid)
                    # --- DEBUG: Log enriched data ---
                    log_debug(page, f"--- ENRICHED DATA for '{loan.title}' ---")
                    log_debug(page, f"  - Details: {loan.book_details}")
                    log_debug(page, "-----------------------------------")
                    if loan.book_details and loan.book_details.cover_url:
                        await download_and_cache_image(
                            client, loan.book_details.cover_url, loan.mmsid
                        )
                except Exception as ex:
                    log_debug(
                        page,
                        f"Could not fetch book details for MMSID {loan.mmsid}: {ex}",
                    )
                    loan.book_details = None

            # --- Step 3: Save to cache ---
            am.save_account_data_to_cache(
                account, user_info, loans_with_details, personal_settings
            )
            log_debug(
                page, f"Network fetch SUCCESS for '{account.name}' and saved to cache."
            )
            show_snack(f"Dane dla {account.name} zostały odświeżone.", ft.Colors.GREEN)

            return am.load_account_data_from_cache(account)

        except Exception as e:
            error_message = f"Błąd logowania dla {account.name}: {e}"
            log_debug(page, error_message)
            show_snack(error_message, ft.Colors.RED_400)
            return None
        finally:
            if client:
                await client.close()

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
            "log_debug": log_debug,  # Pass the logger
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
            page.views.append(
                await build_account_form_view(index=None, **base_common_args)
            )
        elif route.startswith("/edit/"):
            index = int(route.split("/")[-1])
            page.views.append(
                await build_account_form_view(index=index, **base_common_args)
            )
        elif route.startswith("/book/"):
            uid = route.split("/")[-1]
            page.views.append(
                await build_book_details_view(uid=uid, **data_common_args)
            )
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


ft.app(target=main, assets_dir="assets")
