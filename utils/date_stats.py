import calendar
import datetime

def calcular_pascoa(ano):
    a = ano % 19
    b = ano // 100
    c = ano % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    L = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * L) // 451
    mes = (h + L - 7 * m + 114) // 31
    dia = ((h + L - 7 * m + 114) % 31) + 1
    return datetime.date(ano, mes, dia)

def obter_estatisticas_mes(ano, mes):
    cal = calendar.monthcalendar(ano, mes)
    pascoa = calcular_pascoa(ano)
    feriados = [
        datetime.date(ano, 1, 1),
        pascoa - datetime.timedelta(days=47),
        pascoa - datetime.timedelta(days=2),
        datetime.date(ano, 4, 21),
        datetime.date(ano, 5, 1),
        pascoa + datetime.timedelta(days=60),
        datetime.date(ano, 9, 7),
        datetime.date(ano, 10, 12),
        datetime.date(ano, 11, 2),
        datetime.date(ano, 11, 15),
        datetime.date(ano, 11, 20),
        datetime.date(ano, 12, 25),
    ]
    feriados_mes = [f for f in feriados if f.month == mes and f.year == ano]

    dias_seg_sex_total = 0
    dias_seg_sab_total = 0
    feriados_seg_sex = 0
    feriados_seg_sab = 0
    lista_feriados_detalhes = []

    for semana in cal:
        for i in range(7):
            dia = semana[i]
            if dia != 0:
                data_atual = datetime.date(ano, mes, dia)
                wd = data_atual.weekday()
                if wd < 5:
                    dias_seg_sex_total += 1
                    dias_seg_sab_total += 1
                elif wd == 5:
                    dias_seg_sab_total += 1

                if data_atual in feriados_mes:
                    if wd < 5:
                        feriados_seg_sex += 1
                        feriados_seg_sab += 1
                        lista_feriados_detalhes.append((data_atual, "Seg a Sex"))
                    elif wd == 5:
                        feriados_seg_sab += 1
                        lista_feriados_detalhes.append((data_atual, "Sábado"))

    return {
        "seg_sex_total": dias_seg_sex_total,
        "seg_sex_feriados": feriados_seg_sex,
        "seg_sex_uteis": dias_seg_sex_total - feriados_seg_sex,
        "seg_sab_total": dias_seg_sab_total,
        "seg_sab_feriados": feriados_seg_sab,
        "seg_sab_uteis": dias_seg_sab_total - feriados_seg_sab,
        "feriados_detalhes": lista_feriados_detalhes
    }
