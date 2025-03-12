import discord
from discord.ext import commands
import requests
import config
from datetime import datetime

class Weather(commands.Cog):
    """Enhanced weather-related commands."""

    def __init__(self, bot):
        self.bot = bot

    # Weather icon mapping based on OpenWeatherMap condition codes
    WEATHER_ICONS = {
        "clear": "☀️", "clouds": "☁️", "rain": "🌧️", "drizzle": "🌦️",
        "thunderstorm": "⛈️", "snow": "❄️", "mist": "🌫️", "fog": "🌫️",
        "haze": "🌫️", "smoke": "🌫️", "dust": "🌫️", "sand": "🌫️",
        "ash": "🌫️", "squall": "🌬️", "tornado": "🌪️"
    }

    def get_weather_icon(self, condition: str) -> str:
        """Map weather condition to an emoji."""
        condition = condition.lower()
        for key, icon in self.WEATHER_ICONS.items():
            if key in condition:
                return icon
        return "🌍"  # Default icon if no match

    @commands.command(name='weather')
    async def weather(self, ctx, *, city: str = None):
        """Fetch and display detailed weather info for a city."""
        if not city:
            embed = discord.Embed(
                title="🌤️ Weather Command",
                description=f"Get current weather info with `{config.BOT_PREFIX}weather <city>`\nExample: `{config.BOT_PREFIX}weather London`",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="ℹ️ Tip",
                value="Spell the city name correctly for accurate results.",
                inline=False
            )
            embed.set_footer(
                text=f"{config.BOT_NAME} - Powered by OpenWeatherMap",
                icon_url=self.bot.user.avatar.url
            )
            await ctx.send(embed=embed)
            return

        try:
            # OpenWeatherMap API setup
            api_key = config.WEATHER_API_KEY
            url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
            response = requests.get(url)
            data = response.json()

            if response.status_code == 200:
                # Extract weather details
                weather_desc = data["weather"][0]["description"].capitalize()
                weather_icon = self.get_weather_icon(data["weather"][0]["main"])
                temp = data["main"]["temp"]
                feels_like = data["main"]["feels_like"]
                humidity = data["main"]["humidity"]
                wind_speed = data["wind"]["speed"]
                pressure = data["main"]["pressure"]  # hPa
                country = data["sys"]["country"]
                sunrise = datetime.fromtimestamp(data["sys"]["sunrise"]).strftime('%H:%M')
                sunset = datetime.fromtimestamp(data["sys"]["sunset"]).strftime('%H:%M')

                # Create embed
                embed = discord.Embed(
                    title=f"{weather_icon} Weather in {city.capitalize()}, {country}",
                    description=f"**{weather_desc}**",
                    color=discord.Color.blue()
                )

                # Temperature & Feels Like
                embed.add_field(
                    name="🌡️ Temperature",
                    value=f"{temp}°C\nFeels Like: {feels_like}°C",
                    inline=True
                )

                # Wind & Humidity
                embed.add_field(
                    name="🌬️ Conditions",
                    value=f"Wind: {wind_speed} m/s\nHumidity: {humidity}%",
                    inline=True
                )

                # Pressure & Sun Times
                embed.add_field(
                    name="⛅ Atmosphere",
                    value=f"Pressure: {pressure} hPa\nSunrise: {sunrise}\nSunset: {sunset}",
                    inline=True
                )

                # Thumbnail based on weather condition
                icon_code = data["weather"][0]["icon"]
                embed.set_thumbnail(url=f"http://openweathermap.org/img/wn/{icon_code}@2x.png")

                embed.set_footer(
                    text=f"{config.BOT_NAME} - Powered by OpenWeatherMap",
                    icon_url=self.bot.user.avatar.url
                )
                await ctx.send(embed=embed)

            else:
                # Handle API-specific errors
                error_msg = data.get("message", "Unknown error").capitalize()
                error_embed = discord.Embed(
                    title="❌ Weather Error",
                    description=f"Failed to fetch weather: {error_msg}\nPlease check the city name and try again.",
                    color=discord.Color.red()
                )
                error_embed.set_footer(
                    text=f"{config.BOT_NAME} - Powered by OpenWeatherMap",
                    icon_url=self.bot.user.avatar.url
                )
                await ctx.send(embed=error_embed)

        except Exception as e:
            error_embed = discord.Embed(
                title="⚠️ Unexpected Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )
            error_embed.set_footer(
                text=f"{config.BOT_NAME} - Powered by OpenWeatherMap",
                icon_url=self.bot.user.avatar.url
            )
            await ctx.send(embed=error_embed)

async def setup(bot):
    await bot.add_cog(Weather(bot))