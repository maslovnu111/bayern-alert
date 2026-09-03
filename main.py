import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests

# Налаштування часового поясу (за замовчуванням Київ: Europe/Kyiv, або Berlin: Europe/Berlin)
TIMEZONE = "Europe/Kyiv"

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
API_KEY = os.environ.get("FOOTBALL_API_KEY")

# ID Баварії в базі football-data.org — 5
BAYERN_ID = 5


def assess_importance(competition: str, stage: str, opponent: str) -> str:
    """Визначає потенційний рівень гучності сусіда."""
    top_opponents = ["Borussia Dortmund", "Bayer 04 Leverkusen", "RB Leipzig"]

    if "Champions League" in competition:
        if stage in ["QUARTER_FINALS", "SEMI_FINALS", "FINAL"]:
            return "🚨 ЕКСТРЕМАЛЬНА (Плей-оф Ліги Чемпіонів! Сусід кричатиме без зупину)"
        return "🔥 ВИСОКА (Ліга Чемпіонів — приготуйте беруші)"

    if "Bundesliga" in competition:
        if any(team.lower() in opponent.lower() for team in top_opponents):
            return "⚡ ДУЖЕ ВИСОКА (Принципове дербі / Топ-матч)"
        return "🟡 СЕРЕДНЯ (Звичайний тур чемпіонату Німеччини)"

    return "🟢 ПОМІРНА"


def check_bayern_match():
    local_tz = ZoneInfo(TIMEZONE)
    today = datetime.now(local_tz).date()

    url = f"https://api.football-data.org/v4/teams/{BAYERN_ID}/matches?status=SCHEDULED"
    headers = {"X-Auth-Token": API_KEY}

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Помилка отримання даних: {response.status_code} - {response.text}")
        return

    data = response.json()
    matches = data.get("matches", [])

    for match in matches:
        # Час початку матчу за UTC
        utc_time_str = match["utcDate"].replace("Z", "+00:00")
        start_utc = datetime.fromisoformat(utc_time_str)

        # Переводимо у ваш місцевий час
        start_local = start_utc.astimezone(local_tz)

        if start_local.date() == today:
            # Орієнтовна тривалість гри ~1 год 55 хв (два тайми по 45 хв + перерва 15 хв + доданий час)
            end_local = start_local + timedelta(hours=1, minutes=55)

            home_team = match["homeTeam"]["name"]
            away_team = match["awayTeam"]["name"]
            opponent = away_team if match["homeTeam"]["id"] == BAYERN_ID else home_team
            is_home = "Вдома (Allianz Arena)" if match["homeTeam"]["id"] == BAYERN_ID else "На виїзді"

            competition = match.get("competition", {}).get("name", "Невідомий турнір")
            stage = match.get("stage", "")
            importance = assess_importance(competition, stage, opponent)

            message = (
                f"⚠️ <b>УВАГА: СЬОГОДНІ ГРАЄ БАВАРІЯ!</b>\n\n"
                f"⚽ <b>Суперник:</b> {opponent}\n"
                f"🏆 <b>Турнір:</b> {competition}\n"
                f"🏟 <b>Локація:</b> {is_home}\n\n"
                f"⏰ <b>Початок гри:</b> {start_local.strftime('%H:%M')}\n"
                f"⏳ <b>Орієнтовне закінчення:</b> {end_local.strftime('%H:%M')}\n\n"
                f"📢 <b>Рівень небезпеки для вух:</b>\n{importance}"
            )

            # Відправка у Telegram
            tg_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
            requests.post(tg_url, data=payload)
            print("Сповіщення успішно надіслано!")
            return

    print("Сьогодні матчів Баварії немає. Спокій гарантовано.")


if __name__ == "__main__":
    check_bayern_match()
