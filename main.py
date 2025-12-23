import asyncio
import flet as ft
from omnis.client import OmnisClient
from omnis.tenants import KNOWN_TENANTS
import json
from dataclasses import dataclass, asdict

# --- DATA MODELS ---

class Account:
    def __init__(self, name, username, password, tenant_index):
        self.name = name
        self.username = username
        self.password = password
        self.tenant_index = tenant_index

    def to_dict(self):
        return {
            "name": self.name,
            "username": self.username,
            "password": self.password,
            "tenant_index": self.tenant_index,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

class AccountManager:
    def __init__(self, page: ft.Page):
        self.page = page
        self.accounts = []

    async def load_accounts(self):
        try:
            data = await self.page.client_storage.get_async("accounts")
            if data:
                self.accounts = [Account.from_dict(a) for a in json.loads(data)]
        except Exception as e:
            print(f"Error loading accounts: {e}")

    async def save_accounts(self):
        data = json.dumps([a.to_dict() for a in self.accounts])
        await self.page.client_storage.set_async("accounts", data)

    async def add_account(self, account):
        self.accounts.append(account)
        await self.save_accounts()
    
    async def update_account(self, index, account):
        self.accounts[index] = account
        await self.save_accounts()

    async def remove_account(self, index):
        self.accounts.pop(index)
        await self.save_accounts()

# Global state
class AppState:
    def __init__(self):
        self.loans_cache = {}
        self.dashboard_data = {}
        self.visible_accounts = set()

app_state = AppState()

# --- HELPER FUNCTIONS ---

def mask_text(text, visible_start=2, visible_end=2):
    if not text: return "---"
    s_text = str(text).strip()
    if len(s_text) <= (visible_start + visible_end):
        return "*" * len(s_text)
    return s_text[:visible_start] + "*" * (len(s_text) - visible_start - visible_end) + s_text[-visible_end:]

def format_date(date_str):
    if not date_str or len(date_str) != 8: return date_str
    return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"

# --- MAIN APP ---

async def main(page: ft.Page):
    page.title = "Moje Biblioteki"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.primary_color = ft.Colors.BLUE_700
    
    am = AccountManager(page)
    await am.load_accounts()
    if not app_state.visible_accounts:
        app_state.visible_accounts = set(range(len(am.accounts)))

    def show_snack(text, color=None):
        page.snack_bar = ft.SnackBar(ft.Text(text), bgcolor=color)
        page.snack_bar.open = True
        page.update()

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

    def navigate_to(route):
        page.go(route)

    # --- VIEWS ---

    async def build_home_view():
        app_bar = ft.AppBar(title=ft.Text("Moje Książki"), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST, actions=[ft.IconButton(ft.Icons.SETTINGS, on_click=lambda _: navigate_to("/settings"))])
        if not am.accounts: return ft.View("/", [app_bar, ft.Container(content=ft.Text("Brak kont. Dodaj je w ustawieniach."), alignment=ft.alignment.center, expand=True)])

        summary_row = ft.Row(scroll=ft.ScrollMode.HIDDEN, spacing=10)
        summary_container = ft.Container(content=summary_row, padding=10, bgcolor=ft.Colors.BLUE_50, height=140)
        books_column = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)
        
        view = ft.View("/", [app_bar, ft.Column([summary_container, ft.Divider(height=1, color=ft.Colors.GREY_300), books_column], expand=True, spacing=0)])

        def render_books():
            books_column.controls.clear()
            grouped_loans = {}
            for idx in app_state.visible_accounts:
                if idx in app_state.dashboard_data:
                    account = am.accounts[idx]
                    _, loans = app_state.dashboard_data[idx]
                    for l_idx, loan in enumerate(loans):
                        unique_id = f"{idx}_{l_idx}"
                        group_name = loan.library_name + (f" - {loan.location_name}" if loan.location_name else "")
                        if group_name not in grouped_loans: grouped_loans[group_name] = []
                        grouped_loans[group_name].append((unique_id, loan, account.name))

            if not grouped_loans: books_column.controls.append(ft.Container(content=ft.Text("Brak książek do wyświetlenia.", size=16), alignment=ft.alignment.center, padding=20))
            else:
                for group_key in sorted(grouped_loans.keys()):
                    items = grouped_loans[group_key]
                    books_column.controls.append(ft.Container(content=ft.Row([ft.Icon(ft.Icons.LOCATION_ON, size=16, color=ft.Colors.BLUE_GREY_700), ft.Text(group_key, size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_700)]), padding=ft.padding.only(left=15, top=15, bottom=5), bgcolor=ft.Colors.GREY_100))
                    for uid, loan, acc_name in items:
                        is_overdue = "zaleg" in loan.status.lower()
                        books_column.controls.append(ft.Card(elevation=2, content=ft.ListTile(leading=ft.Icon(ft.Icons.BOOK, color=ft.Colors.RED if is_overdue else ft.Colors.BLUE_700), title=ft.Text(loan.title, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS, weight=ft.FontWeight.W_500), subtitle=ft.Column([ft.Text(f"Do: {loan.due_date}", color=ft.Colors.RED if is_overdue else ft.Colors.BLACK, weight=ft.FontWeight.BOLD), ft.Text(f"Konto: {acc_name}", size=12, italic=True)], spacing=2), on_click=lambda _, u=uid: navigate_to(f"/book/{u}"))))
            page.update()

        def render_summaries():
            summary_row.controls.clear()
            for i, acc in enumerate(am.accounts):
                if i in app_state.dashboard_data:
                    user_info, loans = app_state.dashboard_data[i]
                    has_fines = user_info.fines_amount > 0
                    card_content = ft.Container(width=160, padding=10, content=ft.Column([ft.Row([ft.Icon(ft.Icons.ACCOUNT_CIRCLE, color=ft.Colors.BLUE_700), ft.Text(acc.name, weight=ft.FontWeight.BOLD, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS, expand=True)]), ft.Text(f"Książki: {len(loans)}", size=13), ft.Text(f"Kary: {user_info.fines_amount} {user_info.fines_currency}", color=ft.Colors.RED if has_fines else ft.Colors.GREEN_700, weight=ft.FontWeight.BOLD, size=13), ft.Switch(label="Pokaż", value=(i in app_state.visible_accounts), on_change=lambda e, idx=i: (app_state.visible_accounts.add(idx) if e.control.value else app_state.visible_accounts.discard(idx)) or render_books(), active_color=ft.Colors.BLUE_700)], spacing=5))
                    summary_row.controls.append(ft.Card(content=card_content))
            page.update()

        async def fetch_data():
            if not app_state.dashboard_data: books_column.controls = [ft.Container(content=ft.ProgressRing(), alignment=ft.alignment.center, padding=20)]; page.update()
            app_state.loans_cache.clear(); app_state.dashboard_data.clear()
            async def process_account(idx, account):
                try:
                    client = await get_client_for_account(account); user_info = await client.get_user_info(); loans = await client.get_loans()
                    app_state.dashboard_data[idx] = (user_info, loans)
                    for l_idx, loan in enumerate(loans): app_state.loans_cache[f"{idx}_{l_idx}"] = (account, loan)
                except Exception as e: print(f"Error fetching {account.name}: {e}")
            await asyncio.gather(*[process_account(i, a) for i, a in enumerate(am.accounts)])
            if not app_state.visible_accounts: app_state.visible_accounts = set(range(len(am.accounts)))
            render_summaries(); render_books()
        asyncio.create_task(fetch_data())
        return view

    # --- ADD / EDIT VIEW ---
    async def build_account_form_view(index=None):
        is_edit = index is not None
        acc = am.accounts[index] if is_edit else None
        name_input = ft.TextField(label="Nazwa profilu (opcjonalne)", autofocus=True, value=acc.name if acc else "")
        user_input = ft.TextField(label="Numer karty / Login", value=acc.username if acc else "")
        pass_input = ft.TextField(label="Hasło", password=True, can_reveal_password=True, value=acc.password if acc else "")
        tenant_options = [ft.dropdown.Option(text=t["name"], key=str(i)) for i, t in enumerate(KNOWN_TENANTS) if t["base_url"]]
        tenant_dropdown = ft.Dropdown(label="Wybierz bibliotekę", options=tenant_options, value=str(acc.tenant_index) if acc else "0")

        # Generic function to open dialogs
        def open_dialog(dlg): page.open(dlg)
        def close_dialog(dlg): page.close(dlg)

        async def save_click(e):
            if not user_input.value or not pass_input.value: show_snack("Wypełnij login i hasło!"); return
            temp_acc = Account(name=name_input.value or "Temp", username=user_input.value, password=pass_input.value, tenant_index=int(tenant_dropdown.value))
            loading = ft.AlertDialog(title=ft.Text("Zapisywanie..."), content=ft.Container(height=50, content=ft.ProgressBar()), modal=True); open_dialog(loading)
            try:
                client = await get_client_for_account(temp_acc)
                final_name = name_input.value
                if not final_name: user_info = await client.get_user_info(); final_name = user_info.display_name
                new_acc = Account(name=final_name, username=user_input.value, password=pass_input.value, tenant_index=int(tenant_dropdown.value))
                if is_edit: await am.update_account(index, new_acc)
                else: await am.add_account(new_acc)
                close_dialog(loading); navigate_to("/settings")
            except Exception as ex: close_dialog(loading); show_snack(f"Błąd: {str(ex)}")

        async def check_status_click(e):
            t_acc = Account(name="Temp", username=user_input.value, password=pass_input.value, tenant_index=int(tenant_dropdown.value))
            loading = ft.AlertDialog(title=ft.Text("Pobieranie..."), content=ft.Container(height=50, content=ft.ProgressBar()), modal=True); open_dialog(loading)
            try:
                client = await get_client_for_account(t_acc); info = await client.get_user_info()
                close_dialog(loading)
                dlg = ft.AlertDialog(title=ft.Text(f"Stan konta: {info.display_name}"), content=ft.Column([ft.Row([ft.Icon(ft.Icons.MONETIZATION_ON, color=ft.Colors.AMBER), ft.Text(f"Kary: {info.fines_amount} {info.fines_currency}")]), ft.Row([ft.Icon(ft.Icons.BOOK), ft.Text(f"Wypożyczone: {info.loans_count}")]), ft.Row([ft.Icon(ft.Icons.BOOKMARK), ft.Text(f"Zamówione: {info.requests_count}")]), ], tight=True, spacing=10))
                dlg.actions = [ft.TextButton("OK", on_click=lambda _: close_dialog(dlg))]; open_dialog(dlg)
            except Exception as ex: close_dialog(loading); show_snack(f"Błąd: {str(ex)}")

        async def check_details_click(e):
            t_acc = Account(name="Temp", username=user_input.value, password=pass_input.value, tenant_index=int(tenant_dropdown.value))
            loading = ft.AlertDialog(title=ft.Text("Pobieranie danych..."), content=ft.Container(height=50, content=ft.ProgressBar()), modal=True); open_dialog(loading)
            try:
                client = await get_client_for_account(t_acc); details = await client.get_personal_settings()
                close_dialog(loading)
                
                # Initialize all variables
                full_name = "---"; email = "---"; phone = "---"; pesel = "---"; expiry = "---"; addr1 = "---"; addr2 = ""

                # Extract full name from user_details or patronstatus
                user_details_from_api = details.get("user_details", {})
                full_name = user_details_from_api.get("user_name", "---")
                if full_name == "---" or not full_name.strip(): # Fallback if user_name is empty or not found
                    patron_status_list = details.get("patronstatus", [])
                    if isinstance(patron_status_list, list) and patron_status_list:
                        for status_entry in patron_status_list:
                            if 'registration' in status_entry:
                                regs = status_entry['registration']
                                if isinstance(regs, list) and regs:
                                    for reg_entry in regs:
                                        if 'institution' in reg_entry:
                                            insts = reg_entry['institution']
                                            if isinstance(insts, list) and insts:
                                                for inst_entry in insts:
                                                    if 'user_name' in inst_entry and inst_entry['user_name']:
                                                        full_name = inst_entry['user_name']
                                                        break # Found it, break inner loop
                                                if full_name != "---": break # Found it, break middle loop
                                        if full_name != "---": break # Found it, break outer loop
                            if full_name != "---": break # Found it, break initial loop


                # Email
                email_data = details.get("email", {})
                if isinstance(email_data, dict): email = email_data.get("value", "---")
                elif isinstance(email_data, list) and email_data: email = email_data[0].get("value", "---")
                
                # Phone
                phone_data = details.get("telephone1", {})
                if isinstance(phone_data, dict): phone = phone_data.get("value", "---")
                
                # Address
                addr1 = details.get("address1", {}).get("value", "---")
                addr2 = details.get("address2", {}).get("value", "")
                
                # PESEL
                idents = details.get("identifiers", {}).get("identifier", [])
                if isinstance(idents, list):
                    for ide in idents: 
                        if "PESEL" in str(ide): pesel = str(ide).split(";")[-1]
                
                # Expiry Date
                patron_status = details.get("patronstatus", [])
                if isinstance(patron_status, list) and patron_status:
                    regs = patron_status[0].get("registration", [])
                    if isinstance(regs, list) and regs:
                        insts = regs[0].get("institution", [])
                        if isinstance(insts, list) and insts:
                            expiry = format_date(insts[0].get("patronexpirydate", ""))

                content = ft.Column([
                    ft.ListTile(leading=ft.Icon(ft.Icons.PERSON), title=ft.Text("Pełna nazwa"), subtitle=ft.Text(full_name)),
                    ft.ListTile(leading=ft.Icon(ft.Icons.FINGERPRINT), title=ft.Text("PESEL"), subtitle=ft.Text(mask_text(pesel, 2, 2))),
                    ft.ListTile(leading=ft.Icon(ft.Icons.EMAIL), title=ft.Text("E-mail"), subtitle=ft.Text(mask_text(email, 3, 4))),
                    ft.ListTile(leading=ft.Icon(ft.Icons.PHONE), title=ft.Text("Telefon"), subtitle=ft.Text(mask_text(phone, 3, 2))),
                    ft.ListTile(leading=ft.Icon(ft.Icons.HOME), title=ft.Text("Adres"), subtitle=ft.Text(f"{addr1}\n{addr2}".strip())),
                    ft.ListTile(leading=ft.Icon(ft.Icons.EVENT_AVAILABLE), title=ft.Text("Konto ważne do"), subtitle=ft.Text(expiry)),
                ], tight=True, scroll=ft.ScrollMode.AUTO)
                
                dlg = ft.AlertDialog(title=ft.Text("Szczegóły profilu"), content=content)
                dlg.actions = [ft.TextButton("Zamknij", on_click=lambda _: close_dialog(dlg))]
                open_dialog(dlg)
            except Exception as ex: close_dialog(loading); print(f"Err in check_details_click: {ex}"); show_snack(f"Błąd: {str(ex)}")

        async def delete_click(_):
            async def confirm(_): asyncio.create_task(am.remove_account(index)); close_dialog(dlg); navigate_to("/settings")
            dlg = ft.AlertDialog(title=ft.Text("Usuń konto"), content=ft.Text(f"Usunąć profil {acc.name}?")); dlg.actions = [ft.TextButton("Nie", on_click=lambda _: close_dialog(dlg)), ft.TextButton("Tak", on_click=confirm, style=ft.ButtonStyle(color=ft.Colors.RED))]; open_dialog(dlg)

        buttons = [ft.ElevatedButton("Zapisz", on_click=save_click, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE, width=float("inf"), height=45)]
        if is_edit:
            buttons.insert(0, ft.Row([ft.OutlinedButton("Stan konta", icon=ft.Icons.REFRESH, on_click=check_status_click, expand=True), ft.OutlinedButton("Dane osobowe", icon=ft.Icons.PERSON_SEARCH, on_click=check_details_click, expand=True)]))
            buttons.append(ft.TextButton("Usuń konto", icon=ft.Icons.DELETE, icon_color=ft.Colors.RED, on_click=delete_click))
        return ft.View(f"/edit/{index}" if is_edit else "/add", [ft.AppBar(leading=ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: navigate_to("/settings")), title=ft.Text("Edycja" if is_edit else "Dodaj"), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST), ft.Container(padding=20, content=ft.Column([name_input, tenant_dropdown, user_input, pass_input, *buttons], spacing=15))])

    # --- SETTINGS & BOOK DETAILS ---
    async def build_settings_view():
        account_list = ft.Column(spacing=10)
        for i, acc in enumerate(am.accounts):
            tenant_name = KNOWN_TENANTS[acc.tenant_index]["name"]
            account_list.controls.append(ft.Card(content=ft.ListTile(leading=ft.Icon(ft.Icons.ACCOUNT_CIRCLE, size=30, color=ft.Colors.BLUE_700), title=ft.Text(acc.name, weight=ft.FontWeight.BOLD), subtitle=ft.Text(tenant_name), trailing=ft.Icon(ft.Icons.EDIT, color=ft.Colors.GREY_500), on_click=lambda _, idx=i: navigate_to(f"/edit/{idx}"))))
        return ft.View("/settings", [ft.AppBar(leading=ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: navigate_to("/")), title=ft.Text("Zarządzanie kontami"), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST), ft.ListView(expand=True, padding=10, controls=[account_list, ft.Container(height=80)]), ft.FloatingActionButton(icon=ft.Icons.ADD, on_click=lambda _: navigate_to("/add"), text="Dodaj konto")])

    async def build_book_details_view(uid):
        if uid not in app_state.loans_cache: return ft.View("/error", [ft.AppBar(), ft.Text("Błąd: brak danych.")])
        account, loan = app_state.loans_cache[uid]
        full_location = loan.library_name + (f"\n{loan.location_name}" if loan.location_name else "") + (f" ({loan.sub_location_name})" if loan.sub_location_name else "")
        async def renew_click(_):
            loading = ft.AlertDialog(title=ft.Text("Przedłużanie..."), content=ft.Container(height=50, content=ft.ProgressBar()), modal=True)
            page.open(loading)
            try:
                client = await get_client_for_account(account); result = await client.renew_loan(loan.id); page.close(loading)
                msg = result.get("message", "Operacja wykonana.")
                res_dlg = ft.AlertDialog(title=ft.Text("Wynik"), content=ft.Text(str(msg)))
                res_dlg.actions = [ft.TextButton("OK", on_click=lambda _: page.close(res_dlg) or navigate_to("/"))]
                page.open(res_dlg)
            except Exception as ex: page.close(loading); show_snack(f"Błąd: {str(ex)}", color=ft.Colors.RED_400)
        return ft.View(f"/book/{uid}", [ft.AppBar(leading=ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: navigate_to("/")), title=ft.Text("Szczegóły"), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST), ft.Container(padding=20, content=ft.Column([ft.Icon(ft.Icons.BOOK, size=100, color=ft.Colors.BLUE_800), ft.Text(loan.title, size=22, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER), ft.Text(loan.author or "Brak autora", size=18, color=ft.Colors.GREY_700), ft.Divider(), ft.ListTile(leading=ft.Icon(ft.Icons.CALENDAR_MONTH), title=ft.Text("Termin zwrotu"), subtitle=ft.Text(loan.due_date, size=16, weight=ft.FontWeight.BOLD)), ft.ListTile(leading=ft.Icon(ft.Icons.TODAY), title=ft.Text("Wypożyczono"), subtitle=ft.Text(loan.loan_date)), ft.ListTile(leading=ft.Icon(ft.Icons.LOCATION_ON), title=ft.Text("Lokalizacja"), subtitle=ft.Text(full_location)), ft.ListTile(leading=ft.Icon(ft.Icons.QR_CODE), title=ft.Text("Kod kreskowy"), subtitle=ft.Text(loan.barcode)), ft.ListTile(leading=ft.Icon(ft.Icons.ACCOUNT_BOX), title=ft.Text("Konto"), subtitle=ft.Text(account.name)), ft.Divider(), ft.Container(content=ft.ElevatedButton("Przedłuż termin", icon=ft.Icons.UPDATE, width=200, bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE, on_click=renew_click, disabled=not loan.renewable), alignment=ft.alignment.center)], scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.CENTER))])

    async def view_handler(e):
        page.views.clear()
        route = page.route
        if route == "/": page.views.append(await build_home_view())
        elif route == "/settings": page.views.append(await build_settings_view())
        elif route == "/add": page.views.append(await build_account_form_view(None))
        elif route.startswith("/edit/"): page.views.append(await build_account_form_view(int(route.split("/")[-1])))
        elif route.startswith("/book/"): page.views.append(await build_book_details_view(route.split("/")[-1]))
        page.update()

    page.on_route_change = view_handler
    await view_handler(None)

ft.app(target=main)