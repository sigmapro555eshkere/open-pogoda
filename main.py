import asyncio
import html
import os

import aiohttp
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

load_dotenv()
TOKEN = os.getenv("tenge")

if not TOKEN:
    raise ValueError("tenge не найден в .env🔋")

dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я хайповый бот для погоды.\n"
        "Доступные команды:\n"
        "/help\n"
        "/weather <город>"
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "Команды:\n"
        "/start - запуск бота\n"
        "/help - показать помощь\n"
        "/weather <город> - показать текущую погоду"
    )


WEATHER_CODES = {
    0: "Ясно",
    1: "Преимущественно ясно",
    2: "Переменная облачность",
    3: "Пасмурно",
    45: "Туман",
    48: "Изморозь",
    51: "Слабая морось",
    53: "Морось",
    55: "Сильная морось",
    61: "Слабый дождь",
    63: "Дождь",
    65: "Сильный дождь",
    66: "Ледяной дождь",
    67: "Сильный ледяной дождь",
    71: "Слабый снег",
    73: "Снег",
    75: "Сильный снег",
    77: "Снежные зерна",
    80: "Слабый ливень",
    81: "Ливень",
    82: "Сильный ливень",
    85: "Слабый снегопад",
    86: "Сильный снегопад",
    95: "Гроза",
    96: "Гроза с градом",
    99: "Сильная гроза с градом",
}


async def fetch_json(session: aiohttp.ClientSession, url: str, params: dict) -> dict:
    async with session.get(url, params=params) as response:
        response.raise_for_status()
        return await response.json()


async def get_weather(city: str) -> str:
    async with aiohttp.ClientSession() as session:
        geo_data = await fetch_json(
            session,
            "https://geocoding-api.open-meteo.com/v1/search",
            {"name": city, "count": 1, "language": "ru", "format": "json"},
        )

        results = geo_data.get("results") or []
        if not results:
            return f"Город не найден: {html.escape(city)}"

        location = results[0]
        latitude = location["latitude"]
        longitude = location["longitude"]
        city_name = location["name"]
        country = location.get("country", "")

        weather_data = await fetch_json(
            session,
            "https://api.open-meteo.com/v1/forecast",
            {
                "latitude": latitude,
                "longitude": longitude,
                "current": [
                    "temperature_2m",
                    "apparent_temperature",
                    "wind_speed_10m",
                    "weather_code",
                ],
                "timezone": "auto",
                "forecast_days": 1,
            },
        )

        current = weather_data.get("current")
        if not current:
            return "Не удалось получить данные о погоде."

        weather_code = current.get("weather_code")
        description = WEATHER_CODES.get(weather_code, "Неизвестно")

        location_text = city_name if not country else f"{city_name}, {country}"
        return (
            f"Погода в {html.escape(location_text)}:\n"
            f"Состояние: {description}\n"
            f"Температура: {current['temperature_2m']}°C\n"
            f"Ощущается как: {current['apparent_temperature']}°C\n"
            f"Ветер: {current['wind_speed_10m']} м/с"
        )


@dp.message(Command("weather"))
async def cmd_weather(message: Message):
    parts = message.text.split(maxsplit=1) if message.text else []
    if len(parts) < 2 or not parts[1].strip():
        await message.answer("Использование: /weather <город>\nПример: /weather Magadan ")
        return

    city = parts[1].strip()

    try:
        weather_text = await get_weather(city)
    except aiohttp.ClientError:
        await message.answer("Ошибка при запросе к сервису погоды. Попробуй позже.")
        return

    await message.answer(weather_text)

@dp.message()
async def echo(message: Message):
    await message.answer(f"Ты написал: {message.text}")

async def main():
    bot = Bot(TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
