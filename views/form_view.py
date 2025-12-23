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

async def build_account_form_view(index, page, am, app_state, navigate_to, show_snack):
    is_edit = index is not None
    acc = am.accounts[index] if is_edit else None
    
    name_input = ft.TextField(label="Nazwa profilu (opcjonalne)", autofocus=True, value=acc.name if acc else "")
    user_input = ft.TextField(label="Numer karty / Login", value=acc.username if acc else "")
    pass_input = ft.TextField(label="Hasło", password=True, can_reveal_password=True, value=acc.password if acc else "")
    tenant_options = [ft.dropdown.Option(text=t["name"], key=str(i)) for i, t in enumerate(KNOWN_TENANTS) if t["base_url"]]
    tenant_dropdown = ft.Dropdown(label="Wybierz bibliotekę", options=tenant_options, value=str(acc.tenant_index) if acc else "0")

    async def save_click(e):
        if not user_input.value or not pass_input.value:
            show_snack("Wypełnij login i hasło!")
            return
        
        show_snack("Zapisywanie...")

        async def do_save():
            try:
                temp_acc = Account(name=name_input.value or "Temp", username=user_input.value, password=pass_input.value, tenant_index=int(tenant_dropdown.value))
                client = await get_client_for_account(temp_acc)
                final_name = name_input.value
                if not final_name:
                    user_info = await client.get_user_info()
                    final_name = user_info.display_name
                
                new_acc = Account(name=final_name, username=user_input.value, password=pass_input.value, tenant_index=int(tenant_dropdown.value))
                
                if is_edit:
                    await am.update_account(index, new_acc)
                else:
                    await am.add_account(new_acc)
                
                app_state.dashboard_data.clear()
                navigate_to("/")
            except Exception as ex:
                print(f"Error during save: {ex}")
                show_snack(f"Błąd: {str(ex)}", color=ft.Colors.RED)

        await do_save()

    async def delete_click(_):
        def close_dlg():
            page.dialog.open = False
            page.update()

        async def confirm(e):
            close_dlg()
            await asyncio.sleep(0.1)
            await am.remove_account(index)
            app_state.dashboard_data.clear()
            navigate_to("/")

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Usuń konto"),
            content=ft.Text(f"Usunąć profil {acc.name}?"),
            actions=[
                ft.TextButton("Nie", on_click=lambda _: close_dlg()),
                ft.TextButton("Tak", on_click=confirm, style=ft.ButtonStyle(color=ft.Colors.RED))
            ]
        )
        page.dialog = dlg
        dlg.open = True
        page.update()

    buttons = [ft.ElevatedButton("Zapisz", on_click=save_click, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE, width=float("inf"), height=45)]
    if is_edit:
        buttons.insert(0, ft.Row([
            ft.OutlinedButton("Stan konta", icon=ft.Icons.REFRESH, on_click=lambda _, idx=index: navigate_to(f"/status/{idx}"), expand=True),
            ft.OutlinedButton("Dane osobowe", icon=ft.Icons.PERSON_SEARCH, on_click=lambda _, idx=index: navigate_to(f"/details/{idx}"), expand=True)
        ]))
        buttons.append(ft.TextButton("Usuń konto", icon=ft.Icons.DELETE, icon_color=ft.Colors.RED, on_click=delete_click))
    
    return ft.View(
        f"/edit/{index}" if is_edit else "/add",
        [
            ft.AppBar(leading=ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: navigate_to("/settings")), title=ft.Text("Edycja" if is_edit else "Dodaj"), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST),
            ft.Container(padding=20, content=ft.Column([name_input, tenant_dropdown, user_input, pass_input, *buttons], spacing=15))
        ]
    )
