import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests

# Часовий пояс Варшави
TIMEZONE = ZoneInfo("Europe/Warsaw")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
API_KEY = os.environ.get("FOOTBALL_API_KEY")

# ID Баварії в базі даних football-data.org — 5
BAYERN_ID = 5


def assess_importance(competition: str, stage: str, opponent: str) -> tuple[str, str]:
    """Визначає рівень небезпеки шуму та генерує розгорнутий коментар із причиною."""
    comp_lower = competition.lower()
    opp_lower = opponent.lower()

    # 1. Ліга Чемпіонів
    if "champions league" in comp_lower:
        if stage in ["QUARTER_FINALS", "SEMI_FINALS", "FINAL"]:
            return (
                "🚨 ЕКСТРЕМАЛЬНА",
                "Вирішальна стадія плей-оф Ліги Чемпіонів. Будь-яка помилка веде до вильоту з головного турніру Європи. Емоції та крики будуть на максимумі від першої до останньої хвилини.",
            )
        if stage in ["LAST_16", "ROUND_OF_16", "PLAYOFFS"]:
            return (
                "🔥 ВИСОКА",
                "Матч плей-оф Ліги Чемпіонів на виліт. Ціна кожного забитого або пропущеного м'яча величезна, напруга в кімнаті сусіда гарантована.",
            )
        return (
            "🔥 ВИСОКА",
            "Матч Ліги Чемпіонів. Найпрестижніший європейський турнір — такі ігри вболівальники Баварії ніколи не дивляться спокійно.",
        )

    # 2. Бундесліга (Чемпіонат Німеччини)
    if "bundesliga" in comp_lower:
        # Головне дербі Німеччини
        if "dortmund" in opp_lower:
            return (
                "⚡ ДУЖЕ ВИСОКА",
                "Принципове дербі («Der Klassiker») проти Дортмунда. Це історично найзапекліший суперник Баварії — крики лунатимуть на кожен спірний свисток судді.",
            )
        # Битва з прямими конкурентами за чемпіонство
        if any(team in opp_lower for team in ["leverkusen", "leipzig"]):
            return (
                "⚡ ДУЖЕ ВИСОКА",
                f"Матч проти прямого конкурента за золото ({opponent}). Поразка може коштувати першого місця в таблиці, тому реакція на гру буде бурхливою.",
            )
        # Рядовий матч ліги
        return (
            "🟡 СЕРЕДНЯ",
            "Звичайний тур чемпіонату проти суперника з середини таблиці. Якщо гра піде за планом, сусід кричатиме хіба що під час забитих голів.",
        )

    # 3. Кубок Німеччини (DFB-Pokal)
    if "pokal" in comp_lower:
        if stage in ["SEMI_FINALS", "FINAL"]:
            return (
                "🔥 ВИСОКА",
                "Вирішальний матч за національний кубок. Гра ведеться на виліт — у разі нічиєї можливі нервові додаткові тайми та серія пенальті.",
            )
        return (
            "🟡 СЕРЕДНЯ",
            "Матч Кубка Німеччини на виліт. Баварія часто є фаворитом, але сенсації в кубку трапляються регулярно, тож напруга все ж можлива.",
        )

    # 4. Товариські ігри та інші турніри
    return (
        "🟢 ПОМІРНА",
        "Рядовий або товариський матч без великого турнірного значення. Швидше за все, сусід дивитиметься гру спокійно або фоном.",
    )


def check_bayern_match():
    today_local = datetime.now(TIMEZONE).date()

    url = f"https://api.football-data.org/v4/teams/{BAYERN_ID}/matches?status=SCHEDULED"
    headers = {"X-Auth-Token": API_KEY}

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Помилка отримання даних: {response.status_code} - {response.text}")
        return

    data = response.json()
    matches = data.get("matches", [])

    for match in matches:
        utc_time_str = match["utcDate"].replace("Z", "+00:00")
        start_utc = datetime.fromisoformat(utc_time_str)

        # Конвертуємо час у місцевий (Варшава)
        start_local = start_utc.astimezone(TIMEZONE)

        if start_local.date() == today_local:
            # Орієнтовна тривалість ~1 год 55 хв
            end_local = start_local + timedelta(hours=1, minutes=55)

            home_team = match["homeTeam"]["name"]
            away_team = match["awayTeam"]["name"]
            opponent = away_team if match["homeTeam"]["id"] == BAYERN_ID else home_team
            is_home = "Вдома (Allianz Arena)" if match["homeTeam"]["id"] == BAYERN_ID else "На виїзді"

            competition = match.get("competition", {}).get("name", "Невідомий турнір")
            stage = match.get("stage", "")

            # Отримуємо рівень небезпеки та коментар
            level, comment = assess_importance(competition, stage, opponent)

            message = (
                f"⚠️ <b>УВАГА: СЬОГОДНІ ГРАЄ БАВАРІЯ!</b>\n\n"
                f"⚽ <b>Суперник:</b> {opponent}\n"
                f"🏆 <b>Турнір:</b> {competition}\n"
                f"🏟 <b>Локація:</b> {is_home}\n\n"
                f"⏰ <b>Початок гри:</b> {start_local.strftime('%H:%M')}\n"
                f"⏳ <b>Орієнтовне закінчення:</b> {end_local.strftime('%H:%M')}\n\n"
                f"📢 <b>Рівень небезпеки для вух:</b>\n"
                f"<b>{level}</b>\n"
                f"ℹ️ <i>{comment}</i>"
            )

            tg_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
            requests.post(tg_url, data=payload)
            print("Сповіщення успішно надіслано!")
            return

    print("Сьогодні матчів Баварії немає.")


if __name__ == "__main__":
    check_bayern_match()
