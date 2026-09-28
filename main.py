import os
import sys
import requests
from dotenv import load_dotenv

# Ensure UTF-8 output encoding across Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Load environment variables from .env file if available
load_dotenv()

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

WEATHER_URL = "https://api.weatherapi.com/v1/current.json"
NEWS_URL = "https://newsapi.org/v2/top-headlines"
NEWS_EVERYTHING_URL = "https://newsapi.org/v2/everything"

TIMEOUT_SECONDS = 8
PAGE_SIZE = 3

# Mapping of country names to ISO 3166-1 alpha-2 codes supported by NewsAPI
NEWS_API_COUNTRIES = {
    "argentina": "ar",
    "australia": "au",
    "austria": "at",
    "belgium": "be",
    "brazil": "br",
    "bulgaria": "bg",
    "canada": "ca",
    "china": "cn",
    "colombia": "co",
    "cuba": "cu",
    "czech republic": "cz",
    "czechia": "cz",
    "egypt": "eg",
    "france": "fr",
    "germany": "de",
    "greece": "gr",
    "hong kong": "hk",
    "hungary": "hu",
    "india": "in",
    "indonesia": "id",
    "ireland": "ie",
    "israel": "il",
    "italy": "it",
    "japan": "jp",
    "latvia": "lv",
    "lithuania": "lt",
    "malaysia": "my",
    "mexico": "mx",
    "morocco": "ma",
    "netherlands": "nl",
    "new zealand": "nz",
    "nigeria": "ng",
    "norway": "no",
    "philippines": "ph",
    "poland": "pl",
    "portugal": "pt",
    "romania": "ro",
    "russia": "ru",
    "saudi arabia": "sa",
    "serbia": "rs",
    "singapore": "sg",
    "slovakia": "sk",
    "slovenia": "si",
    "south africa": "za",
    "south korea": "kr",
    "korea": "kr",
    "sweden": "se",
    "switzerland": "ch",
    "taiwan": "tw",
    "thailand": "th",
    "turkey": "tr",
    "türkiye": "tr",
    "uae": "ae",
    "ukraine": "ua",
    "united arab emirates": "ae",
    "united kingdom": "gb",
    "uk": "gb",
    "great britain": "gb",
    "england": "gb",
    "united states": "us",
    "united states of america": "us",
    "usa": "us",
    "venezuela": "ve",
}


def check_api_keys() -> bool:
    """Validates that API keys exist before running."""
    missing = []
    if not WEATHER_API_KEY:
        missing.append("WEATHER_API_KEY (from https://www.weatherapi.com/)")
    if not NEWS_API_KEY:
        missing.append("NEWS_API_KEY (from https://newsapi.org/)")

    if missing:
        print("⚠️  Missing API key configuration:")
        for key in missing:
            print(f"  - {key}")
        print("\nPlease set them in a .env file or your environment variables.")
        return False
    return True


def get_country_code(country_name: str) -> str | None:
    """Maps country name to a supported 2-letter ISO country code for NewsAPI."""
    normalized = country_name.strip().lower()
    if normalized in NEWS_API_COUNTRIES:
        return NEWS_API_COUNTRIES[normalized]
    if len(normalized) == 2 and normalized in NEWS_API_COUNTRIES.values():
        return normalized
    return None


