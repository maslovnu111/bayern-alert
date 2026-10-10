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
            return ("🚨 ЕКСТРЕМАЛЬНА", "Вирішальна стадія Ліги Чемпіонів. Емоції та крики сусіда гарантовані весь матч.")
        return ("🔥 ВИСОКА", "Матч Ліги Чемпіонів. Один із найважливіших турнірів сезону.")

    if "bundesliga" in comp_lower:
        if "dortmund" in opp_lower:
            return ("⚡ ДУЖЕ ВИСОКА", "Принципове дербі («Der Klassiker») проти Дортмунда. Найвища напруга.")
        if any(team in opp_lower for team in ["leverkusen", "leipzig"]):
            return ("⚡ ДУЖЕ ВИСОКА", f"Матч проти прямого конкурента ({opponent}) за перше місце в чемпіонаті.")
        return ("🟡 СЕРЕДНЯ", "Звичайний тур чемпіонату. Крики лунатимуть переважно під час забитих голів.")

    return ("🟢 ПОМІРНА", "Кубковий, товариський або рядовий матч без критичного турнірного тиску.")


def check_bayern_match():
    today_local = datetime.now(TIMEZONE).date()

    # Запитуємо матчі без жорсткого фільтра за статусом
    url = f"https://api.football-data.org/v4/teams/{BAYERN_ID}/matches"
    headers = {"X-Auth-Token": API_KEY}

    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Помилка API: {response.status_code}")
            send_tg_message(f"⚠️ Помилка отримання даних матчу (Код {response.status_code}).")
            return

        data = response.json()
        matches = data.get("matches", [])

        # --- ДІАГНОСТИКА: друк отриманих матчів у логи GitHub ---
        print(f"=== Отримано від сервера матчів: {len(matches)} ===")
        for m in matches[:5]:
            print(f"-> {m.get('utcDate')} | {m.get('homeTeam', {}).get('name')} vs {m.get('awayTeam', {}).get('name')} | Статус: {m.get('status')}")
        print("====================================================")

        valid_statuses = ["SCHEDULED", "TIMED", "IN_PLAY", "PAUSED"]

        for match in matches:
            if match.get("status") not in valid_statuses:
                continue

            utc_time_str = match["utcDate"].replace("Z", "+00:00")
            start_utc = datetime.fromisoformat(utc_time_str)
            start_local = start_utc.astimezone(TIMEZONE)

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
                print("Сповіщення успішно надіслано в Telegram!")
                return

        print("Сьогодні матчів Баварії немає.")

    except Exception as e:
        print(f"Виникла помилка: {e}")


if __name__ == "__main__":
    check_bayern_match()
