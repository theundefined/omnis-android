import flet as ft
from omnis.tenants import KNOWN_TENANTS


async def build_settings_view(page, am, app_state, navigate_to, show_snack, log_debug):
    account_list = ft.Column(spacing=10)
    for i, acc in enumerate(am.accounts):
        tenant_name = KNOWN_TENANTS[acc.tenant_index]["name"]
        account_list.controls.append(
            ft.Card(
                content=ft.ListTile(
                    leading=ft.Icon(
                        ft.Icons.ACCOUNT_CIRCLE, size=30, color=ft.Colors.BLUE_700
                    ),
                    title=ft.Text(acc.name, weight=ft.FontWeight.BOLD),
                    subtitle=ft.Text(tenant_name),
                    trailing=ft.Icon(ft.Icons.EDIT, color=ft.Colors.GREY_500),
                    on_click=lambda _, idx=i: navigate_to(f"/edit/{idx}"),
                )
            )
        )

    return ft.View(
        "/settings",
        [
            ft.AppBar(
                leading=ft.IconButton(
                    ft.Icons.ARROW_BACK, on_click=lambda _: navigate_to("/")
                ),
                title=ft.Text("Zarządzanie kontami"),
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            ),
            ft.ListView(
                expand=True,
                padding=10,
                controls=[account_list, ft.Container(height=80)],
            ),
            ft.FloatingActionButton(
                icon=ft.Icons.ADD,
                on_click=lambda _: navigate_to("/add"),
                text="Dodaj konto",
            ),
        ],
    )
