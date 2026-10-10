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


def send_tg_message(text: str):
    """Відправляє повідомлення в Telegram."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"Помилка надсилання в Telegram: {e}")


def assess_importance(competition: str, stage: str, opponent: str) -> tuple[str, str]:
    """Визначає рівень небезпеки шуму та генерує розгорнутий коментар із поясненням."""
    comp_lower = competition.lower()
    opp_lower = opponent.lower()

    # 1. Ліга Чемпіонів
    if "champions league" in comp_lower:
        if stage in ["QUARTER_FINALS", "SEMI_FINALS", "FINAL"]:
            return (
                "🚨 ЕКСТРЕМАЛЬНА",
                "Вирішальна стадія плей-оф Ліги Чемпіонів. Будь-яка помилка веде до вильоту з турніру. Емоції та крики сусіда гарантовані весь матч.",
            )
        if stage in ["LAST_16", "ROUND_OF_16", "PLAYOFFS"]:
            return (
                "🔥 ВИСОКА",
                "Матч плей-оф Ліги Чемпіонів на виліт. Ціна кожного голу величезна, напруга в кімнаті сусіда гарантована.",
            )
        return (
            "🔥 ВИСОКА",
            "Матч Ліги Чемпіонів. Найпрестижніший європейський турнір сезону — такі ігри фанати дивляться з особливим азартом.",
        )

    # 2. Бундесліга (Чемпіонат Німеччини)
    if "bundesliga" in comp_lower:
        if "dortmund" in opp_lower:
            return (
                "⚡ ДУЖЕ ВИСОКА",
                "Принципове дербі («Der Klassiker») проти Дортмунда. Найзапекліший історичний суперник — крики лунатимуть на кожен спірний свисток.",
            )
        if any(team in opp_lower for team in ["leverkusen", "leipzig"]):
            return (
                "⚡ ДУЖЕ ВИСОКА",
                f"Матч проти прямого конкурента ({opponent}) за перше місце в турнірній таблиці.",
            )
        return (
            "🟡 СЕРЕДНЯ",
            "Звичайний тур чемпіонату Німеччини проти середняка. Сусід кричатиме переважно під час забитих голів.",
        )

    # 3. Кубок Німеччини (DFB-Pokal)
    if "pokal" in comp_lower:
        return (
            "🔥 ВИСОКА",
            "Матч Кубка Німеччини на виліт. Будь-яка осічка означає кінець боротьби за трофей, можливі додаткові тайми чи пенальті.",
        )

    # 4. Товариські ігри та інші турніри
    return (
        "🟢 ПОМІРНА",
        "Рядовий або товариський матч без критичного турнірного тиску.",
    )


def check_bayern_match():
    today_local = datetime.now(TIMEZONE).date()

    # Запитуємо всі матчі клубу без жорстких фільтрів статусу в URL
    url = f"https://api.football-data.org/v4/teams/{BAYERN_ID}/matches"
    headers = {"X-Auth-Token": API_KEY}

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Помилка API: {response.status_code} - {response.text}")
            send_tg_message(f"⚠️ Помилка Football API (Код {response.status_code}).")
            return

        matches = response.json().get("matches", [])

        # Діагностичний вивід у логи GitHub Actions
        valid_statuses = ["TIMED", "SCHEDULED", "IN_PLAY", "PAUSED"]
        upcoming = [m for m in matches if m.get("status") in valid_statuses]
        print(f"=== Усього майбутніх матчів у базі: {len(upcoming)} ===")
        for m in upcoming[:5]:
            print(
                f"-> {m.get('utcDate')} | "
                f"{m.get('homeTeam', {}).get('name')} vs {m.get('awayTeam', {}).get('name')} | "
                f"Статус: {m.get('status')} | "
                f"Турнір: {m.get('competition', {}).get('name')}"
            )
        print("==========================================================")

        for match in matches:
            utc_time_str = match["utcDate"].replace("Z", "+00:00")
            start_utc = datetime.fromisoformat(utc_time_str)
            start_local = start_utc.astimezone(TIMEZONE)

            # Перевіряємо збіг за сьогоднішньою датою у Варшаві
            if start_local.date() == today_local:
                end_local = start_local + timedelta(hours=1, minutes=55)

                home_team = match["homeTeam"]["name"]
                away_team = match["awayTeam"]["name"]
                opponent = away_team if match["homeTeam"]["id"] == BAYERN_ID else home_team
                is_home = "Вдома (Allianz Arena)" if match["homeTeam"]["id"] == BAYERN_ID else "На виїзді"

                competition = match.get("competition", {}).get("name", "Невідомий турнір")
                stage = match.get("stage", "")

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

                send_tg_message(message)
                print("Сповіщення про сьогоднішній матч успішно надіслано в Telegram!")
                return

        print("Сьогодні матчів Баварії немає.")

    except Exception as e:
        print(f"Виникла помилка під час виконання: {e}")


if __name__ == "__main__":
    check_bayern_match()
