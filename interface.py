from core import Bot
from core_web import BotWeb


def show(use_web: bool = False) -> None:
    print("=" * 52)
    print("Текстовий чат-бот на базі трансформерної моделі")
    print("Введіть ваше запитання та натисніть Enter.")
    print("Щоб завершити роботу, введіть команду: вихід або exit")
    print("=" * 52)

    try:
        # Initialize standard bot or web-enabled bot
        bot = BotWeb() if use_web else Bot()
    except Exception as exc:
        print(f"Помилка ініціалізації ({type(exc).__name__}): {exc}")
        return

    while True:
        user_input = input("\nВи: ").strip()
        if not user_input:
            continue

        # Handle commands using match/case
        match user_input.lower():
            case "вихід" | "exit":
                print("Бот: До побачення! Роботу завершено.")
                break
            case _:
                try:
                    reply = bot.generate_response(user_input)
                    print(f"Бот: {reply}")
                except Exception as exc:
                    print(f"Помилка генерації ({type(exc).__name__}): {exc}")
                    # Roll back the failed user message so history stays consistent
                    bot.history.pop_last_message()


if __name__ == "__main__":
    # Set use_web=True to run BotWeb with internet search
    show(use_web=False)