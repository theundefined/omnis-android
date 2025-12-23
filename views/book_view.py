import flet as ft
from app_state import app_state, Account
from omnis.client import OmnisClient
from omnis.tenants import KNOWN_TENANTS

async def get_client_for_account(account: Account):
    tenant = KNOWN_TENANTS[account.tenant_index]
    client = OmnisClient(base_url=tenant["base_url"])
    await client.login(
        username=account.username,
        password=account.password,
        institution=tenant["institution"],
        view=tenant["view"]
    )
    return client

async def build_book_details_view(uid, page, am, app_state, navigate_to, show_snack):
    if uid not in app_state.loans_cache:
        return ft.View("/error", [ft.AppBar(title=ft.Text("Błąd")), ft.Text("Błąd: Nie znaleziono książki w pamięci podręcznej.")])
    
    account, loan = app_state.loans_cache[uid]
    full_location = loan.library_name + (f"\n{loan.location_name}" if loan.location_name else "") + (f" ({loan.sub_location_name})" if loan.sub_location_name else "")
    
    async def renew_click(_):
        show_snack("Przedłużanie...")
        try:
            client = await get_client_for_account(account)
            result = await client.renew_loan(loan.id)
            msg = result.get("message", "Operacja wykonana.")
            show_snack(msg, color=ft.Colors.GREEN)
            app_state.dashboard_data.clear() # Force refresh
            navigate_to("/")
        except Exception as ex:
            show_snack(f"Błąd: {str(ex)}", color=ft.Colors.RED_400)

    return ft.View(
        f"/book/{uid}",
        [
            ft.AppBar(
                leading=ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: navigate_to("/")),
                title=ft.Text("Szczegóły"),
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST
            ),
            ft.Container(
                padding=20,
                content=ft.Column(
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
                        ft.Divider(),
                        ft.Container(
                            content=ft.ElevatedButton(
                                "Przedłuż termin",
                                icon=ft.Icons.UPDATE,
                                width=200,
                                bgcolor=ft.Colors.GREEN_700,
                                color=ft.Colors.WHITE,
                                on_click=renew_click,
                                disabled=not loan.renewable
                            ),
                            alignment=ft.alignment.center
                        )
                    ],
                    scroll=ft.ScrollMode.AUTO,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER
                )
            )
        ]
    )
