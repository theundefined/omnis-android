import flet as ft
import asyncio
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

async def build_home_view(page, am, app_state, navigate_to, show_snack):
    async def refresh_data(force: bool = False):
        if not force and app_state.dashboard_data:
            return

        books_column.controls = [ft.Container(content=ft.ProgressRing(), alignment=ft.alignment.center, padding=20)]
        summary_row.controls.clear()
        if page.route == "/": page.update()

        if force:
            app_state.loans_cache.clear()
            app_state.dashboard_data.clear()

        async def process_account(idx, account):
            try:
                client = await get_client_for_account(account)
                user_info = await client.get_user_info()
                loans = await client.get_loans()
                app_state.dashboard_data[idx] = (user_info, loans)
                for l_idx, loan in enumerate(loans):
                    app_state.loans_cache[f"{idx}_{l_idx}"] = (account, loan)
            except Exception as e:
                print(f"Error fetching {account.name}: {e}")
        
        await asyncio.gather(*[process_account(i, a) for i, a in enumerate(am.accounts)])

        if not app_state.visible_accounts:
            app_state.visible_accounts = set(range(len(am.accounts)))
        
        render_summaries()
        render_books()

    def render_books():
        books_column.controls.clear()
        grouped_loans = {}
        visible_data_exists = any(idx in app_state.dashboard_data for idx in app_state.visible_accounts)

        if not visible_data_exists and am.accounts:
            books_column.controls.append(ft.Container(content=ft.Text("Brak danych do wyświetlenia. Odśwież.", size=16), alignment=ft.alignment.center, padding=20))
        else:
            for idx in app_state.visible_accounts:
                if idx in app_state.dashboard_data:
                    account = am.accounts[idx]
                    _, loans = app_state.dashboard_data[idx]
                    for l_idx, loan in enumerate(loans):
                        unique_id = f"{idx}_{l_idx}"
                        group_name = loan.library_name + (f" - {loan.location_name}" if loan.location_name else "")
                        if group_name not in grouped_loans: grouped_loans[group_name] = []
                        grouped_loans[group_name].append((unique_id, loan, account.name))

            if not grouped_loans and am.accounts:
                books_column.controls.append(ft.Container(content=ft.Text("Brak wypożyczonych książek.", size=16), alignment=ft.alignment.center, padding=20))
            elif not am.accounts:
                pass # Handled by the main view
            else:
                for group_key in sorted(grouped_loans.keys()):
                    items = grouped_loans[group_key]
                    books_column.controls.append(ft.Container(content=ft.Row([ft.Icon(ft.Icons.LOCATION_ON, size=16, color=ft.Colors.BLUE_GREY_700), ft.Text(group_key, size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_700)]), padding=ft.padding.only(left=15, top=15, bottom=5), bgcolor=ft.Colors.GREY_100))
                    for uid, loan, acc_name in items:
                        is_overdue = "zaleg" in loan.status.lower()
                        books_column.controls.append(ft.Card(elevation=2, content=ft.ListTile(leading=ft.Icon(ft.Icons.BOOK, color=ft.Colors.RED if is_overdue else ft.Colors.BLUE_700), title=ft.Text(loan.title, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS, weight=ft.FontWeight.W_500), subtitle=ft.Column([ft.Text(f"Do: {loan.due_date}", color=ft.Colors.RED if is_overdue else ft.Colors.BLACK, weight=ft.FontWeight.BOLD), ft.Text(f"Konto: {acc_name}", size=12, italic=True)], spacing=2), on_click=lambda _, u=uid: navigate_to(f"/book/{u}"))))
        
        if page.route == "/": page.update()

    def render_summaries():
        summary_row.controls.clear()
        for i, acc in enumerate(am.accounts):
            if i in app_state.dashboard_data:
                user_info, loans = app_state.dashboard_data[i]
                has_fines = user_info.fines_amount > 0
                card_content = ft.Container(width=160, padding=10, content=ft.Column([
                    ft.Row([ft.Icon(ft.Icons.ACCOUNT_CIRCLE, color=ft.Colors.BLUE_700), ft.Text(acc.name, weight=ft.FontWeight.BOLD, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS, expand=True)]),
                    ft.Text(f"Książki: {len(loans)}", size=13),
                    ft.Text(f"Kary: {user_info.fines_amount} {user_info.fines_currency}", color=ft.Colors.RED if has_fines else ft.Colors.GREEN_700, weight=ft.FontWeight.BOLD, size=13),
                    ft.Switch(
                        label="Pokaż",
                        value=(i in app_state.visible_accounts),
                        on_change=lambda e, idx=i: (app_state.visible_accounts.add(idx) if e.control.value else app_state.visible_accounts.discard(idx)) or render_books(),
                        active_color=ft.Colors.BLUE_700,
                        label_position=ft.LabelPosition.LEFT
                    )], spacing=5))
                summary_row.controls.append(ft.Card(content=card_content))
        if page.route == "/": page.update()

    async def refresh_button_click(e):
        await refresh_data(force=True)

    app_bar = ft.AppBar(
        title=ft.Text("Moje Książki"),
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        actions=[
            ft.IconButton(ft.Icons.REFRESH, on_click=refresh_button_click, tooltip="Odśwież dane"),
            ft.IconButton(ft.Icons.SETTINGS, on_click=lambda _: navigate_to("/settings")),
        ]
    )

    if not am.accounts:
        return ft.View("/", [app_bar, ft.Container(content=ft.Text("Brak kont. Dodaj je w ustawieniach."), alignment=ft.alignment.center, expand=True)])

    summary_row = ft.Row(scroll=ft.ScrollMode.HIDDEN, spacing=10)
    summary_container = ft.Container(content=summary_row, padding=10, bgcolor=ft.Colors.BLUE_50, height=160)
    books_column = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)
    
    view = ft.View("/", [app_bar, ft.Column([summary_container, ft.Divider(height=1, color=ft.Colors.GREY_300), books_column], expand=True, spacing=0)])

    if app_state.dashboard_data:
        render_summaries()
        render_books()

    asyncio.create_task(refresh_data())
    return view
