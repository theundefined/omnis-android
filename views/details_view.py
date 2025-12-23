import flet as ft
import asyncio
from app_state import Account, mask_text, format_date
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

async def build_account_details_view(index, page, am, app_state, navigate_to, show_snack):
    acc = am.accounts[index]
    content_area = ft.Column(
        controls=[ft.ProgressRing()],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        expand=True
    )

    async def fetch_details():
        try:
            client = await get_client_for_account(acc)
            details = await client.get_personal_settings()

            full_name, email, phone, pesel, expiry, addr1, addr2 = "---", "---", "---", "---", "---", "---", ""
            
            user_details_from_api = details.get("user_details", {})
            full_name = user_details_from_api.get("user_name", "---")
            if full_name == "---" or not full_name.strip():
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
                                                    break
                                            if full_name != "---": break
                                    if full_name != "---": break
                        if full_name != "---": break
            
            email_data = details.get("email", {})
            if isinstance(email_data, dict): email = email_data.get("value", "---")
            elif isinstance(email_data, list) and email_data: email = email_data[0].get("value", "---")
            
            phone_data = details.get("telephone1", {})
            if isinstance(phone_data, dict): phone = phone_data.get("value", "---")
            
            addr1 = details.get("address1", {}).get("value", "---")
            addr2 = details.get("address2", {}).get("value", "")
            
            idents = details.get("identifiers", {}).get("identifier", [])
            if isinstance(idents, list):
                for ide in idents: 
                    if "PESEL" in str(ide): pesel = str(ide).split(";")[-1]
            
            patron_status = details.get("patronstatus", [])
            if isinstance(patron_status, list) and patron_status:
                regs = patron_status[0].get("registration", [])
                if isinstance(regs, list) and regs:
                    insts = regs[0].get("institution", [])
                    if isinstance(insts, list) and insts:
                        expiry = format_date(insts[0].get("patronexpirydate", ""))
            
            content_area.controls.clear()
            content_area.controls.extend([
                ft.ListTile(leading=ft.Icon(ft.Icons.PERSON), title=ft.Text("Pełna nazwa"), subtitle=ft.Text(full_name)),
                ft.ListTile(leading=ft.Icon(ft.Icons.FINGERPRINT), title=ft.Text("PESEL"), subtitle=ft.Text(mask_text(pesel, 2, 2))),
                ft.ListTile(leading=ft.Icon(ft.Icons.EMAIL), title=ft.Text("E-mail"), subtitle=ft.Text(mask_text(email, 3, 4))),
                ft.ListTile(leading=ft.Icon(ft.Icons.PHONE), title=ft.Text("Telefon"), subtitle=ft.Text(mask_text(phone, 3, 2))),
                ft.ListTile(leading=ft.Icon(ft.Icons.HOME), title=ft.Text("Adres"), subtitle=ft.Text(f"{addr1}\n{addr2}".strip())),
                ft.ListTile(leading=ft.Icon(ft.Icons.EVENT_AVAILABLE), title=ft.Text("Konto ważne do"), subtitle=ft.Text(expiry)),
            ])
        except Exception as e:
            content_area.controls.clear()
            content_area.controls.append(ft.Text(f"Błąd pobierania danych: {e}", color=ft.Colors.RED))
        page.update()

    page.run_task(fetch_details)

    return ft.View(
        f"/details/{index}",
        [
            ft.AppBar(
                leading=ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: navigate_to(f"/edit/{index}")),
                title=ft.Text(f"Dane osobowe: {acc.name}"),
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST
            ),
            ft.Container(content=content_area, padding=20, expand=True)
        ]
    )
