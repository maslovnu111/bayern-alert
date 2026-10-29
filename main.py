import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests

# Часовий пояс Варшави
TIMEZONE = ZoneInfo("Europe/Warsaw")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
API_KEY = os.environ.get("FOOTBALL_API_KEY")

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
    """Визначає рівень небезпеки шуму та генерує коментар."""
    comp_lower = competition.lower()
    opp_lower = opponent.lower()

    # 1. Ліга Чемпіонів
    if "champions league" in comp_lower:
        if stage in ["QUARTER_FINALS", "SEMI_FINALS", "FINAL"]:
            return (
                "🚨 ЕКСТРЕМАЛЬНА",
                "Вирішальна стадія плей-оф Ліги Чемпіонів. Будь-яка помилка веде до вильоту з турніру. Емоції та крики сусіда гарантовані весь матч.",
            )
        return (
            "🔥 ВИСОКА",
            "Матч Ліги Чемпіонів. Найпрестижніший європейський турнір сезону — такі ігри фанати дивляться з особливим азартом.",
        )

    # 2. Бундесліга
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
            "Звичайний тур чемпіонату Німеччини. Сусід кричатиме переважно під час забитих голів.",
        )

    # 3. Кубок Німеччини (DFB-Pokal / Кубок НФФ)
    if any(k in comp_lower for k in ["pokal", "cup", "кубок"]):
        return (
            "🔥 ВИСОКА",
            "Матч Кубка Німеччини (Кубок НФФ) на виліт. Програш означає миттєвий виліт із турніру, а у разі нічиєї можливі додаткові тайми та пенальті!",
        )

    # 4. Інші турніри
    return (
        "🟢 ПОМІРНА",
        "Рядовий, кубковий або товариський матч.",
    )


def format_and_send(opponent: str, competition: str, is_home: str, start_local: datetime, stage: str = ""):
    """Формує та надсилає сповіщення у Telegram."""
    end_local = start_local + timedelta(hours=1, minutes=55)
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
    print(f"Сповіщення надіслано! Суперник: {opponent} ({competition})")


def check_espn_fallback(today_local) -> bool:
    """Резервна перевірка через безкоштовний API ESPN (бачить Кубок Німеччини, Суперкубок тощо)."""
    date_str = today_local.strftime("%Y%m%d")
    leagues = [
        ("ger.dfb_pokal", "Кубок Німеччини (DFB-Pokal)"),
        ("ger.super_cup", "Суперкубок Німеччини"),
        ("ger.1", "Bundesliga"),
        ("uefa.champions", "UEFA Champions League"),
        ("fifa.cwc", "Клубний Чемпіонат Світу"),
        ("club.friendly", "Товариський матч"),
    ]

    for slug, comp_name in leagues:
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard?dates={date_str}"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                continue
            events = resp.json().get("events", [])
            for event in events:
                competitions = event.get("competitions", [{}])[0]
                competitors = competitions.get("competitors", [])

                bayern_comp = None
                opponent_comp = None
                for comp in competitors:
                    team_name = comp.get("team", {}).get("displayName", "")
                    if "bayern" in team_name.lower():
                        bayern_comp = comp
                    else:
                        opponent_comp = comp

                if bayern_comp and opponent_comp:
                    utc_str = event["date"].replace("Z", "+00:00")
                    start_local = datetime.fromisoformat(utc_str).astimezone(TIMEZONE)

                    if start_local.date() == today_local:
                        opponent_name = opponent_comp.get("team", {}).get("displayName", "Невідомий суперник")
                        is_home = "Вдома (Allianz Arena)" if bayern_comp.get("homeAway") == "home" else "На виїзді"
                        format_and_send(opponent_name, comp_name, is_home, start_local)
                        return True
        except Exception as e:
            print(f"Помилка резервної перевірки ({slug}): {e}")

    return False


def check_bayern_match():
    today_local = datetime.now(TIMEZONE).date()

    # 1. Основна перевірка через football-data.org (Бундесліга та Ліга Чемпіонів)
    url = f"https://api.football-data.org/v4/teams/{BAYERN_ID}/matches"
    headers = {"X-Auth-Token": API_KEY}

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            matches = response.json().get("matches", [])
            for match in matches:
                utc_time_str = match["utcDate"].replace("Z", "+00:00")
                start_local = datetime.fromisoformat(utc_time_str).astimezone(TIMEZONE)

                if start_local.date() == today_local:
                    home_team = match["homeTeam"]["name"]
                    away_team = match["awayTeam"]["name"]
                    opponent = away_team if match["homeTeam"]["id"] == BAYERN_ID else home_team
                    is_home = "Вдома (Allianz Arena)" if match["homeTeam"]["id"] == BAYERN_ID else "На виїзді"
                    competition = match.get("competition", {}).get("name", "Турнір")
                    stage = match.get("stage", "")

                    format_and_send(opponent, competition, is_home, start_local, stage)
                    return
    except Exception as e:
        print(f"Помилка основного API: {e}")

    # 2. Додаткова перевірка через ESPN (Кубок Німеччини / Кубок НФФ та інші турніри)
    print("Перевірка кубкових матчів через додаткову базу...")
    if check_espn_fallback(today_local):
        return

    print("Сьогодні матчів Баварії немає в жодній базі.")


if __name__ == "__main__":
    check_bayern_match()
