import discord
from discord.ext import commands
import config
from config import BOT_PREFIX
import random
import aiohttp
from PIL import Image, ImageDraw, ImageFont
import io
import os
import json
import datetime
from discord.ui import Button, View, Select
import asyncio
import base64
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# Ensure the data/games directory exists
os.makedirs("data/games", exist_ok=True)

# SQLAlchemy setup
Base = declarative_base()
engine = create_engine('sqlite:///data/games/coinrush.db', echo=False)
Session = sessionmaker(bind=engine)

# Database Models
class Guild(Base):
    __tablename__ = 'guilds'
    id = Column(String, primary_key=True)
    users = relationship("User", back_populates="guild")

class User(Base):
    __tablename__ = 'users'
    id = Column(String, primary_key=True)
    guild_id = Column(String, ForeignKey('guilds.id'), nullable=False)
    coins = Column(Integer, default=0)
    items = Column(Text, default="[]")  # JSON string for items list
    last_work = Column(Float, default=0)
    last_steal = Column(Float, default=0)
    last_daily = Column(Float, default=0)
    job = Column(String, nullable=True)
    has_owned_vip = Column(Boolean, default=False)
    last_invest = Column(Float, default=0)
    achievements = Column(Text, default="[]")  # JSON string for achievements list
    total_earnings = Column(Integer, default=0)
    steals = Column(Integer, default=0)
    items_bought = Column(Integer, default=0)
    elicit_works = Column(Integer, default=0)
    investment_profits = Column(Integer, default=0)
    trades = Column(Integer, default=0)
    jackpots_won = Column(Integer, default=0)
    guild = relationship("Guild", back_populates="users")

# Create tables
Base.metadata.create_all(engine)