def get_weather(city: str, session: requests.Session) -> dict:
    """Fetch weather data for a given city."""
    params = {
        "key": WEATHER_API_KEY,
        "q": city,
        "aqi": "no",
    }
    try:
        response = session.get(WEATHER_URL, params=params, timeout=TIMEOUT_SECONDS)
        if response.status_code == 200:
            data = response.json()
            location = data.get("location", {})
            current = data.get("current", {})
            condition = current.get("condition", {})
            return {
                "city": location.get("name", city),
                "country": location.get("country", ""),
                "temp_c": current.get("temp_c", "N/A"),
                "condition": condition.get("text", "Unknown"),
                "humidity": current.get("humidity", "N/A"),
                "wind_kph": current.get("wind_kph", "N/A"),
            }
        elif response.status_code == 400:
            return {"error": f"City '{city}' not found. Please check spelling."}
        elif response.status_code == 401:
            return {"error": "Invalid WeatherAPI key. Please verify WEATHER_API_KEY in .env."}
        elif response.status_code == 429:
            return {"error": "WeatherAPI rate limit or quota exceeded."}
        else:
            return {"error": f"Weather API error: HTTP {response.status_code}"}
    except requests.exceptions.Timeout:
        return {"error": "Weather request timed out. Please check your internet connection."}
    except requests.exceptions.RequestException as e:
        return {"error": f"Network error fetching weather: {e}"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


def get_news(city: str, country: str, session: requests.Session) -> dict:
    """Fetch top news headlines for a given city and country."""
    headers = {"X-Api-Key": NEWS_API_KEY}

    try:
        # Attempt 1: Fetch city-specific headlines
        res = session.get(
            NEWS_URL,
            headers=headers,
            params={"q": city, "pageSize": PAGE_SIZE, "language": "en"},
            timeout=TIMEOUT_SECONDS,
        )
        if res.status_code == 200:
            articles = [
                art["title"]
                for art in res.json().get("articles", [])
                if art.get("title") and art["title"] != "[Removed]"
            ]
            if articles:
                return {"articles": articles, "error": None}
        elif res.status_code == 401:
            return {"articles": [], "error": "Invalid NewsAPI key. Please verify NEWS_API_KEY in .env."}
        elif res.status_code == 429:
            return {"articles": [], "error": "NewsAPI rate limit or quota reached."}

        # Attempt 2: Fall back to country-level top headlines if country code is supported
        country_code = get_country_code(country)
        if country_code:
            res = session.get(
                NEWS_URL,
                headers=headers,
                params={"country": country_code, "pageSize": PAGE_SIZE},
                timeout=TIMEOUT_SECONDS,
            )
            if res.status_code == 200:
                articles = [
                    art["title"]
                    for art in res.json().get("articles", [])
                    if art.get("title") and art["title"] != "[Removed]"
                ]
                if articles:
                    return {"articles": articles, "error": None}
            elif res.status_code == 401:
                return {"articles": [], "error": "Invalid NewsAPI key. Please verify NEWS_API_KEY in .env."}
            elif res.status_code == 429:
                return {"articles": [], "error": "NewsAPI rate limit or quota reached."}

        # Attempt 3: Fall back to general search via the everything endpoint
        res = session.get(
            NEWS_EVERYTHING_URL,
            headers=headers,
            params={"q": city, "pageSize": PAGE_SIZE, "language": "en", "sortBy": "publishedAt"},
            timeout=TIMEOUT_SECONDS,
        )
        if res.status_code == 200:
            articles = [
                art["title"]
                for art in res.json().get("articles", [])
                if art.get("title") and art["title"] != "[Removed]"
            ]
            if articles:
                return {"articles": articles, "error": None}
        elif res.status_code == 401:
            return {"articles": [], "error": "Invalid NewsAPI key. Please verify NEWS_API_KEY in .env."}
        elif res.status_code == 429:
            return {"articles": [], "error": "NewsAPI rate limit or quota reached."}

        return {"articles": [], "error": None}

    except requests.exceptions.Timeout:
        return {"articles": [], "error": "News request timed out."}
    except requests.exceptions.RequestException as e:
        return {"articles": [], "error": f"Network error fetching news: {e}"}
    except Exception as e:
        return {"articles": [], "error": f"Unexpected error: {e}"}


def display_dashboard(weather_data: dict, news_data: dict):
    """Renders formatted CLI dashboard."""
    city_name = weather_data["city"].upper()
    country_name = weather_data["country"]
    header = f"🌤️  {city_name}, {country_name} DASHBOARD  🌤️"
    width = max(50, len(header) + 4)

    print("\n" + "=" * width)
    print(header.center(width))
    print("=" * width)
    print(f"Weather:  {weather_data['temp_c']}°C, {weather_data['condition']}")
    print(f"Humidity: {weather_data['humidity']}% | Wind: {weather_data['wind_kph']} km/h")
    print("-" * width)
    print("📰 TOP NEWS HEADLINES")

    if news_data.get("error"):
        print(f"  ⚠️  {news_data['error']}")
    elif news_data.get("articles"):
        for i, headline in enumerate(news_data["articles"], 1):
            print(f"  {i}. {headline}")
    else:
        print("  ℹ️  No recent English headlines found for this location.")

    print("=" * width + "\n")


def main():
    print("\nStarting City Dashboard...")
    if not check_api_keys():
        sys.exit(1)

    with requests.Session() as session:
        while True:
            try:
                city_input = input("Enter city name (or 'q' to quit): ").strip()
                if not city_input:
                    continue
                if city_input.lower() in ("quit", "exit", "q"):
                    print("Thank you for using City Dashboard!")
                    break

                weather = get_weather(city_input, session)
                if "error" in weather:
                    print(f"⚠️  {weather['error']}\n")
                    continue

                news = get_news(weather["city"], weather["country"], session)
                display_dashboard(weather, news)

            except (KeyboardInterrupt, EOFError):
                print("\nExiting...")
                break


if __name__ == "__main__":
    main()
