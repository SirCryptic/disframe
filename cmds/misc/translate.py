import discord
from discord.ext import commands
from googletrans import Translator, LANGUAGES
import config

class Translate(commands.Cog):
    """Enhanced translation commands with full Discord emoji support."""

    def __init__(self, bot):
        self.bot = bot
        self.translator = Translator()

    # Comprehensive emoji mapping for all googletrans languages
    TRANSLATION_EMOJIS = {
        "af": "🇿🇦",  # Afrikaans (South Africa)
        "sq": "🇦🇱",  # Albanian (Albania)
        "am": "🇪🇹",  # Amharic (Ethiopia)
        "ar": "🇸🇦",  # Arabic (Saudi Arabia)
        "hy": "🇦🇲",  # Armenian (Armenia)
        "az": "🇦🇿",  # Azerbaijani (Azerbaijan)
        "eu": "🇪🇸",  # Basque (Spain, no specific flag, using Spain)
        "be": "🇧🇾",  # Belarusian (Belarus)
        "bn": "🇧🇩",  # Bengali (Bangladesh)
        "bs": "🇧🇦",  # Bosnian (Bosnia and Herzegovina)
        "bg": "🇧🇬",  # Bulgarian (Bulgaria)
        "ca": "🇪🇸",  # Catalan (Spain, often Catalonia but using Spain)
        "ceb": "🇵🇭",  # Cebuano (Philippines)
        "ny": "🇲🇼",  # Chichewa (Malawi)
        "zh-cn": "🇨🇳",  # Chinese (Simplified, China)
        "zh-tw": "🇹🇼",  # Chinese (Traditional, Taiwan)
        "co": "🇫🇷",  # Corsican (France, no specific flag)
        "hr": "🇭🇷",  # Croatian (Croatia)
        "cs": "🇨🇿",  # Czech (Czech Republic)
        "da": "🇩🇰",  # Danish (Denmark)
        "nl": "🇳🇱",  # Dutch (Netherlands)
        "en": "🇬🇧",  # English (United Kingdom)
        "eo": "🌐",  # Esperanto (No country flag)
        "et": "🇪🇪",  # Estonian (Estonia)
        "tl": "🇵🇭",  # Filipino (Philippines)
        "fi": "🇫🇮",  # Finnish (Finland)
        "fr": "🇫🇷",  # French (France)
        "fy": "🇳🇱",  # Frisian (Netherlands, often Friesland but using NL)
        "gl": "🇪🇸",  # Galician (Spain)
        "ka": "🇬🇪",  # Georgian (Georgia)
        "de": "🇩🇪",  # German (Germany)
        "el": "🇬🇷",  # Greek (Greece)
        "gu": "🇮🇳",  # Gujarati (India)
        "ht": "🇭🇹",  # Haitian Creole (Haiti)
        "ha": "🇳🇬",  # Hausa (Nigeria)
        "haw": "🇺🇸",  # Hawaiian (United States, Hawaii but using US)
        "iw": "🇮🇱",  # Hebrew (Israel, 'iw' is legacy code for Hebrew)
        "he": "🇮🇱",  # Hebrew (Modern code)
        "hi": "🇮🇳",  # Hindi (India)
        "hmn": "🇨🇳",  # Hmong (China, common region)
        "hu": "🇭🇺",  # Hungarian (Hungary)
        "is": "🇮🇸",  # Icelandic (Iceland)
        "ig": "🇳🇬",  # Igbo (Nigeria)
        "id": "🇮🇩",  # Indonesian (Indonesia)
        "ga": "🇮🇪",  # Irish (Ireland)
        "it": "🇮🇹",  # Italian (Italy)
        "ja": "🇯🇵",  # Japanese (Japan)
        "jw": "🇮🇩",  # Javanese (Indonesia)
        "kn": "🇮🇳",  # Kannada (India)
        "kk": "🇰🇿",  # Kazakh (Kazakhstan)
        "km": "🇰🇭",  # Khmer (Cambodia)
        "ko": "🇰🇷",  # Korean (South Korea)
        "ku": "🇮🇶",  # Kurdish (Iraq, common region)
        "ky": "🇰🇬",  # Kyrgyz (Kyrgyzstan)
        "lo": "🇱🇦",  # Lao (Laos)
        "la": "🌐",  # Latin (No country flag)
        "lv": "🇱🇻",  # Latvian (Latvia)
        "lt": "🇱🇹",  # Lithuanian (Lithuania)
        "lb": "🇱🇺",  # Luxembourgish (Luxembourg)
        "mk": "🇲🇰",  # Macedonian (North Macedonia)
        "mg": "🇲🇬",  # Malagasy (Madagascar)
        "ms": "🇲🇾",  # Malay (Malaysia)
        "ml": "🇮🇳",  # Malayalam (India)
        "mt": "🇲🇹",  # Maltese (Malta)
        "mi": "🇳🇿",  # Maori (New Zealand)
        "mr": "🇮🇳",  # Marathi (India)
        "mn": "🇲🇳",  # Mongolian (Mongolia)
        "my": "🇲🇲",  # Myanmar (Burma)
        "ne": "🇳🇵",  # Nepali (Nepal)
        "no": "🇳🇴",  # Norwegian (Norway)
        "or": "🇮🇳",  # Odia (India)
        "ps": "🇦🇫",  # Pashto (Afghanistan)
        "fa": "🇮🇷",  # Persian (Iran)
        "pl": "🇵🇱",  # Polish (Poland)
        "pt": "🇵🇹",  # Portuguese (Portugal)
        "pa": "🇮🇳",  # Punjabi (India)
        "ro": "🇷🇴",  # Romanian (Romania)
        "ru": "🇷🇺",  # Russian (Russia)
        "sm": "🇼🇸",  # Samoan (Samoa)
        "gd": "🇬🇧",  # Scots Gaelic (United Kingdom, Scotland)
        "sr": "🇷🇸",  # Serbian (Serbia)
        "st": "🇱🇸",  # Sesotho (Lesotho)
        "sn": "🇿🇼",  # Shona (Zimbabwe)
        "sd": "🇵🇰",  # Sindhi (Pakistan)
        "si": "🇱🇰",  # Sinhala (Sri Lanka)
        "sk": "🇸🇰",  # Slovak (Slovakia)
        "sl": "🇸🇮",  # Slovenian (Slovenia)
        "so": "🇸🇴",  # Somali (Somalia)
        "es": "🇪🇸",  # Spanish (Spain)
        "su": "🇮🇩",  # Sundanese (Indonesia)
        "sw": "🇰🇪",  # Swahili (Kenya)
        "sv": "🇸🇪",  # Swedish (Sweden)
        "tg": "🇹🇯",  # Tajik (Tajikistan)
        "ta": "🇮🇳",  # Tamil (India)
        "te": "🇮🇳",  # Telugu (India)
        "th": "🇹🇭",  # Thai (Thailand)
        "tr": "🇹🇷",  # Turkish (Turkey)
        "uk": "🇺🇦",  # Ukrainian (Ukraine)
        "ur": "🇵🇰",  # Urdu (Pakistan)
        "ug": "🇨🇳",  # Uyghur (China)
        "uz": "🇺🇿",  # Uzbek (Uzbekistan)
        "vi": "🇻🇳",  # Vietnamese (Vietnam)
        "cy": "🇬🇧",  # Welsh (United Kingdom, Wales)
        "xh": "🇿🇦",  # Xhosa (South Africa)
        "yi": "🇮🇱",  # Yiddish (Israel, common region)
        "yo": "🇳🇬",  # Yoruba (Nigeria)
        "zu": "🇿🇦"   # Zulu (South Africa)
    }

    def get_language_emoji(self, lang_code: str) -> str:
        """Map language code to a Discord emoji flag or default."""
        return self.TRANSLATION_EMOJIS.get(lang_code.lower(), "🌐")

    @commands.command(name='translate')
    async def translate(self, ctx, lang: str = None, *, text: str = None):
        """Translate text into a specified language with emoji-enhanced output."""
        if not lang or not text:
            embed = discord.Embed(
                title="🌐 Translate",
                description=f"Translate text with `{config.BOT_PREFIX}translate <language_code> <text>`\nExample: `{config.BOT_PREFIX}translate es Hello, how are you?`",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="ℹ️ Language Codes",
                value="[Supported Languages](https://cloud.google.com/translate/docs/languages)",
                inline=False
            )
            embed.set_footer(
                text=f"{config.BOT_NAME} v{config.BOT_VERSION} | Powered by Google Translate",
                icon_url=self.bot.user.avatar.url
            )
            await ctx.send(embed=embed)
            return

        try:
            # Validate language code
            if lang.lower() not in LANGUAGES:
                raise ValueError(f"Invalid language code '{lang}'. Use `{config.BOT_PREFIX}translate` for help.")

            # Perform translation
            translation = self.translator.translate(text, dest=lang)
            source_lang = LANGUAGES.get(translation.src.lower(), "Unknown").capitalize()
            target_lang = LANGUAGES.get(lang.lower(), "Unknown").capitalize()
            source_emoji = self.get_language_emoji(translation.src)
            target_emoji = self.get_language_emoji(lang)

            # Sanitize output
            original_text = translation.origin.strip()
            translated_text = translation.text.strip()

            # Create embed
            embed = discord.Embed(
                title="🌐 Translation",
                description=f"{source_emoji} {source_lang} → {target_emoji} {target_lang}",
                color=discord.Color.blue()
            )

            # Translation Details
            embed.add_field(
                name="📥 Original",
                value=original_text,
                inline=True
            )
            embed.add_field(
                name="📤 Translated",
                value=translated_text,
                inline=True
            )

            # Language Info
            embed.add_field(
                name="ℹ️ Details",
                value=f"Source: {translation.src.upper()} ({source_lang})\nTarget: {lang.upper()} ({target_lang})",
                inline=False
            )

            embed.set_footer(
                text=f"{config.BOT_NAME} v{config.BOT_VERSION} | Powered by Google Translate",
                icon_url=self.bot.user.avatar.url
            )
            await ctx.send(embed=embed)

        except ValueError as ve:
            error_embed = discord.Embed(
                title="❌ Translation Error",
                description=str(ve),
                color=discord.Color.red()
            )
            error_embed.set_footer(
                text=f"{config.BOT_NAME} v{config.BOT_VERSION} | Powered by Google Translate",
                icon_url=self.bot.user.avatar.url
            )
            await ctx.send(embed=error_embed)
        except Exception as e:
            error_embed = discord.Embed(
                title="⚠️ Unexpected Error",
                description=f"Failed to translate: {str(e)}",
                color=discord.Color.red()
            )
            error_embed.set_footer(
                text=f"{config.BOT_NAME} v{config.BOT_VERSION} | Powered by Google Translate",
                icon_url=self.bot.user.avatar.url
            )
            await ctx.send(embed=error_embed)

async def setup(bot):
    await bot.add_cog(Translate(bot))
