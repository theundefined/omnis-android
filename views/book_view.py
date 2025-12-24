import flet as ft
import asyncio
from datetime import datetime, timedelta

# Import the client directly for action-based network calls
from omnis import OmnisClient
from omnis.tenants import KNOWN_TENANTS


def get_time_ago(dt: datetime) -> str:
    """Returns a human-readable string of how long ago a datetime was."""
    now = datetime.now()
    diff = now - dt

    if diff < timedelta(minutes=1):
        return "przed chwilą"
    elif diff < timedelta(hours=1):
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes} min temu"
    elif diff < timedelta(days=1):
        hours = int(diff.total_seconds() / 3600)
        return f"{hours} godz. temu"
    else:
        days = diff.days
        return f"{days} dni temu"


import flet as ft
import asyncio
from datetime import datetime, timedelta

# Import the client directly for action-based network calls
from omnis import OmnisClient
from omnis.tenants import KNOWN_TENANTS


def get_time_ago(dt: datetime) -> str:
    """Returns a human-readable string of how long ago a datetime was."""
    now = datetime.now()
    diff = now - dt
    
    if diff < timedelta(minutes=1):
        return "przed chwilą"
    elif diff < timedelta(hours=1):
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes} min temu"
    elif diff < timedelta(days=1):
        hours = int(diff.total_seconds() / 3600)
        return f"{hours} godz. temu"
    else:
        days = diff.days
        return f"{days} dni temu"


async def build_book_details_view(
    uid, page, am, app_state, navigate_to, show_snack, get_data_for_account, log_debug
):
    log_debug(page, f"Building book details view for uid: {uid}")

    content_area = ft.Column(
        [ft.ProgressRing()], 
        expand=True, 
        alignment=ft.MainAxisAlignment.CENTER, 
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )

    async def load_and_populate():
        log_debug(page, "Book view: starting data processing.")
        try:
            acc_idx_str, loan_idx_str = uid.split("_")
            acc_idx, loan_idx = int(acc_idx_str), int(loan_idx_str)
        except (ValueError, IndexError):
            content_area.controls.clear()
            content_area.controls.append(ft.Text("Błąd: Nieprawidłowy identyfikator książki.", color=ft.Colors.RED))
            log_debug(page, f"Book view: Invalid UID format: {uid}")
            page.update()
            return

        if acc_idx >= len(am.accounts):
            content_area.controls.clear()
            content_area.controls.append(ft.Text("Błąd: Nieprawidłowy identyfikator konta.", color=ft.Colors.RED))
            log_debug(page, f"Book view: Invalid account index {acc_idx} for UID {uid}")
            page.update()
            return

        account = am.accounts[acc_idx]
        log_debug(page, f"Book view: fetching data for account '{account.name}'")
        cached_data = await get_data_for_account(account)

        if not cached_data or loan_idx >= len(cached_data.loans):
            content_area.controls.clear()
            content_area.controls.append(ft.Text("Błąd: Nie znaleziono książki w pamięci podręcznej.", color=ft.Colors.RED))
            log_debug(page, f"Book view: Loan index {loan_idx} out of bounds or no cache for UID {uid}")
            page.update()
            return
        
        loan = cached_data.loans[loan_idx]
        log_debug(page, f"Book view: Found loan '{loan.title}'")

        async def renew_click(_):
            log_debug(page, f"Book view: 'Renew' clicked for loan id {loan.id}")
            show_snack("Przedłużanie...")
            try:
                tenant = KNOWN_TENANTS[account.tenant_index]
                client = OmnisClient(base_url=tenant["base_url"])
                await client.login(
                    username=account.username,
                    password=account.password,
                    institution=tenant["institution"],
                    view=tenant["view"],
                )
                result = await client.renew_loan(loan.id)
                msg = result.get("message", "Operacja wykonana.")
                log_debug(page, f"Book view: Renewal successful: {msg}")
                show_snack(msg, color=ft.Colors.GREEN)
                await get_data_for_account(account, force_refresh=True)
                navigate_to("/")
            except Exception as ex:
                error_msg = f"Błąd przedłużania: {str(ex)}"
                log_debug(page, f"Book view: Renewal failed: {error_msg}")
                show_snack(error_msg, color=ft.Colors.RED_400)

        full_location = loan.library_name + (f"\n{loan.location_name}" if loan.location_name else "") + (f" ({loan.sub_location_name})" if loan.sub_location_name else "")
        
        content_area.controls.clear()
        content_area.controls.extend(
            [
                ft.Icon(ft.Icons.BOOK, size=100, color=ft.Colors.BLUE_800),
                ft.Text(loan.title, size=22, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                ft.Text(loan.author or "Brak autora", size=18, color=ft.Colors.GREY_700),
                ft.Divider(),
                ft.ListTile(leading=ft.Icon(ft.Icons.CALENDAR_MONTH), title=ft.Text("Termin zwrotu"), subtitle=ft.Text(loan.due_date, size=16, weight=ft.FontWeight.BOLD)),
                ft.ListTile(leading=ft.Icon(ft.Icons.TODAY), title=ft.Text("Wypożyczono"), subtitle=ft.Text(loan.loan_date)),
                ft.ListTile(leading=ft.Icon(ft.Icons.LOCATION_ON), title=ft.Text("Lokalizacja"), subtitle=ft.Text(full_location)),
                ft.ListTile(leading=ft.Icon(ft.Icons.QR_CODE), title=ft.Text("Kod kreskowy"), subtitle=ft.Text(loan.barcode)),
                ft.ListTile(leading=ft.Icon(ft.Icons.ACCOUNT_BOX), title=ft.Text("Konto"), subtitle=ft.Text(account.name)),
                ft.Text(f"Dane z: {get_time_ago(cached_data.last_updated)}", italic=True, color=ft.Colors.BLUE_GREY_400, text_align=ft.TextAlign.CENTER),
                ft.Divider(),
                ft.Container(
                    content=ft.ElevatedButton(
                        "Przedłuż termin",
                        icon=ft.Icons.UPDATE,
                        width=200,
                        bgcolor=ft.Colors.GREEN_700,
                        color=ft.Colors.WHITE,
                        on_click=renew_click,
                        disabled=not loan.renewable,
                    ),
                    alignment=ft.alignment.center,
                ),
            ]
        )
        log_debug(page, "Book view: Populated controls, calling page.update().")
        page.update()

    view = ft.View(
        f"/book/{uid}",
        [
            ft.AppBar(
                leading=ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: navigate_to("/")),
                title=ft.Text("Szczegóły"),
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            ),
            content_area
        ],
    )

    asyncio.create_task(load_and_populate())
    log_debug(page, "Book view: Created background task to load and populate.")

    return view