class CoinRush(commands.Cog):
    """An enhanced economy game with jobs, coins, items, trading, achievements, and a casino (guild-only)."""

    def __init__(self, bot):
        self.bot = bot
        self.base_image_path = os.path.join("assets", "images", "coinrush_base.jpg")
        self.busted_image_path = os.path.join("assets", "images", "busted_base.jpg")
        self.hospital_image_path = os.path.join("assets", "images", "hospital_base.jpg")
        self.font_path = os.path.join("assets", "fonts", "impact.ttf")
        self.jobs = {
            "Hacker": {"pay_min": 20, "pay_max": 60, "elicit": True, "emoji": "👨‍💻"},
            "Police": {"pay_min": 30, "pay_max": 50, "elicit": False, "emoji": "👮"},
            "Paramedic": {"pay_min": 25, "pay_max": 45, "elicit": False, "emoji": "👨‍⚕️"},
            "Engineer": {"pay_min": 35, "pay_max": 55, "elicit": False, "emoji": "👷"},
            "Chef": {"pay_min": 15, "pay_max": 40, "elicit": False, "emoji": "👨‍🍳"},
            "Artist": {"pay_min": 10, "pay_max": 50, "elicit": False, "emoji": "🎨"},
            "Pilot": {"pay_min": 40, "pay_max": 70, "elicit": False, "emoji": "✈️"},
            "Trader": {"pay_min": 25, "pay_max": 60, "elicit": False, "emoji": "💼"},
            "Drug Dealer": {"pay_min": 30, "pay_max": 80, "elicit": True, "emoji": "💊"},
            "Cartel Boss": {"pay_min": 50, "pay_max": 100, "elicit": True, "emoji": "🕴️"},
            "Crypto Investor": {"pay_min": 5, "pay_max": 90, "elicit": False, "emoji": "📈"}
        }
        self.shop_items = {
            "Cool Hat": {"cost": 100, "effect": "work_boost", "value": 0.1, "sell_price": 75},
            "Laser Gun": {"cost": 300, "effect": "steal_boost", "value": 0.15, "sell_price": 225},
            "Medkit": {"cost": 150, "effect": "work_stability", "value": 10, "sell_price": 100},
            "Stealth Cloak": {"cost": 250, "effect": "steal_protect", "value": 0.25, "sell_price": 175},
            "Toolbox": {"cost": 120, "effect": "work_boost", "value": 0.05, "sell_price": 90},
            "Shield": {"cost": 180, "effect": "steal_protect", "value": 0.15, "sell_price": 135},
            "Jetpack": {"cost": 350, "effect": "work_boost", "value": 0.2, "sell_price": 260},
            "Spy Drone": {"cost": 280, "effect": "steal_boost", "value": 0.1, "sell_price": 210},
            "Lucky Coin": {"cost": 90, "effect": "work_stability", "value": 5, "sell_price": 65},
            "Golden Key": {"cost": 400, "effect": "work_boost", "value": 0.25, "sell_price": 300},
            "Smoke Bomb": {"cost": 220, "effect": "steal_protect", "value": 0.3, "sell_price": 165},
            "Night Vision": {"cost": 260, "effect": "steal_boost", "value": 0.12, "sell_price": 195},
            "VIP Badge": {"cost": 1000, "effect": "steal_protect", "value": 0.95, "sell_price": 750},
            "Coffee Mug": {"cost": 80, "effect": "work_boost", "value": 0.08, "sell_price": 60},
            "Lockpick Set": {"cost": 200, "effect": "steal_boost", "value": 0.2, "sell_price": 150},
            "Steel Armor": {"cost": 320, "effect": "steal_protect", "value": 0.35, "sell_price": 240},
            "Energy Drink": {"cost": 110, "effect": "work_stability", "value": 8, "sell_price": 80},
            "Flashlight": {"cost": 140, "effect": "steal_boost", "value": 0.08, "sell_price": 105},
            "Safe Box": {"cost": 270, "effect": "steal_protect", "value": 0.28, "sell_price": 200},
            "Rocket Boots": {"cost": 380, "effect": "work_boost", "value": 0.22, "sell_price": 285}
        }
        self.achievements = {
            "First Payday": {"description": "Earn your first coins from work", "condition": lambda data: data["total_earnings"] >= 1},
            "Thief": {"description": "Successfully steal from someone", "condition": lambda data: data["steals"] >= 1},
            "Millionaire": {"description": "Reach 1,000 coins", "condition": lambda data: data["coins"] >= 1000},
            "Shopaholic": {"description": "Buy 5 items", "condition": lambda data: data["items_bought"] >= 5},
            "Risk Taker": {"description": "Work an elicit job 10 times", "condition": lambda data: data["elicit_works"] >= 10},
            "Investor": {"description": "Make a profit from investing", "condition": lambda data: data["investment_profits"] >= 1},
            "Trader": {"description": "Complete a trade", "condition": lambda data: data["trades"] >= 1},
            "VIP": {"description": "Own a VIP Badge", "condition": lambda data: "VIP Badge" in data["items"]},
            "Gambler": {"description": "Win a jackpot in the casino", "condition": lambda data: data.get("jackpots_won", 0) >= 1}
        }
        self.vip_role_name = "⭐VIP"
        self.easter_egg_encoded = "QnkxU2lyQ3J5cHRpYyDwn6W1IHJqdy1kYWQtbHktNC1ldmVyIC0gR2l0SHViOiBnaXRodWIuY29tL1NpckNyeXB0aWMgLSBEaXNGcmFtZXMgQ29yZS4="

    def get_user_data(self, guild_id: str, user_id: str, session=None):
        close_session = False
        if session is None:
            session = Session()
            close_session = True
        
        guild = session.query(Guild).get(guild_id)
        if not guild:
            guild = Guild(id=guild_id)
            session.add(guild)
            session.commit()
        
        user = session.query(User).filter_by(id=user_id, guild_id=guild_id).first()
        if not user:
            user = User(id=user_id, guild_id=guild_id)
            session.add(user)
            session.commit()
        
        user_data = {
            "coins": user.coins,
            "items": json.loads(user.items),
            "last_work": user.last_work,
            "last_steal": user.last_steal,
            "last_daily": user.last_daily,
            "job": user.job,
            "has_owned_vip": user.has_owned_vip,
            "last_invest": user.last_invest,
            "achievements": json.loads(user.achievements),
            "total_earnings": user.total_earnings,
            "steals": user.steals,
            "items_bought": user.items_bought,
            "elicit_works": user.elicit_works,
            "investment_profits": user.investment_profits,
            "trades": user.trades,
            "jackpots_won": user.jackpots_won
        }
        
        if close_session:
            session.close()
        
        return user_data

    def save_user_data(self, guild_id: str, user_id: str, data: dict, session=None):
        close_session = False
        if session is None:
            session = Session()
            close_session = True
        
        guild = session.query(Guild).get(guild_id)
        if not guild:
            guild = Guild(id=guild_id)
            session.add(guild)
        
        user = session.query(User).filter_by(id=user_id, guild_id=guild_id).first()
        if not user:
            user = User(id=user_id, guild_id=guild_id)
            session.add(user)
        
        user.coins = data["coins"]
        user.items = json.dumps(data["items"])
        user.last_work = data["last_work"]
        user.last_steal = data["last_steal"]
        user.last_daily = data["last_daily"]
        user.job = data["job"]
        user.has_owned_vip = data["has_owned_vip"]
        user.last_invest = data["last_invest"]
        user.achievements = json.dumps(data["achievements"])
        user.total_earnings = data["total_earnings"]
        user.steals = data["steals"]
        user.items_bought = data["items_bought"]
        user.elicit_works = data["elicit_works"]
        user.investment_profits = data["investment_profits"]
        user.trades = data["trades"]
        user.jackpots_won = data["jackpots_won"]
        
        session.commit()
        if close_session:
            session.close()

    def get_guild_data(self, guild_id: str):
        session = Session()
        guild = session.query(Guild).get(guild_id)
        if not guild:
            session.close()
            return {}
        
        guild_data = {}
        for user in guild.users:
            guild_data[user.id] = self.get_user_data(guild_id, user.id, session)
        
        session.close()
        return guild_data

    def save_guild_data(self, guild_id: str, data: dict):
        session = Session()
        guild = session.query(Guild).get(guild_id)
        if not guild:
            guild = Guild(id=guild_id)
            session.add(guild)
        
        for user_id, user_data in data.items():
            self.save_user_data(guild_id, user_id, user_data, session)
        
        session.commit()
        session.close()

    def check_achievements(self, user_id: str, guild_id: str):
        session = Session()
        user_data = self.get_user_data(guild_id, user_id, session)
        unlocked = user_data.get("achievements", [])
        new_unlocks = []
        for ach_name, ach_data in self.achievements.items():
            if ach_name not in unlocked and ach_data["condition"](user_data):
                new_unlocks.append(ach_name)
                unlocked.append(ach_name)
        user_data["achievements"] = unlocked
        self.save_user_data(guild_id, user_id, user_data, session)
        session.close()
        return new_unlocks

    def initialize_user_data(self):
        return {
            "coins": 0,
            "items": [],
            "last_work": 0,
            "last_steal": 0,
            "last_daily": 0,
            "job": None,
            "has_owned_vip": False,
            "last_invest": 0,
            "achievements": [],
            "total_earnings": 0,
            "steals": 0,
            "items_bought": 0,
            "elicit_works": 0,
            "investment_profits": 0,
            "trades": 0,
            "jackpots_won": 0
        }

    def create_embed(self, title, description, color=discord.Color.blue(), image_bytes=None):
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.datetime.utcnow()
        )
        if image_bytes:
            file = discord.File(image_bytes, filename="image.png")
            embed.set_image(url="attachment://image.png")
            return embed, file
        embed.set_footer(
            text=f"{config.BOT_NAME} v{config.BOT_VERSION}",
            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
        )
        return embed, None

    async def generate_image(self, message, busted=False, hospital=False):
        try:
            if hospital:
                img_path = self.hospital_image_path
            elif busted:
                img_path = self.busted_image_path
            else:
                img_path = self.base_image_path
            img = Image.open(img_path).convert("RGBA") if os.path.exists(img_path) else Image.new("RGBA", (600, 400), (100, 100, 100, 255))
            draw = ImageDraw.Draw(img)
            font_size = 60
            font = ImageFont.truetype(self.font_path, font_size) if os.path.exists(self.font_path) else ImageFont.load_default()

            text_color = (255, 255, 255)
            outline_color = (0, 0, 0)
            lines = message.split('\n')
            total_height = len(lines) * font_size
            start_y = (img.height - total_height) // 2

            for i, line in enumerate(lines):
                text_bbox = draw.textbbox((0, 0), line, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_x = (img.width - text_width) // 2
                text_y = start_y + i * font_size

                for dx, dy in [(-2, -2), (2, 2), (-2, 2), (2, -2)]:
                    draw.text((text_x + dx, text_y + dy), line, font=font, fill=outline_color)
                draw.text((text_x, text_y), line, font=font, fill=text_color)

            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            return buffer
        except Exception:
            return None

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        vip_role = discord.utils.get(guild.roles, name=self.vip_role_name)
        if not vip_role:
            try:
                await guild.create_role(
                    name=self.vip_role_name,
                    color=discord.Color.yellow(),
                    reason="CoinRush VIP role setup"
                )
            except discord.errors.Forbidden:
                if guild.owner:
                    await guild.owner.send(
                        f"Hello! I joined '{guild.name}' but lack 'Manage Roles' permission to create '{self.vip_role_name}' for CoinRush.\n"
                        f"Grant it and run `{BOT_PREFIX}coinrushsetup`."
                    )
            except Exception:
                pass

    @commands.command(name="coinrushsetup")
    async def coinrush_setup(self, ctx):
        if not ctx.guild:
            embed, _ = self.create_embed("❌ Guild-Only Command", f"{ctx.author.mention}, run this in a server!")
            await ctx.send(embed=embed, delete_after=5)
            return

        vip_role = discord.utils.get(ctx.guild.roles, name=self.vip_role_name)
        if vip_role:
            embed, _ = self.create_embed("✅ Role Exists", f"{ctx.author.mention}, '{self.vip_role_name}' is set up!")
            await ctx.send(embed=embed, delete_after=5)
            return

        try:
            await ctx.guild.create_role(
                name=self.vip_role_name,
                color=discord.Color.yellow(),
                reason=f"CoinRush VIP role setup by {ctx.author}"
            )
            embed, _ = self.create_embed("✅ Setup Complete", f"{ctx.author.mention}, '{self.vip_role_name}' created!")
            await ctx.send(embed=embed, delete_after=5)
        except discord.errors.Forbidden:
            embed, _ = self.create_embed("❌ Permission Denied", f"{ctx.author.mention}, I need 'Manage Roles' permission!")
            await ctx.send(embed=embed, delete_after=5)
        except Exception:
            embed, _ = self.create_embed("❌ Setup Failed", f"{ctx.author.mention}, an error occurred!")
            await ctx.send(embed=embed, delete_after=5)

    @commands.command(name="coinhelp")
    async def coin_help(self, ctx):
        if not ctx.guild:
            embed, _ = self.create_embed("❌ Guild-Only Game", f"{ctx.author.mention}, CoinRush is guild-only!")
            await ctx.send(embed=embed, delete_after=5)
            return

        help_text = (
            f"**CoinRush Commands**\n"
            f"`{BOT_PREFIX}coin` - Start/manage game.\n"
            f"`{BOT_PREFIX}setjob <job>` - Pick a job (or list).\n"
            f"`{BOT_PREFIX}quitjob` - Quit job.\n"
            f"`{BOT_PREFIX}daily` - Claim daily coins.\n"
            f"`{BOT_PREFIX}trade` - Trade coins/items.\n"
            f"`{BOT_PREFIX}coinleader` - Top coin holders.\n"
            f"`{BOT_PREFIX}achievements` - View your achievements.\n"
            f"`{BOT_PREFIX}coinhelp` - This menu.\n"
            f"`{BOT_PREFIX}coinrushsetup` - Setup VIP role.\n\n"
            f"**How to Play**\n"
            f"- Elicit jobs (e.g., Drug Dealer) risk busts; all risk hospital bills.\n"
            f"- Items like Smoke Bomb, Lockpick Set, and Medkit can be used in Work/Steal actions.\n"
            f"- Invest coins for potential profits or losses.\n"
            f"- 'VIP Badge' offers 95% theft protection + ⭐VIP role.\n"
            f"- Casino: Bet coins in slots for a chance at big wins!\n"
            f"- Unlock achievements for bragging rights!"
        )
        embed, _ = self.create_embed("CoinRush Help", help_text)
        await ctx.send(embed=embed)

    @commands.command(name="achievements")
    async def view_achievements(self, ctx):
        if not ctx.guild:
            embed, _ = self.create_embed("❌ Guild-Only Game", f"{ctx.author.mention}, CoinRush is guild-only!")
            await ctx.send(embed=embed, delete_after=5)
            return

        user_id = str(ctx.author.id)
        guild_id = str(ctx.guild.id)
        user_data = self.get_user_data(guild_id, user_id)
        if not user_data:
            user_data = self.initialize_user_data()
            self.save_user_data(guild_id, user_id, user_data)
        
        unlocked = user_data.get("achievements", [])
        ach_text = "🏆 **Your Achievements** 🏆\n\n"
        for ach_name, ach_data in self.achievements.items():
            status = "✅" if ach_name in unlocked else "🔒"
            ach_text += f"{status} **{ach_name}**: {ach_data['description']}\n"
        embed, _ = self.create_embed(f"{ctx.author.display_name}'s Achievements", ach_text)
        await ctx.send(embed=embed)

    @commands.command(name="setjob")
    async def set_job(self, ctx, *, job: str = None):
        if not ctx.guild:
            embed, _ = self.create_embed("❌ Guild-Only Game", f"{ctx.author.mention}, CoinRush is guild-only!")
            await ctx.send(embed=embed, delete_after=5)
            return

        user_id = str(ctx.author.id)
        guild_id = str(ctx.guild.id)
        user_data = self.get_user_data(guild_id, user_id)
        if not user_data:
            user_data = self.initialize_user_data()
            self.save_user_data(guild_id, user_id, user_data)

        jobs_list = "\n".join([f"{details['emoji']} {job_name}{' (Elicit)' if details['elicit'] else ''}" for job_name, details in self.jobs.items()])

        if not job:
            embed, _ = self.create_embed("Available Jobs", f"{ctx.author.mention}, choose:\n{jobs_list}\n\nUse `{BOT_PREFIX}setjob <job>`!")
            await ctx.send(embed=embed)
            return

        job = " ".join(word.capitalize() for word in job.split())
        job_found = None
        for job_name in self.jobs.keys():
            if job_name.lower() == job.lower():
                job_found = job_name
                break

        if not job_found:
            embed, _ = self.create_embed("❌ Invalid Job", f"{ctx.author.mention}, '{job}' isn’t valid!\n\nJobs:\n{jobs_list}")
            await ctx.send(embed=embed, delete_after=5)
            return

        if user_data["job"]:
            embed, _ = self.create_embed("❌ Employed", f"{ctx.author.mention}, you’re a {user_data['job']}!\nQuit with `{BOT_PREFIX}quitjob`.")
            await ctx.send(embed=embed, delete_after=5)
            return

        user_data["job"] = job_found
        self.save_user_data(guild_id, user_id, user_data)
        embed, _ = self.create_embed("Job Set!", f"{ctx.author.mention}, you’re a {job_found}! Earn coins with `{BOT_PREFIX}coin`.")
        await ctx.send(embed=embed, delete_after=5)

    @commands.command(name="quitjob")
    async def quit_job(self, ctx):
        if not ctx.guild:
            embed, _ = self.create_embed("❌ Guild-Only Game", f"{ctx.author.mention}, CoinRush is guild-only!")
            await ctx.send(embed=embed, delete_after=5)
            return

        user_id = str(ctx.author.id)
        guild_id = str(ctx.guild.id)
        user_data = self.get_user_data(guild_id, user_id)
        if not user_data:
            user_data = self.initialize_user_data()
            self.save_user_data(guild_id, user_id, user_data)

        if not user_data["job"]:
            embed, _ = self.create_embed("❌ No Job", f"{ctx.author.mention}, no job to quit!")
            await ctx.send(embed=embed, delete_after=5)
            return

        old_job = user_data["job"]
        user_data["job"] = None
        self.save_user_data(guild_id, user_id, user_data)
        embed, _ = self.create_embed("Job Quit!", f"{ctx.author.mention}, quit as {old_job}! Set a new job with `{BOT_PREFIX}setjob <job>`.")
        await ctx.send(embed=embed, delete_after=5)

    @commands.command(name="daily")
    async def daily_reward(self, ctx):
        if not ctx.guild:
            embed, _ = self.create_embed("❌ Guild-Only Game", f"{ctx.author.mention}, CoinRush is guild-only!")
            await ctx.send(embed=embed, delete_after=5)
            return

        user_id = str(ctx.author.id)
        guild_id = str(ctx.guild.id)
        user_data = self.get_user_data(guild_id, user_id)
        if not user_data:
            user_data = self.initialize_user_data()
            self.save_user_data(guild_id, user_id, user_data)

        now = datetime.datetime.utcnow().timestamp()
        last_daily = user_data["last_daily"]
        if now - last_daily < 86400:
            remaining = int(86400 - (now - last_daily))
            hours, remainder = divmod(remaining, 3600)
            minutes = remainder // 60
            await ctx.send(f"{ctx.author.mention}, next daily in {hours}h {minutes}m!", delete_after=5)
            return

        reward = random.randint(50, 100)
        user_data["coins"] += reward
        user_data["last_daily"] = now
        self.save_user_data(guild_id, user_id, user_data)
        image = await self.generate_image(f"Success!\n+{reward} Coins")
        embed, file = self.create_embed("Daily Reward!", f"{ctx.author.mention}, claimed {reward} coins!", image_bytes=image)
        await ctx.send(embed=embed, file=file, ephemeral=True, delete_after=6)

    @commands.command(name="trade")
    async def trade(self, ctx):
        if not ctx.guild:
            embed, _ = self.create_embed("❌ Guild-Only Game", f"{ctx.author.mention}, CoinRush is guild-only!")
            await ctx.send(embed=embed, delete_after=5)
            return

        user_id = str(ctx.author.id)
        guild_id = str(ctx.guild.id)
        guild_data = self.get_guild_data(guild_id)

        # Initialize user data if not present
        if user_id not in guild_data:
            guild_data[user_id] = self.initialize_user_data()
            self.save_user_data(guild_id, user_id, guild_data[user_id])

        tradable_players = [
            (uid, self.bot.get_user(int(uid)))
            for uid in guild_data.keys()
            if uid != user_id and self.bot.get_user(int(uid)) and not self.bot.get_user(int(uid)).bot
        ]
        if not tradable_players:
            embed, _ = self.create_embed("❌ No Partners", f"{ctx.author.mention}, no one to trade with!")
            await ctx.send(embed=embed, delete_after=5)
            return

        embed, _ = self.create_embed("🤝 Trade Hub", f"{ctx.author.mention}, select a player to trade with!")
        trade_select_view = TradeSelect(self, ctx.author, ctx.guild.id, None, tradable_players)
        message = await ctx.send(embed=embed, view=trade_select_view, delete_after=60)
        trade_select_view.message = message

    @commands.command(name="coinleader")
    async def coinleader(self, ctx):
        if not ctx.guild:
            embed, _ = self.create_embed("❌ Guild-Only Game", f"{ctx.author.mention}, CoinRush is guild-only!")
            await ctx.send(embed=embed, delete_after=5)
            return

        guild_id = str(ctx.guild.id)
        guild_data = self.get_guild_data(guild_id)
        if not guild_data:
            embed, _ = self.create_embed(f"Coinrush Leaderboard - {ctx.guild.name}", "No one has coins yet!")
            await ctx.send(embed=embed)
            return

        class LeaderboardView(View):
            def __init__(self, cog, guild, guild_data, page=0):
                super().__init__(timeout=60)
                self.cog = cog
                self.guild = guild
                self.guild_data = guild_data
                self.page = page
                self.per_page = 10
                self.message = None
                self.add_items()

            def get_sorted_players(self):
                return sorted(self.guild_data.items(), key=lambda x: x[1]["coins"], reverse=True)

            def format_leaderboard(self):
                sorted_players = self.get_sorted_players()
                total_pages = (len(sorted_players) + self.per_page - 1) // self.per_page
                start = self.page * self.per_page
                end = min(start + self.per_page, len(sorted_players))
                rank_emojis = ["🥇", "🥈", "🥉"] + [f"{i+1}️⃣" for i in range(3, 10)]
                leaderboard_text = "🏆Rank | 👤Player | ⚒️Job | 🪙Coins\n" + "-"*40 + "\n"
                for i, (uid, data) in enumerate(sorted_players[start:end], start=start):
                    member = self.guild.get_member(int(uid))
                    name = member.display_name if member else f"Unknown ({uid})"
                    job = data["job"] or "Unemployed"
                    job_emoji = self.cog.jobs[job]["emoji"] if job in self.cog.jobs else "❓"
                    rank_emoji = rank_emojis[i] if i < len(rank_emojis) else f"{i+1}"
                    leaderboard_text += f"{rank_emoji} | {name:<15} | {job_emoji} {job:<12} | {data['coins']}\n"
                leaderboard_text += f"\nPage {self.page + 1}/{total_pages}"
                return leaderboard_text

            def add_items(self):
                self.clear_items()
                sorted_players = self.get_sorted_players()
                total_pages = (len(sorted_players) + self.per_page - 1) // self.per_page
                self.add_item(Button(label="◀", style=discord.ButtonStyle.grey, custom_id="prev_page", disabled=self.page == 0))
                self.add_item(Button(label="▶", style=discord.ButtonStyle.grey, custom_id="next_page", disabled=self.page >= total_pages - 1))

            async def update_view(self):
                embed, _ = self.cog.create_embed(f"🏆 Coinrush Leaderboard - {self.guild.name}", self.format_leaderboard())
                self.add_items()
                await self.message.edit(embed=embed, view=self)

            @discord.ui.button(custom_id="prev_page")
            async def prev_page(self, interaction: discord.Interaction, button: Button):
                self.page -= 1
                await self.update_view()
                await interaction.response.defer()

            @discord.ui.button(custom_id="next_page")
            async def next_page(self, interaction: discord.Interaction, button: Button):
                self.page += 1
                await self.update_view()
                await interaction.response.defer()

        view = LeaderboardView(self, ctx.guild, guild_data)
        embed, _ = self.create_embed(f"🏆 Coinrush Leaderboard - {ctx.guild.name}", view.format_leaderboard())
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @commands.command(name="coin")
    async def coin_game(self, ctx):
        if not ctx.guild:
            embed, _ = self.create_embed("❌ Guild-Only Game", f"{ctx.author.mention}, CoinRush is guild-only!")
            await ctx.send(embed=embed, delete_after=5)
            return

        user_id = str(ctx.author.id)
        guild_id = str(ctx.guild.id)
        user_data = self.get_user_data(guild_id, user_id)
        if not user_data:
            user_data = self.initialize_user_data()
            self.save_user_data(guild_id, user_id, user_data)
        job = user_data["job"] or "Unemployed"
        welcome_message = "Welcome back to CoinRush!" if user_data["job"] else "Welcome to CoinRush!"

        class CoinRushView(View):
            def __init__(self, cog, user, guild_id):
                super().__init__(timeout=None)
                self.cog = cog
                self.user = user
                self.guild_id = guild_id
                self.message = None
                self.shop_message = None
                self.shop_open = False

            async def interaction_check(self, interaction: discord.Interaction) -> bool:
                if interaction.user.id != self.user.id:
                    await interaction.response.send_message("This UI is for someone else!", ephemeral=True)
                    return False
                return True

            async def notify_achievements(self, new_unlocks):
                if new_unlocks:
                    ach_text = "\n".join([f"🏆 **{ach}** - {self.cog.achievements[ach]['description']}" for ach in new_unlocks])
                    embed, _ = self.cog.create_embed("Achievement Unlocked!", f"{self.user.mention}\n{ach_text}")
                    await self.message.channel.send(embed=embed, delete_after=6)

            @discord.ui.button(label="Work", style=discord.ButtonStyle.green, emoji="💼")
            async def work_button(self, interaction: discord.Interaction, button: Button):
                user_id = str(self.user.id)
                guild_id = self.guild_id
                user_data = self.cog.get_user_data(guild_id, user_id)
                if not user_data:
                    user_data = self.cog.initialize_user_data()
                    self.cog.save_user_data(guild_id, user_id, user_data)

                now = datetime.datetime.utcnow().timestamp()
                last_work = user_data["last_work"]
                if now - last_work < 600:
                    remaining = int(600 - (now - last_work))
                    hours, remainder = divmod(remaining, 3600)
                    minutes = remainder // 60
                    await interaction.response.send_message(f"Work in {hours}h {minutes}m!", ephemeral=True)
                    return

                job = user_data["job"]
                if not job:
                    await interaction.response.send_message(f"Set a job with `{BOT_PREFIX}setjob <job>`!", ephemeral=True)
                    return

                if random.random() < 0.05:
                    bill = random.randint(20, 100)
                    if "Medkit" in user_data["items"] and random.random() < 0.5:
                        user_data["items"].remove("Medkit")
                        image = await self.cog.generate_image("Success!\nMedkit Used!")
                        embed, file = self.cog.create_embed("Hospital Avoided!", f"{self.user.mention}, used a Medkit to avoid a {bill} coin hospital bill!", image_bytes=image)
                    else:
                        user_data["coins"] -= bill
                        image = await self.cog.generate_image(f"Hospital!\n-{bill} Coins")
                        embed, file = self.cog.create_embed("Hospital Visit!", f"{self.user.mention}, bill: {bill} coins!", image_bytes=image)
                else:
                    pay_min = self.cog.jobs[job]["pay_min"]
                    pay_max = self.cog.jobs[job]["pay_max"]
                    for item in user_data["items"]:
                        if self.cog.shop_items[item]["effect"] == "work_stability":
                            pay_min += self.cog.shop_items[item]["value"]
                    earnings = random.randint(pay_min, pay_max)
                    for item in user_data["items"]:
                        if self.cog.shop_items[item]["effect"] == "work_boost":
                            earnings = int(earnings * (1 + self.cog.shop_items[item]["value"]))

                    if self.cog.jobs[job]["elicit"] and random.random() < 0.2:
                        fine = random.randint(50, 150)
                        if "Smoke Bomb" in user_data["items"] and random.random() < 0.3:
                            user_data["items"].remove("Smoke Bomb")
                            image = await self.cog.generate_image("Success!\nSmoke Bomb Used!")
                            embed, file = self.cog.create_embed("Bust Escaped!", f"{self.user.mention}, used a Smoke Bomb to escape a {fine} coin fine!", image_bytes=image)
                        else:
                            user_data["coins"] -= fine
                            image = await self.cog.generate_image(f"Busted!\n-{fine} Coins")
                            embed, file = self.cog.create_embed("Busted!", f"{self.user.mention}, busted as {job}! Paid {fine} coins!", image_bytes=image)
                    else:
                        user_data["coins"] += earnings
                        user_data["total_earnings"] += earnings
                        if self.cog.jobs[job]["elicit"]:
                            user_data["elicit_works"] += 1
                        image = await self.cog.generate_image(f"Success!\n+{earnings} Coins")
                        embed, file = self.cog.create_embed("Work Complete!", f"{self.user.mention}, earned {earnings} coins as {job}!", image_bytes=image)

                user_data["last_work"] = now
                self.cog.save_user_data(guild_id, user_id, user_data)
                new_unlocks = self.cog.check_achievements(user_id, self.guild_id)
                await interaction.response.send_message(embed=embed, file=file, ephemeral=True, delete_after=6)
                await self.notify_achievements(new_unlocks)

            @discord.ui.button(label="Steal", style=discord.ButtonStyle.red, emoji="🕵️")
            async def steal_button(self, interaction: discord.Interaction, button: Button):
                user_id = str(self.user.id)
                guild_id = self.guild_id
                user_data = self.cog.get_user_data(guild_id, user_id)
                if not user_data:
                    user_data = self.cog.initialize_user_data()
                    self.cog.save_user_data(guild_id, user_id, user_data)

                now = datetime.datetime.utcnow().timestamp()
                last_steal = user_data["last_steal"]
                if now - last_steal < 300:
                    remaining = int(300 - (now - last_steal))
                    hours, remainder = divmod(remaining, 3600)
                    minutes = remainder // 60
                    await interaction.response.send_message(f"Steal in {hours}h {minutes}m!", ephemeral=True)
                    return

                target = random.choice([m for m in interaction.guild.members if m != self.user and not m.bot])
                target_id = str(target.id)
                target_data = self.cog.get_user_data(guild_id, target_id)
                if not target_data:
                    target_data = self.cog.initialize_user_data()
                    self.cog.save_user_data(guild_id, target_id, target_data)

                if target_data["coins"] < 10 and not target_data["items"]:
                    await interaction.response.send_message(f"{target.mention} has nothing to steal!", ephemeral=True)
                    return

                steal_chance = 0.5
                for item in user_data["items"]:
                    if self.cog.shop_items[item]["effect"] == "steal_boost":
                        steal_chance += self.cog.shop_items[item]["value"]
                for item in target_data["items"]:
                    if self.cog.shop_items[item]["effect"] == "steal_protect":
                        steal_chance -= self.cog.shop_items[item]["value"]

                if random.random() < steal_chance:
                    if random.random() < 0.3 and target_data["items"]:
                        stolen_item = random.choice(target_data["items"])
                        user_data["items"].append(stolen_item)
                        target_data["items"].remove(stolen_item)
                        if stolen_item == "VIP Badge":
                            vip_role = discord.utils.get(interaction.guild.roles, name=self.cog.vip_role_name)
                            if vip_role:
                                try:
                                    await target.remove_roles(vip_role, reason="VIP Badge stolen")
                                    await self.user.add_roles(vip_role, reason="VIP Badge stolen")
                                except discord.errors.Forbidden:
                                    await interaction.channel.send("Failed to manage VIP role!")
                            target_data["has_owned_vip"] = False
                        result = f"Item: {stolen_item}"
                        image = await self.cog.generate_image(f"Success!\n{result}")
                        embed, file = self.cog.create_embed("Steal Successful!", f"{self.user.mention} stole {result} from {target.mention}!", image_bytes=image)
                    else:
                        stolen = random.randint(5, 20)
                        if "Lockpick Set" in user_data["items"] and random.random() < 0.4:
                            stolen = int(stolen * 1.5)
                            user_data["items"].remove("Lockpick Set")
                            result = f"{stolen} Coins (Lockpick Bonus!)"
                            image = await self.cog.generate_image(f"Success!\n{result}")
                            embed, file = self.cog.create_embed("Steal Successful!", f"{self.user.mention} used a Lockpick Set to steal {stolen} coins from {target.mention}!", image_bytes=image)
                        else:
                            result = f"{stolen} Coins"
                            image = await self.cog.generate_image(f"Success!\n{result}")
                            embed, file = self.cog.create_embed("Steal Successful!", f"{self.user.mention} stole {stolen} coins from {target.mention}!", image_bytes=image)
                        user_data["coins"] += stolen
                        target_data["coins"] -= stolen
                    user_data["steals"] += 1
                else:
                    penalty = min(10, max(0, user_data["coins"]))
                    if "Smoke Bomb" in user_data["items"] and random.random() < 0.3:
                        user_data["items"].remove("Smoke Bomb")
                        image = await self.cog.generate_image("Success!\nSmoke Bomb Used!")
                        embed, file = self.cog.create_embed("Escape Successful!", f"{self.user.mention} used a Smoke Bomb to escape a {penalty} coin penalty!", image_bytes=image)
                    else:
                        user_data["coins"] -= penalty
                        image = await self.cog.generate_image(f"Caught!\n-{penalty} Coins")
                        embed, file = self.cog.create_embed("Steal Failed!", f"{self.user.mention} caught stealing from {target.mention}, lost {penalty} coins!", image_bytes=image)

                user_data["last_steal"] = now
                self.cog.save_user_data(guild_id, user_id, user_data)
                self.cog.save_user_data(guild_id, target_id, target_data)
                new_unlocks = self.cog.check_achievements(user_id, self.guild_id)
                await interaction.response.send_message(embed=embed, file=file, ephemeral=True, delete_after=6)
                await self.notify_achievements(new_unlocks)

            @discord.ui.button(label="Shop", style=discord.ButtonStyle.blurple, emoji="🛒")
            async def shop_button(self, interaction: discord.Interaction, button: Button):
                if self.shop_open:
                    await interaction.response.send_message("Shop already open!", ephemeral=True)
                    return

                self.shop_open = True
                for item in self.children:
                    item.disabled = True
                await self.message.edit(view=self)

                user_id = str(self.user.id)
                guild_id = self.guild_id
                user_data = self.cog.get_user_data(guild_id, user_id)
                if not user_data:
                    user_data = self.cog.initialize_user_data()
                    self.cog.save_user_data(guild_id, user_id, user_data)

                shop_list = "\n".join([f"{item}: {data['cost']} coins ({data['effect']})" for item, data in self.cog.shop_items.items()])
                embed, _ = self.cog.create_embed("CoinRush Shop", f"Items:\n{shop_list}\n\nSelect to buy/sell!")

                class ShopSelect(Select):
                    def __init__(self, cog, user, guild_id, parent_view):
                        options = [discord.SelectOption(label=item, description=f"{data['cost']} coins") for item, data in cog.shop_items.items()]
                        super().__init__(placeholder="Buy an item", options=options)
                        self.cog = cog
                        self.user = user
                        self.guild_id = guild_id
                        self.parent_view = parent_view

                    async def callback(self, interaction: discord.Interaction):
                        await interaction.response.send_message("Processing...", ephemeral=True)
                        item = self.values[0]
                        cost = self.cog.shop_items[item]["cost"]
                        user_id = str(self.user.id)
                        guild_id = self.guild_id
                        user_data = self.cog.get_user_data(guild_id, user_id)
                        if not user_data:
                            user_data = self.cog.initialize_user_data()
                            self.cog.save_user_data(guild_id, user_id, user_data)

                        if user_data["coins"] < cost:
                            await interaction.followup.send(f"Not enough coins for {item} (need {cost})!", ephemeral=True)
                            return
                        if item in user_data["items"]:
                            await interaction.followup.send(f"You already own {item}!", ephemeral=True)
                            return
                        user_data["coins"] -= cost
                        user_data["items"].append(item)
                        user_data["items_bought"] += 1
                        if item == "VIP Badge":
                            user_data["has_owned_vip"] = True
                            vip_role = discord.utils.get(interaction.guild.roles, name=self.cog.vip_role_name)
                            if vip_role:
                                try:
                                    await self.user.add_roles(vip_role, reason="VIP Badge purchased")
                                except discord.errors.Forbidden:
                                    await interaction.followup.send("Failed to assign VIP role!", ephemeral=True)
                        self.cog.save_user_data(guild_id, user_id, user_data)
                        image = await self.cog.generate_image(f"Success!\nBought {item}!")
                        embed, file = self.cog.create_embed("Purchase Complete!", f"{self.user.mention} bought {item} for {cost} coins!", image_bytes=image)
                        new_unlocks = self.cog.check_achievements(user_id, self.guild_id)
                        await interaction.followup.send(embed=embed, file=file, ephemeral=True, delete_after=6)
                        await self.parent_view.notify_achievements(new_unlocks)

                class SellSelect(Select):
                    def __init__(self, cog, user, guild_id, parent_view):
                        user_id = str(user.id)
                        guild_id = cog.guild_id
                        user_data = cog.get_user_data(guild_id, user_id)
                        if not user_data:
                            user_data = cog.initialize_user_data()
                            cog.save_user_data(guild_id, user_id, user_data)
                        options = [discord.SelectOption(label=item, description=f"Sell for {cog.shop_items[item]['sell_price']} coins")
                                  for item in set(user_data["items"])] if user_data["items"] else [discord.SelectOption(label="No items", description="Nothing to sell")]
                        super().__init__(placeholder="Sell an item", options=options)
                        self.cog = cog
                        self.user = user
                        self.guild_id = guild_id
                        self.parent_view = parent_view

                    async def callback(self, interaction: discord.Interaction):
                        await interaction.response.defer()
                        item = self.values[0]
                        if item == "No items":
                            await interaction.followup.send("No items to sell!", ephemeral=True)
                            return
                        user_id = str(self.user.id)
                        guild_id = self.guild_id
                        user_data = self.cog.get_user_data(guild_id, user_id)
                        if not user_data:
                            user_data = self.cog.initialize_user_data()
                            self.cog.save_user_data(guild_id, user_id, user_data)
                        sell_price = self.cog.shop_items[item]["sell_price"]
                        user_data["coins"] += sell_price
                        user_data["items"].remove(item)
                        if item == "VIP Badge" and "VIP Badge" not in user_data["items"]:
                            vip_role = discord.utils.get(interaction.guild.roles, name=self.cog.vip_role_name)
                            if vip_role:
                                try:
                                    await self.user.remove_roles(vip_role, reason="VIP Badge sold")
                                except discord.errors.Forbidden:
                                    await interaction.followup.send("Failed to remove VIP role!", ephemeral=True)
                            user_data["has_owned_vip"] = False
                        self.cog.save_user_data(guild_id, user_id, user_data)
                        image = await self.cog.generate_image(f"Success!\nSold {item}!")
                        embed, file = self.cog.create_embed("Sale Complete!", f"{self.user.mention} sold {item} for {sell_price} coins!", image_bytes=image)
                        await interaction.followup.send(embed=embed, file=file, ephemeral=True, delete_after=6)

                shop_view = View()
                shop_view.add_item(ShopSelect(self.cog, self.user, self.guild_id, self))
                shop_view.add_item(SellSelect(self.cog, self.user, self.guild_id, self))
                shop_view.add_item(Button(label="Close Shop", style=discord.ButtonStyle.red, emoji="❌", custom_id="close_shop"))

                async def close_shop_callback(interaction: discord.Interaction):
                    if interaction.user.id != self.user.id:
                        await interaction.response.send_message("Only the owner can close!", ephemeral=True)
                        return
                    self.shop_open = False
                    for item in self.children:
                        item.disabled = False
                    await self.message.edit(view=self)
                    if self.shop_message:
                        try:
                            await self.shop_message.delete()
                        except (discord.errors.Forbidden, discord.errors.NotFound):
                            pass
                        self.shop_message = None
                    await interaction.response.send_message("Shop closed!", ephemeral=True)

                for item in shop_view.children:
                    if item.custom_id == "close_shop":
                        item.callback = close_shop_callback

                self.shop_message = await interaction.channel.send(embed=embed, view=shop_view, delete_after=60)
                await interaction.response.defer()

            @discord.ui.button(label="Balance", style=discord.ButtonStyle.grey, emoji="💰")
            async def balance_button(self, interaction: discord.Interaction, button: Button):
                user_id = str(self.user.id)
                guild_id = self.guild_id
                user_data = self.cog.get_user_data(guild_id, user_id)
                if not user_data:
                    user_data = self.cog.initialize_user_data()
                    self.cog.save_user_data(guild_id, user_id, user_data)

                if user_data["coins"] == 1337:
                    easter_egg_message = base64.b64decode(self.cog.easter_egg_encoded).decode('utf-8')
                    embed, _ = self.cog.create_embed(
                        "1337 Easter Egg!",
                        f"{self.user.mention}, magic number hit!\n\n*{easter_egg_message}*"
                    )
                else:
                    items = ", ".join(user_data["items"]) if user_data["items"] else "None"
                    job = user_data["job"] or "Unemployed"
                    job_emoji = self.cog.jobs[job]["emoji"] if job in self.cog.jobs else "❓"
                    ach_count = len(user_data["achievements"])
                    embed, _ = self.cog.create_embed(
                        "Your Balance",
                        f"{self.user.mention}\n🪙 Coins: {user_data['coins']}\n{job_emoji} Job: {job}\n🎒 Items: {items}\n🏆 Achievements: {ach_count}/{len(self.cog.achievements)}"
                    )
                await interaction.response.send_message(embed=embed, ephemeral=True)

            @discord.ui.button(label="Invest", style=discord.ButtonStyle.grey, emoji="📈")
            async def invest_button(self, interaction: discord.Interaction, button: Button):
                user_id = str(self.user.id)
                guild_id = self.guild_id
                user_data = self.cog.get_user_data(guild_id, user_id)
                if not user_data:
                    user_data = self.cog.initialize_user_data()
                    self.cog.save_user_data(guild_id, user_id, user_data)

                now = datetime.datetime.utcnow().timestamp()
                last_invest = user_data.get("last_invest", 0)
                if now - last_invest < 1800:
                    remaining = int(1800 - (now - last_invest))
                    hours, remainder = divmod(remaining, 3600)
                    minutes = remainder // 60
                    await interaction.response.send_message(f"Invest again in {minutes}m!", ephemeral=True)
                    return

                if user_data["coins"] < 50:
                    await interaction.response.send_message("You need at least 50 coins to invest!", ephemeral=True)
                    return

                investment = min(random.randint(50, 200), user_data["coins"])
                user_data["coins"] -= investment
                success_chance = 0.6 if user_data["job"] == "Crypto Investor" else 0.5
                if random.random() < success_chance:
                    profit = int(investment * random.uniform(1.2, 2.0))
                    user_data["coins"] += profit
                    user_data["investment_profits"] += profit - investment
                    image = await self.cog.generate_image(f"Success!\n+{profit - investment} Coins")
                    embed, file = self.cog.create_embed("Investment Success!", f"{self.user.mention} invested {investment} coins and earned {profit} coins!", image_bytes=image)
                else:
                    loss = investment
                    image = await self.cog.generate_image(f"Failed!\n-{loss} Coins")
                    embed, file = self.cog.create_embed("Investment Failed!", f"{self.user.mention} lost {loss} coins in a bad investment!", image_bytes=image)

                user_data["last_invest"] = now
                self.cog.save_user_data(guild_id, user_id, user_data)
                new_unlocks = self.cog.check_achievements(user_id, self.guild_id)
                await interaction.response.send_message(embed=embed, file=file, ephemeral=True, delete_after=6)
                await self.notify_achievements(new_unlocks)

            @discord.ui.button(label="Trade", style=discord.ButtonStyle.grey, emoji="🤝")
            async def trade_button(self, interaction: discord.Interaction, button: Button):
                if self.shop_open:
                    await interaction.response.send_message("Finish current task first!", ephemeral=True)
                    return

                if self.shop_message:
                    try:
                        await self.shop_message.delete()
                    except (discord.errors.Forbidden, discord.errors.NotFound):
                        pass
                    self.shop_message = None

                self.shop_open = True
                for item in self.children:
                    item.disabled = True
                await self.message.edit(view=self)

                user_id = str(self.user.id)
                guild_id = self.guild_id
                guild_data = self.cog.get_guild_data(guild_id)
                if user_id not in guild_data:
                    guild_data[user_id] = self.cog.initialize_user_data()
                    self.cog.save_user_data(guild_id, user_id, guild_data[user_id])

                tradable_players = [
                    (uid, self.cog.bot.get_user(int(uid)))
                    for uid in guild_data.keys()
                    if uid != user_id and self.cog.bot.get_user(int(uid)) and not self.cog.bot.get_user(int(uid)).bot
                ]
                if not tradable_players:
                    await interaction.response.send_message("No valid trade partners!", ephemeral=True)
                    self.shop_open = False
                    for item in self.children:
                        item.disabled = False
                    await self.message.edit(view=self)
                    return

                embed, _ = self.cog.create_embed("🤝 Trade Hub", f"{self.user.mention}, select a player to trade with!")
                trade_select_view = TradeSelect(self.cog, self.user, self.guild_id, self, tradable_players)
                self.shop_message = await interaction.channel.send(embed=embed, view=trade_select_view, delete_after=60)
                trade_select_view.message = self.shop_message
                await interaction.response.send_message("Trade hub opened!", ephemeral=True)

            @discord.ui.button(label="Casino", style=discord.ButtonStyle.grey, emoji="🎰")
            async def casino_button(self, interaction: discord.Interaction, button: Button):
                if self.shop_open:
                    await interaction.response.send_message("Finish current task first!", ephemeral=True)
                    return

                self.shop_open = True
                for item in self.children:
                    item.disabled = True
                await self.message.edit(view=self)

                user_id = str(self.user.id)
                guild_id = self.guild_id
                user_data = self.cog.get_user_data(guild_id, user_id)
                if not user_data:
                    user_data = self.cog.initialize_user_data()
                    self.cog.save_user_data(guild_id, user_id, user_data)

                embed, _ = self.cog.create_embed("🎰 CoinRush Casino", f"{self.user.mention}, welcome to the casino!\nType a bet amount to play slots (e.g., '50').\nMatch 3 symbols to win!")
                self.shop_message = await interaction.channel.send(embed=embed, delete_after=60)
                await interaction.response.defer()

                def check(m):
                    return m.author.id == self.user.id and m.channel == interaction.channel and m.content.isdigit()

                try:
                    msg = await self.cog.bot.wait_for("message", check=check, timeout=30)
                    bet = int(msg.content)
                    if bet < 1:
                        await interaction.channel.send("Bet must be at least 1 coin!", delete_after=5)
                        self.shop_open = False
                        for item in self.children:
                            item.disabled = False
                        await self.message.edit(view=self)
                        await self.shop_message.delete()
                        return
                    if user_data["coins"] < bet:
                        await interaction.channel.send(f"Not enough coins! You have {user_data['coins']} coins.", delete_after=5)
                        self.shop_open = False
                        for item in self.children:
                            item.disabled = False
                        await self.message.edit(view=self)
                        await self.shop_message.delete()
                        return

                    user_data["coins"] -= bet
                    result = [random.choice(["🍒", "🍋", "💎", "7️⃣"]) for _ in range(3)]
                    if result[0] == result[1] == result[2]:
                        winnings = bet * 5
                        user_data["coins"] += winnings
                        user_data["jackpots_won"] = user_data.get("jackpots_won", 0) + 1
                        image = await self.cog.generate_image(f"Success!\n+{winnings} Coins")
                        embed, file = self.cog.create_embed("🎰 Jackpot!", f"{self.user.mention} spun {result} and won {winnings} coins!", image_bytes=image)
                    else:
                        image = await self.cog.generate_image(f"Failed!\n-{bet} Coins")
                        embed, file = self.cog.create_embed("🎰 No Luck!", f"{self.user.mention} spun {result} and lost {bet} coins.", image_bytes=image)

                    self.cog.save_user_data(guild_id, user_id, user_data)
                    new_unlocks = self.cog.check_achievements(user_id, self.guild_id)
                    await interaction.channel.send(embed=embed, file=file, delete_after=6)
                    await self.notify_achievements(new_unlocks)

                except asyncio.TimeoutError:
                    await interaction.channel.send("Casino timed out!", delete_after=5)

                self.shop_open = False
                for item in self.children:
                    item.disabled = False
                await self.message.edit(view=self)
                await self.shop_message.delete()

            @discord.ui.button(label="Finish", style=discord.ButtonStyle.red, emoji="🏁")
            async def finish_button(self, interaction: discord.Interaction, button: Button):
                for item in self.children:
                    item.disabled = True
                embed, _ = self.cog.create_embed("Game Over", f"{self.user.mention}, session ended!")
                self.shop_open = False
                try:
                    await interaction.response.edit_message(embed=embed, view=self)
                    if self.shop_message:
                        try:
                            await self.shop_message.delete()
                        except (discord.errors.Forbidden, discord.errors.NotFound):
                            pass
                        self.shop_message = None
                except discord.errors.HTTPException:
                    await interaction.channel.send("Session ended, but couldn’t update UI!")
                self.stop()

        embed, _ = self.create_embed("CoinRush Game", f"{ctx.author.mention}, {welcome_message}\nJob: {job}\nPlay below!")
        view = CoinRushView(self, ctx.author, ctx.guild.id)
        message = await ctx.send(embed=embed, view=view)
        view.message = message

class TradeSelect(View):
    def __init__(self, cog, user, guild_id, parent_view, targets):
        super().__init__(timeout=60)
        self.cog = cog
        self.user = user
        self.guild_id = guild_id
        self.parent_view = parent_view
        self.targets = targets
        self.message = None
        self.add_items()

    def add_items(self):
        options = [discord.SelectOption(label=target.display_name, value=str(target.id)) for _, target in self.targets]
        select = Select(placeholder="Choose a trade partner", options=options[:25], custom_id="trade_select")
        select.callback = self.trade_select_callback
        self.add_item(select)
        cancel_button = Button(label="Cancel", style=discord.ButtonStyle.red, emoji="❌", custom_id="close_trade")
        cancel_button.callback = self.cancel_callback
        self.add_item(cancel_button)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("Only the initiator can interact!", ephemeral=True)
            return False
        return True

    async def trade_select_callback(self, interaction: discord.Interaction):
        target_id = interaction.data["values"][0]
        target = self.cog.bot.get_user(int(target_id))
        guild_id = self.guild_id
        
        # Ensure both initiator and target have data
        initiator_data = self.cog.get_user_data(guild_id, str(self.user.id))
        if not initiator_data:
            initiator_data = self.cog.initialize_user_data()
            self.cog.save_user_data(guild_id, str(self.user.id), initiator_data)
        target_data = self.cog.get_user_data(guild_id, target_id)
        if not target_data:
            target_data = self.cog.initialize_user_data()
            self.cog.save_user_data(guild_id, target_id, target_data)

        class TradeView(View):
            def __init__(self, cog, initiator, target, guild_id, parent_view):
                super().__init__(timeout=60)
                self.cog = cog
                self.initiator = initiator
                self.target = target
                self.guild_id = guild_id
                self.parent_view = parent_view
                self.initiator_offer = {"coins": 0, "items": []}
                self.target_offer = {"coins": 0, "items": []}
                self.initiator_accepted = False
                self.target_accepted = False
                self.message = None

            async def interaction_check(self, interaction: discord.Interaction) -> bool:
                if interaction.user.id not in [self.initiator.id, self.target.id]:
                    await interaction.response.send_message("You’re not part of this trade!", ephemeral=True)
                    return False
                return True

            async def update_trade_message(self):
                embed, _ = self.cog.create_embed(
                    "Trade Request",
                    f"{self.initiator.mention} offers: {self.initiator_offer['coins']} coins, {', '.join(self.initiator_offer['items']) or 'None'} (Accepted: {self.initiator_accepted})\n"
                    f"{self.target.mention} offers: {self.target_offer['coins']} coins, {', '.join(self.target_offer['items']) or 'None'} (Accepted: {self.target_accepted})\n\n"
                    "Both must accept to complete."
                )
                try:
                    await self.message.edit(embed=embed, view=self)
                except discord.errors.NotFound:
                    pass

            @discord.ui.button(label="Offer Coins", style=discord.ButtonStyle.blurple)
            async def offer_coins(self, interaction: discord.Interaction, button: Button):
                user_id = str(interaction.user.id)
                guild_id = self.guild_id
                user_data = self.cog.get_user_data(guild_id, user_id)
                if not user_data:
                    user_data = self.cog.initialize_user_data()
                    self.cog.save_user_data(guild_id, user_id, user_data)
                offer = self.initiator_offer if interaction.user.id == self.initiator.id else self.target_offer
                await interaction.response.send_message("How many coins to offer?", ephemeral=True)
                def check(m):
                    return m.author.id == interaction.user.id and m.channel == interaction.channel and m.content.isdigit()
                try:
                    msg = await self.cog.bot.wait_for("message", check=check, timeout=30)
                    amount = int(msg.content)
                    offer["coins"] = amount
                    await interaction.followup.send(f"Offered {amount} coins!", ephemeral=True)
                    await self.update_trade_message()
                except asyncio.TimeoutError:
                    pass

            @discord.ui.button(label="Offer Item", style=discord.ButtonStyle.blurple)
            async def offer_item(self, interaction: discord.Interaction, button: Button):
                user_id = str(interaction.user.id)
                guild_id = self.guild_id
                user_data = self.cog.get_user_data(guild_id, user_id)
                if not user_data:
                    user_data = self.cog.initialize_user_data()
                    self.cog.save_user_data(guild_id, user_id, user_data)
                offer = self.initiator_offer if interaction.user.id == self.initiator.id else self.target_offer
                if not user_data["items"]:
                    await interaction.response.send_message("No items to offer!", ephemeral=True)
                    return
                items = ", ".join(user_data["items"])
                await interaction.response.send_message(f"Your items: {items}\nType item to offer (case insensitive):", ephemeral=True)
                def check(m):
                    return m.author.id == interaction.user.id and m.channel == interaction.channel and any(m.content.lower() == item.lower() for item in user_data["items"])
                try:
                    msg = await self.cog.bot.wait_for("message", check=check, timeout=30)
                    item_input = msg.content.lower()
                    item = next(i for i in user_data["items"] if i.lower() == item_input)
                    offer["items"].append(item)
                    await interaction.followup.send(f"Offered {item}!", ephemeral=True)
                    await self.update_trade_message()
                except asyncio.TimeoutError:
                    pass

            @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
            async def accept(self, interaction: discord.Interaction, button: Button):
                if interaction.user.id == self.initiator.id:
                    self.initiator_accepted = True
                    await interaction.response.send_message("You accepted!", ephemeral=True)
                elif interaction.user.id == self.target.id:
                    self.target_accepted = True
                    await interaction.response.send_message("You accepted!", ephemeral=True)

                await self.update_trade_message()

                if self.initiator_accepted and self.target_accepted:
                    guild_id = self.guild_id
                    initiator_id = str(self.initiator.id)
                    target_id = str(self.target.id)
                    
                    initiator_data = self.cog.get_user_data(guild_id, initiator_id)
                    if not initiator_data:
                        initiator_data = self.cog.initialize_user_data()
                        self.cog.save_user_data(guild_id, initiator_id, initiator_data)
                    target_data = self.cog.get_user_data(guild_id, target_id)
                    if not target_data:
                        target_data = self.cog.initialize_user_data()
                        self.cog.save_user_data(guild_id, target_id, target_data)

                    for item in self.initiator_offer["items"]:
                        if item not in initiator_data["items"]:
                            embed, _ = self.cog.create_embed("Trade Failed", f"{self.initiator.mention} doesn’t have {item}!")
                            await interaction.channel.send(embed=embed, delete_after=6)
                            self.parent_view.shop_open = False
                            for item in self.parent_view.children:
                                item.disabled = False
                            try:
                                await self.parent_view.message.edit(view=self.parent_view)
                            except discord.errors.NotFound:
                                pass
                            await self.message.delete()
                            self.stop()
                            return
                    for item in self.target_offer["items"]:
                        if item not in target_data["items"]:
                            embed, _ = self.cog.create_embed("Trade Failed", f"{self.target.mention} doesn’t have {item}!")
                            await interaction.channel.send(embed=embed, delete_after=6)
                            self.parent_view.shop_open = False
                            for item in self.parent_view.children:
                                item.disabled = False
                            try:
                                await self.parent_view.message.edit(view=self.parent_view)
                            except discord.errors.NotFound:
                                pass
                            await self.message.delete()
                            self.stop()
                            return

                    initiator_data["coins"] -= self.initiator_offer["coins"]
                    initiator_data["coins"] += self.target_offer["coins"]
                    target_data["coins"] -= self.target_offer["coins"]
                    target_data["coins"] += self.initiator_offer["coins"]

                    for item in self.initiator_offer["items"]:
                        initiator_data["items"].remove(item)
                        target_data["items"].append(item)
                        if item == "VIP Badge":
                            vip_role = discord.utils.get(interaction.guild.roles, name=self.cog.vip_role_name)
                            if vip_role:
                                try:
                                    await self.initiator.remove_roles(vip_role, reason="VIP Badge traded")
                                    await self.target.add_roles(vip_role, reason="VIP Badge received")
                                except discord.errors.Forbidden:
                                    await interaction.channel.send("Failed to manage VIP role!", delete_after=5)
                            initiator_data["has_owned_vip"] = False
                    for item in self.target_offer["items"]:
                        target_data["items"].remove(item)
                        initiator_data["items"].append(item)
                        if item == "VIP Badge":
                            vip_role = discord.utils.get(interaction.guild.roles, name=self.cog.vip_role_name)
                            if vip_role:
                                try:
                                    await self.target.remove_roles(vip_role, reason="VIP Badge traded")
                                    await self.initiator.add_roles(vip_role, reason="VIP Badge received")
                                except discord.errors.Forbidden:
                                    await interaction.channel.send("Failed to manage VIP role!", delete_after=5)
                            target_data["has_owned_vip"] = False

                    initiator_data["trades"] += 1
                    target_data["trades"] += 1
                    self.cog.save_user_data(guild_id, initiator_id, initiator_data)
                    self.cog.save_user_data(guild_id, target_id, target_data)
                    embed, _ = self.cog.create_embed(
                        "Trade Complete!",
                        f"{self.initiator.mention} gave: {self.initiator_offer['coins']} coins, {', '.join(self.initiator_offer['items']) or 'None'}\n"
                        f"{self.target.mention} gave: {self.target_offer['coins']} coins, {', '.join(self.target_offer['items']) or 'None'}"
                    )
                    await interaction.channel.send(embed=embed)
                    new_unlocks_initiator = self.cog.check_achievements(initiator_id, self.guild_id)
                    new_unlocks_target = self.cog.check_achievements(target_id, self.guild_id)
                    if new_unlocks_initiator:
                        embed, _ = self.cog.create_embed("Achievement Unlocked!", f"{self.initiator.mention}\n" + "\n".join([f"🏆 **{ach}**" for ach in new_unlocks_initiator]))
                        await interaction.channel.send(embed=embed, delete_after=6)
                    if new_unlocks_target:
                        embed, _ = self.cog.create_embed("Achievement Unlocked!", f"{self.target.mention}\n" + "\n".join([f"🏆 **{ach}**" for ach in new_unlocks_target]))
                        await interaction.channel.send(embed=embed, delete_after=6)
                    self.parent_view.shop_open = False
                    for item in self.parent_view.children:
                        item.disabled = False
                    if self.parent_view.message:
                        try:
                            await self.parent_view.message.edit(view=self.parent_view)
                        except discord.errors.NotFound:
                            pass
                    await self.message.delete()
                    self.stop()

            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji="❌")
            async def cancel(self, interaction: discord.Interaction, button: Button):
                embed, _ = self.cog.create_embed("Trade Cancelled", f"{interaction.user.mention} cancelled the trade.")
                await interaction.channel.send(embed=embed, delete_after=6)
                self.parent_view.shop_open = False
                for item in self.parent_view.children:
                    item.disabled = False
                if self.parent_view and self.parent_view.message:
                    try:
                        await self.parent_view.message.edit(view=self.parent_view)
                    except discord.errors.NotFound:
                        pass
                try:
                    await self.message.delete()
                except discord.errors.NotFound:
                    pass
                await interaction.response.send_message("Trade hub closed!", ephemeral=True)
                self.stop()

            async def on_timeout(self):
                if not self.message:
                    return
                embed, _ = self.cog.create_embed("Trade Timed Out", "Trade expired.")
                await self.message.channel.send(embed=embed, delete_after=6)
                self.parent_view.shop_open = False
                for item in self.parent_view.children:
                    item.disabled = False
                if self.parent_view and self.parent_view.message:
                    try:
                        await self.parent_view.message.edit(view=self.parent_view)
                    except discord.errors.NotFound:
                        pass
                try:
                    await self.message.delete()
                except discord.errors.NotFound:
                    pass
                self.stop()

        embed, _ = self.cog.create_embed(
            "Trade Request",
            f"{self.user.mention} wants to trade with {target.mention}!\nOffer below; both must accept."
        )
        trade_view = TradeView(self.cog, self.user, target, self.guild_id, self.parent_view or self)
        try:
            await self.message.delete()
            if self.parent_view:
                self.parent_view.shop_message = await interaction.channel.send(embed=embed, view=trade_view, delete_after=60)
                trade_view.message = self.parent_view.shop_message
            else:
                trade_view.message = await interaction.channel.send(embed=embed, view=trade_view, delete_after=60)
            await interaction.response.defer()
        except discord.errors.NotFound:
            if self.parent_view:
                self.parent_view.shop_open = False
                for item in self.parent_view.children:
                    item.disabled = False
                if self.parent_view.message:
                    await self.parent_view.message.edit(view=self.parent_view)
            embed, _ = self.cog.create_embed("Trade Failed", "Couldn’t start trade session!")
            await interaction.channel.send(embed=embed, delete_after=6)

    async def cancel_callback(self, interaction: discord.Interaction):
        embed, _ = self.cog.create_embed("Trade Hub Closed", f"{self.user.mention}, trade selection cancelled.")
        await interaction.channel.send(embed=embed, delete_after=6)
        if self.parent_view:
            self.parent_view.shop_open = False
            for item in self.parent_view.children:
                item.disabled = False
            if self.parent_view.message:
                try:
                    await self.parent_view.message.edit(view=self.parent_view)
                except discord.errors.NotFound:
                    pass
        try:
            await self.message.delete()
        except discord.errors.NotFound:
            pass
        await interaction.response.send_message("Trade hub closed!", ephemeral=True)
        self.stop()

    async def on_timeout(self):
        if not self.message:
            return
        embed, _ = self.cog.create_embed("Trade Hub Closed", f"{self.user.mention}, trade selection timed out.")
        await self.message.channel.send(embed=embed, delete_after=6)
        if self.parent_view:
            self.parent_view.shop_open = False
            for item in self.parent_view.children:
                item.disabled = False
            if self.parent_view.message:
                try:
                    await self.parent_view.message.edit(view=self.parent_view)
                except discord.errors.NotFound:
                    pass
        try:
            await self.message.delete()
        except discord.errors.NotFound:
            pass
        self.stop()

async def setup(bot):
    await bot.add_cog(CoinRush(bot))