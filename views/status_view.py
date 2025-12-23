import flet as ft
import asyncio
from app_state import Account
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

async def build_status_view(index, page, am, app_state, navigate_to, show_snack):
    acc = am.accounts[index]
    content_area = ft.Column(
        controls=[ft.ProgressRing()],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        expand=True
    )
    
    async def fetch_status():
        try:
            client = await get_client_for_account(acc)
            info = await client.get_user_info()
            content_area.controls.clear()
            content_area.controls.extend([
                ft.ListTile(leading=ft.Icon(ft.Icons.PERSON_PIN_CIRCLE, size=40), title=ft.Text(info.display_name, size=20, weight=ft.FontWeight.BOLD)),
                ft.Divider(height=10),
                ft.ListTile(leading=ft.Icon(ft.Icons.MONETIZATION_ON, color=ft.Colors.AMBER), title=ft.Text("Kary"), subtitle=ft.Text(f"{info.fines_amount} {info.fines_currency}", size=18)),
                ft.ListTile(leading=ft.Icon(ft.Icons.BOOK), title=ft.Text("Wypożyczone"), subtitle=ft.Text(str(info.loans_count), size=18)),
                ft.ListTile(leading=ft.Icon(ft.Icons.BOOKMARK), title=ft.Text("Zamówione"), subtitle=ft.Text(str(info.requests_count), size=18)),
            ])
        except Exception as e:
            content_area.controls.clear()
            content_area.controls.append(ft.Text(f"Błąd pobierania danych: {e}", color=ft.Colors.RED))
        page.update()

    # Use page.run_task to run the async function in the background
    page.run_task(fetch_status)

    return ft.View(
        f"/status/{index}",
        [
            ft.AppBar(
                leading=ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: navigate_to(f"/edit/{index}")),
                title=ft.Text(f"Stan konta: {acc.name}"),
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST
            ),
            ft.Container(content=content_area, padding=20, expand=True)
        ]
    )
