from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side

from database.schemas import UserRel


def convert_date(date: datetime) -> str:
    """Перевод даты в формат для вывода"""
    return date.date().strftime("%d.%m.%Y")

def generate_excel_file(data: list[UserRel]) -> None:
    """Генерация excel файла с пользователями"""
    wb = Workbook()

    # удаление лишнего листа
    del wb["Sheet"]

    # создание нового листа
    wb.create_sheet("Users", index=0)
    sheet = wb['Users']

    # настройка стилей
    font = Font(bold=True)
    align_center = Alignment(horizontal="center")
    border = Border(
        left=Side(border_style="thin", color='FF000000'),
        right=Side(border_style="thin", color='FF000000'),
        top=Side(border_style="thin", color='FF000000'),
        bottom=Side(border_style="thin", color='FF000000'),
    )

    # width
    sheet.column_dimensions["A"].width = 10
    sheet.column_dimensions["B"].width = 20
    sheet.column_dimensions["C"].width = 20
    sheet.column_dimensions["D"].width = 20
    sheet.column_dimensions["E"].width = 20
    sheet.column_dimensions["F"].width = 20
    sheet.column_dimensions["G"].width = 20
    sheet.column_dimensions["H"].width = 20
    sheet.column_dimensions["I"].width = 20
    sheet.column_dimensions["J"].width = 20
    sheet.column_dimensions["K"].width = 20
    sheet.column_dimensions["L"].width = 20

    # header
    sheet.append(
        [
            "№ п/п", "Database id","Телеграм id", "Username", "Имя", "Фамилия", "Телефон",
            "Подписка id", "Статус подписки", "Начало подписки", "Завершение подписки", "Профиль id",
        ]
    )

    # align
    sheet["A1"].alignment = align_center
    sheet["B1"].alignment = align_center
    sheet["C1"].alignment = align_center
    sheet["D1"].alignment = align_center
    sheet["E1"].alignment = align_center
    sheet["F1"].alignment = align_center
    sheet["G1"].alignment = align_center
    sheet["H1"].alignment = align_center
    sheet["I1"].alignment = align_center
    sheet["J1"].alignment = align_center
    sheet["K1"].alignment = align_center
    sheet["L1"].alignment = align_center

    # font
    sheet["A1"].font = font
    sheet["B1"].font = font
    sheet["C1"].font = font
    sheet["D1"].font = font
    sheet["E1"].font = font
    sheet["F1"].font = font
    sheet["G1"].font = font
    sheet["H1"].font = font
    sheet["I1"].font = font
    sheet["J1"].font = font
    sheet["K1"].font = font
    sheet["L1"].font = font

    # border
    sheet["A1"].border = border
    sheet["B1"].border = border
    sheet["C1"].border = border
    sheet["D1"].border = border
    sheet["E1"].border = border
    sheet["F1"].border = border
    sheet["G1"].border = border
    sheet["H1"].border = border
    sheet["I1"].border = border
    sheet["J1"].border = border
    sheet["K1"].border = border
    sheet["L1"].border = border

    for idx, user in enumerate(data, start=1):
        subscription = user.subscription[0]

        # Пропускаем пользователей с неактивной подпиской
        if not subscription.active and subscription.expire_date is None:
            continue

        is_active = "Активна" if subscription.active else "Неактивна"

        sheet.append([
            idx,
            user.id,
            user.tg_id,
            user.username,
            user.firstname,
            user.lastname,
            user.phone,
            subscription.id,
            is_active,
            subscription.start_date,
            subscription.expire_date,
            subscription.profile_id,
        ])

        # выравнивание колонки А по центру
        a_number = f"A{idx + 1}"
        sheet[a_number].alignment = align_center

        # границы ячеек
        b_number = f"B{idx + 1}"
        c_number = f"C{idx + 1}"
        d_number = f"D{idx + 1}"
        e_number = f"E{idx + 1}"
        f_number = f"F{idx + 1}"
        g_number = f"G{idx + 1}"
        h_number = f"H{idx + 1}"
        i_number = f"I{idx + 1}"
        j_number = f"J{idx + 1}"
        k_number = f"K{idx + 1}"
        l_number = f"L{idx + 1}"

        # выравнивание по центру
        sheet[b_number].alignment = align_center
        sheet[c_number].alignment = align_center
        sheet[d_number].alignment = align_center
        sheet[f_number].alignment = align_center
        sheet[e_number].alignment = align_center
        sheet[f_number].alignment = align_center
        sheet[g_number].alignment = align_center
        sheet[h_number].alignment = align_center
        sheet[i_number].alignment = align_center
        sheet[j_number].alignment = align_center
        sheet[k_number].alignment = align_center
        sheet[l_number].alignment = align_center

        sheet[a_number].border = border
        sheet[b_number].border = border
        sheet[c_number].border = border
        sheet[d_number].border = border
        sheet[e_number].border = border
        sheet[f_number].border = border
        sheet[g_number].border = border
        sheet[h_number].border = border
        sheet[i_number].border = border
        sheet[j_number].border = border
        sheet[k_number].border = border
        sheet[l_number].border = border

    wb.save("users/users.xlsx")
