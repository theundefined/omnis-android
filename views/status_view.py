import flet as ft
from datetime import datetime, timedelta


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

async def build_status_view(
    index, page, am, app_state, navigate_to, show_snack, get_data_for_account, log_debug
):
    acc = am.accounts[index]
    log_debug(page, f"Building status view for account '{acc.name}' (index: {index})")

    content_area = ft.Column(
        controls=[ft.ProgressRing()],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        expand=True,
    )

    async def load_and_populate():
        log_debug(page, "Status view: starting data fetch.")
        cached_data = await get_data_for_account(acc)
        log_debug(page, f"Status view: data fetch complete. Data is {'present' if cached_data else 'missing'}.")
        
        content_area.controls.clear()

        if cached_data:
            info = cached_data.user_info
            content_area.controls.extend(
                [
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.PERSON_PIN_CIRCLE, size=40),
                        title=ft.Text(info.display_name, size=20, weight=ft.FontWeight.BOLD),
                    ),
                    ft.Divider(height=10),
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.MONETIZATION_ON, color=ft.Colors.AMBER),
                        title=ft.Text("Kary"),
                        subtitle=ft.Text(f"{info.fines_amount} {info.fines_currency}", size=18),
                    ),
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.BOOK),
                        title=ft.Text("Wypożyczone"),
                        subtitle=ft.Text(str(info.loans_count), size=18),
                    ),
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.BOOKMARK),
                        title=ft.Text("Zamówione"),
                        subtitle=ft.Text(str(info.requests_count), size=18),
                    ),
                    ft.Divider(height=10),
                    ft.Text(
                        f"Dane z: {get_time_ago(cached_data.last_updated)}",
                        italic=True,
                        color=ft.Colors.BLUE_GREY_400,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ]
            )
            log_debug(page, "Status view: Populated controls with data.")
        else:
            content_area.controls.append(
                ft.Text(
                    "Nie udało się pobrać danych konta. Sprawdź połączenie z internetem i spróbuj odświeżyć na ekranie głównym.",
                    color=ft.Colors.RED,
                )
            )
            log_debug(page, "Status view: Displayed error message.")

        log_debug(page, "Status view: Calling page.update().")
        page.update()

    # --- View construction ---
    view = ft.View(
        f"/status/{index}",
        [
            ft.AppBar(
                leading=ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: navigate_to("/")),
                title=ft.Text(f"Stan konta: {acc.name}"),
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            ),
            ft.Container(content=content_area, padding=20, expand=True),
        ],
    )
    
    # Run the data loading as a background task
    asyncio.create_task(load_and_populate())
    log_debug(page, "Status view: Created background task to load and populate.")

    return view
