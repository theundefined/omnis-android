import flet as ft
import asyncio
from datetime import datetime, timedelta

# Import Account model for type hinting


async def build_home_view(
    page, am, app_state, navigate_to, show_snack, get_data_for_account, log_debug
):
    # --- Local State for this View ---
    _dashboard_data = {}  # Dict to hold {account_idx: CachedData}
    loading_ring = ft.ProgressRing(visible=False, width=20, height=20, stroke_width=2)

    # --- Core Logic ---
    async def initial_load():
        """Load data for all accounts, primarily from cache."""
        nonlocal loading_ring
        loading_ring.visible = True
        if page.route == "/":
            page.update()

        tasks = [get_data_for_account(acc, force_refresh=False) for acc in am.accounts]
        results = await asyncio.gather(*tasks)

        for i, data in enumerate(results):
            if data:
                _dashboard_data[i] = data

        loading_ring.visible = False
        render_summaries()
        render_books()
        page.update()

    async def refresh_all_data(e=None):
        """Force refresh data for all visible accounts from the network."""
        nonlocal loading_ring
        loading_ring.visible = True
        page.update()

        tasks = [
            get_data_for_account(am.accounts[i], force_refresh=True)
            for i in app_state.visible_accounts
        ]
        results = await asyncio.gather(*tasks)

        for i, data in zip(app_state.visible_accounts, results):
            if data:
                _dashboard_data[i] = data

        loading_ring.visible = False
        render_summaries()
        render_books()
        page.update()
        show_snack("Dane zostały odświeżone.")

    # --- UI Rendering ---
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

    def render_books():
        books_column.controls.clear()
        grouped_loans = {}
        visible_data_exists = any(
            idx in _dashboard_data for idx in app_state.visible_accounts
        )

        if not visible_data_exists and am.accounts:
            books_column.controls.append(
                ft.Container(
                    content=ft.Text("Brak danych do wyświetlenia. Odśwież.", size=16),
                    alignment=ft.alignment.center,
                    padding=20,
                )
            )
        else:
            for idx in app_state.visible_accounts:
                if idx in _dashboard_data:
                    account = am.accounts[idx]
                    loans = _dashboard_data[idx].loans
                    for l_idx, loan in enumerate(loans):
                        unique_id = f"{idx}_{l_idx}"
                        group_name = loan.library_name + (
                            f" - {loan.location_name}" if loan.location_name else ""
                        )
                        if group_name not in grouped_loans:
                            grouped_loans[group_name] = []
                        grouped_loans[group_name].append(
                            (unique_id, loan, account.name)
                        )

            if not grouped_loans and am.accounts:
                books_column.controls.append(
                    ft.Container(
                        content=ft.Text("Brak wypożyczonych książek.", size=16),
                        alignment=ft.alignment.center,
                        padding=20,
                    )
                )
            elif not am.accounts:
                pass
            else:
                for group_key in sorted(grouped_loans.keys()):
                    items = grouped_loans[group_key]
                    books_column.controls.append(
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.Icon(
                                        ft.Icons.LOCATION_ON,
                                        size=16,
                                        color=ft.Colors.BLUE_GREY_700,
                                    ),
                                    ft.Text(
                                        group_key,
                                        size=14,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.BLUE_GREY_700,
                                    ),
                                ]
                            ),
                            padding=ft.padding.only(left=15, top=15, bottom=5),
                            bgcolor=ft.Colors.GREY_100,
                        )
                    )
                    for uid, loan, acc_name in items:
                        is_overdue = "zaleg" in loan.status.lower()
                        books_column.controls.append(
                            ft.Card(
                                elevation=2,
                                content=ft.ListTile(
                                    leading=ft.Icon(
                                        ft.Icons.BOOK,
                                        color=(
                                            ft.Colors.RED
                                            if is_overdue
                                            else ft.Colors.BLUE_700
                                        ),
                                    ),
                                    title=ft.Text(
                                        loan.title,
                                        max_lines=2,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                        weight=ft.FontWeight.W_500,
                                    ),
                                    subtitle=ft.Column(
                                        [
                                            ft.Text(
                                                f"Do: {loan.due_date}",
                                                color=(
                                                    ft.Colors.RED
                                                    if is_overdue
                                                    else ft.Colors.BLACK
                                                ),
                                                weight=ft.FontWeight.BOLD,
                                            ),
                                            ft.Text(
                                                f"Konto: {acc_name}",
                                                size=12,
                                                italic=True,
                                            ),
                                        ],
                                        spacing=2,
                                    ),
                                    on_click=lambda _, u=uid: navigate_to(f"/book/{u}"),
                                ),
                            )
                        )

        if page.route == "/":
            page.update()

    def render_summaries():
        summary_row.controls.clear()
        for i, acc in enumerate(am.accounts):
            card_content_controls = [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.ACCOUNT_CIRCLE, color=ft.Colors.BLUE_700),
                        ft.Text(
                            acc.name,
                            weight=ft.FontWeight.BOLD,
                            no_wrap=True,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            expand=True,
                        ),
                    ]
                ),
            ]
            if i in _dashboard_data:
                cached_data = _dashboard_data[i]
                user_info = cached_data.user_info
                loans = cached_data.loans
                has_fines = user_info.fines_amount > 0
                card_content_controls.extend(
                    [
                        ft.Text(f"Książki: {len(loans)}", size=13),
                        ft.Text(
                            f"Kary: {user_info.fines_amount} {user_info.fines_currency}",
                            color=ft.Colors.RED if has_fines else ft.Colors.GREEN_700,
                            weight=ft.FontWeight.BOLD,
                            size=13,
                        ),
                        ft.Text(
                            f"Aktual.: {get_time_ago(cached_data.last_updated)}",
                            size=11,
                            italic=True,
                            color=ft.Colors.BLUE_GREY_400,
                        ),
                    ]
                )
            else:
                card_content_controls.append(
                    ft.Text(
                        "Brak danych (odśwież)", size=12, color=ft.Colors.ORANGE_800
                    )
                )

            card_content_controls.append(
                ft.Switch(
                    label="Pokaż",
                    value=(i in app_state.visible_accounts),
                    on_change=lambda e, idx=i: (
                        app_state.visible_accounts.add(idx)
                        if e.control.value
                        else app_state.visible_accounts.discard(idx)
                    )
                    or render_books(),
                    active_color=ft.Colors.BLUE_700,
                    label_position=ft.LabelPosition.LEFT,
                )
            )
            card_content = ft.Container(
                width=160,
                padding=10,
                content=ft.Column(card_content_controls, spacing=5),
            )
            summary_row.controls.append(ft.Card(content=card_content))

        if page.route == "/":
            page.update()

    # --- Build View ---
    app_bar = ft.AppBar(
        title=ft.Text("Moje Książki"),
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        actions=[
            loading_ring,
            ft.IconButton(
                ft.Icons.REFRESH, on_click=refresh_all_data, tooltip="Odśwież dane"
            ),
            ft.IconButton(
                ft.Icons.SETTINGS, on_click=lambda _: navigate_to("/settings")
            ),
        ],
    )

    if not am.accounts:
        return ft.View(
            "/",
            [
                app_bar,
                ft.Container(
                    content=ft.Text("Brak kont. Dodaj je w ustawieniach."),
                    alignment=ft.alignment.center,
                    expand=True,
                ),
            ],
        )

    summary_row = ft.Row(scroll=ft.ScrollMode.HIDDEN, spacing=10)
    summary_container = ft.Container(
        content=summary_row, padding=10, bgcolor=ft.Colors.BLUE_50, height=180
    )  # Increased height
    books_column = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=0)

    view = ft.View(
        "/",
        [
            app_bar,
            ft.Column(
                [
                    summary_container,
                    ft.Divider(height=1, color=ft.Colors.GREY_300),
                    books_column,
                ],
                expand=True,
                spacing=0,
            ),
        ],
    )

    # Trigger the initial data load
    asyncio.create_task(initial_load())

    return view
