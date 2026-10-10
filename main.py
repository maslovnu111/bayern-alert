import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests

TIMEZONE = ZoneInfo("Europe/Warsaw")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
API_KEY = os.environ.get("FOOTBALL_API_KEY")

BAYERN_ID = 5


def send_tg_message(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    requests.post(url, data=payload)


def assess_importance(competition: str, stage: str, opponent: str) -> tuple[str, str]:
    comp_lower = competition.lower()
    opp_lower = opponent.lower()

    if "champions league" in comp_lower:
        if stage in ["QUARTER_FINALS", "SEMI_FINALS", "FINAL"]:
            return ("🚨 ЕКСТРЕМАЛЬНА", "Вирішальна стадія Ліги Чемпіонів. Емоції та крики на максимумі.")
        return ("🔥 ВИСОКА", "Матч Ліги Чемпіонів. Один із найважливіших турнірів сезону.")

    if "bundesliga" in comp_lower:
        if "dortmund" in opp_lower:
            return ("⚡ ДУЖЕ ВИСОКА", "Принципове дербі («Der Klassiker») проти Дортмунда. Максимальна напруга.")
        if any(team in opp_lower for team in ["leverkusen", "leipzig"]):
            return ("⚡ ДУЖЕ ВИСОКА", f"Матч проти прямого конкурента ({opponent}) за золото.")
        return ("🟡 СЕРЕДНЯ", "Звичайний тур чемпіонату. Крики лунатимуть переважно під час забитих голів.")

    return ("🟢 ПОМІРНА", "Матч без критичного турнірного тиску.")


def check_bayern_match():
    today_local = datetime.now(TIMEZONE).date()

    # Запитуємо всі найближчі матчі команди
    url = f"https://api.football-data.org/v4/teams/{BAYERN_ID}/matches"
    headers = {"X-Auth-Token": API_KEY}

    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            send_tg_message(f"⚠️ Помилка Football API: {response.status_code}")
            return

        matches = response.json().get("matches", [])
        valid_statuses = ["SCHEDULED", "TIMED", "IN_PLAY", "PAUSED"]
        
        # Відбираємо майбутні/актуальні матчі
        upcoming = [m for m in matches if m.get("status") in valid_statuses]

        match_today = None
        for match in upcoming:
            utc_str = match["utcDate"].replace("Z", "+00:00")
            start_local = datetime.fromisoformat(utc_str).astimezone(TIMEZONE)

            if start_local.date() == today_local:
                match_today = (match, start_local)
                break

        if match_today:
            match, start_local = match_today
            end_local = start_local + timedelta(hours=1, minutes=55)

            home = match["homeTeam"]["name"]
            away = match["awayTeam"]["name"]
            opponent = away if match["homeTeam"]["id"] == BAYERN_ID else home
            is_home = "Вдома (Allianz Arena)" if match["homeTeam"]["id"] == BAYERN_ID else "На виїзді"
            competition = match.get("competition", {}).get("name", "Турнір")
            stage = match.get("stage", "")

            level, comment = assess_importance(competition, stage, opponent)

            msg = (
                f"⚠️ <b>УВАГА: СЬОГОДНІ ГРАЄ БАВАРІЯ!</b>\n\n"
                f"⚽ <b>Суперник:</b> {opponent}\n"
                f"🏆 <b>Турнір:</b> {competition}\n"
                f"🏟 <b>Локація:</b> {is_home}\n\n"
                f"⏰ <b>Початок гри:</b> {start_local.strftime('%H:%M')}\n"
                f"⏳ <b>Орієнтовне закінчення:</b> {end_local.strftime('%H:%M')}\n\n"
                f"📢 <b>Рівень небезпеки для вух:</b>\n<b>{level}</b>\nℹ️ <i>{comment}</i>"
            )
            send_tg_message(msg)
            print("Сповіщення про сьогоднішній матч надіслано!")
        else:
            print("Сьогодні матчів Баварії немає.")
            
            # Якщо запуск виконувався вручну через кнопку Run Workflow — надіслати тестовий звіт
            if os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch":
                diag = ["ℹ️ <b>Тест бота успішний! Сьогодні гри немає.</b>\n\n📅 <b>Найближчі матчі Баварії:</b>"]
                for m in upcoming[:3]:
                    m_utc = m["utcDate"].replace("Z", "+00:00")
                    m_time = datetime.fromisoformat(m_utc).astimezone(TIMEZONE)
                    opp = m["awayTeam"]["name"] if m["homeTeam"]["id"] == BAYERN_ID else m["homeTeam"]["name"]
                    diag.append(f"• {m_time.strftime('%d.%m %H:%M')} проти <b>{opp}</b> ({m.get('competition', {}).get('name')})")
                send_tg_message("\n".join(diag))

    except Exception as e:
        print(f"Помилка: {e}")


if __name__ == "__main__":
    check_bayern_match()
