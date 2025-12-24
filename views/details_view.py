import flet as ft
from app_state import mask_text, format_date
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
from app_state import mask_text, format_date
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

async def build_account_details_view(
    index, page, am, app_state, navigate_to, show_snack, get_data_for_account, log_debug
):
    acc = am.accounts[index]
    log_debug(page, f"Building details view for account '{acc.name}' (index: {index})")
    
    content_area = ft.Column(
        controls=[ft.ProgressRing()],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        expand=True,
    )

    async def load_and_populate():
        log_debug(page, "Details view: starting data fetch.")
        cached_data = await get_data_for_account(acc)
        log_debug(page, f"Details view: data fetch complete. Data is {'present' if cached_data else 'missing'}.")

        content_area.controls.clear()

        if not cached_data or not cached_data.personal_settings:
            content_area.controls.append(
                ft.Text("Nie udało się pobrać szczegółowych danych konta.", color=ft.Colors.RED)
            )
            log_debug(page, "Details view: personal_settings missing, showing error.")
            page.update()
            return

        try:
            details = cached_data.personal_settings
            
            # --- Parsing Logic ---
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
            
            # --- Display Logic ---
            content_area.controls.extend([
                ft.ListTile(leading=ft.Icon(ft.Icons.PERSON), title=ft.Text("Pełna nazwa"), subtitle=ft.Text(full_name)),
                ft.ListTile(leading=ft.Icon(ft.Icons.FINGERPRINT), title=ft.Text("PESEL"), subtitle=ft.Text(mask_text(pesel, 2, 2))),
                ft.ListTile(leading=ft.Icon(ft.Icons.EMAIL), title=ft.Text("E-mail"), subtitle=ft.Text(mask_text(email, 3, 4))),
                ft.ListTile(leading=ft.Icon(ft.Icons.PHONE), title=ft.Text("Telefon"), subtitle=ft.Text(mask_text(phone, 3, 2))),
                ft.ListTile(leading=ft.Icon(ft.Icons.HOME), title=ft.Text("Adres"), subtitle=ft.Text(f"{addr1}\n{addr2}".strip())),
                ft.ListTile(leading=ft.Icon(ft.Icons.EVENT_AVAILABLE), title=ft.Text("Konto ważne do"), subtitle=ft.Text(expiry)),
                ft.Divider(height=10),
                ft.Text(f"Dane z: {get_time_ago(cached_data.last_updated)}", italic=True, color=ft.Colors.BLUE_GREY_400, text_align=ft.TextAlign.CENTER),
            ])
            log_debug(page, "Details view: Populated controls with data.")
        except Exception as e:
            error_msg = f"Błąd przetwarzania danych: {e}"
            content_area.controls.append(ft.Text(error_msg, color=ft.Colors.RED))
            log_debug(page, f"Details view: Exception during processing: {error_msg}")

        log_debug(page, "Details view: Calling page.update().")
        page.update()

    # --- View construction ---
    view = ft.View(
        f"/details/{index}",
        [
            ft.AppBar(
                leading=ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: navigate_to("/")),
                title=ft.Text(f"Dane osobowe: {acc.name}"),
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            ),
            ft.Container(content=content_area, padding=20, expand=True),
        ],
    )

    asyncio.create_task(load_and_populate())
    log_debug(page, "Details view: Created background task to load and populate.")

    return view
