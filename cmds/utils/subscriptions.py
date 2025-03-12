import discord
from discord.ext import commands, tasks
import sqlite3
from datetime import datetime, UTC, timedelta
import logging
from config import BOT_PREFIX, OWNER_ID, DEV_IDS, SUBSCRIPTION_ROLE, BOT_NAME, BOT_VERSION, ROLE_COLORS

logger = logging.getLogger(__name__)

class SubscriptionManager:
    def __init__(self, db_path="data/subscriptions.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the SQLite database and table."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    user_id INTEGER PRIMARY KEY,
                    start_datetime TEXT NOT NULL,
                    duration_days INTEGER NOT NULL,
                    CHECK (user_id > 0),
                    CHECK (duration_days >= 0)
                )
            """)
            conn.commit()

    def _execute(self, query, params=()):
        """Execute a query with error handling."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                conn.commit()
                return cursor
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            raise

    def add(self, user_id, duration_days):
        """Add or update a subscription."""
        self._execute(
            "INSERT OR REPLACE INTO subscriptions (user_id, start_datetime, duration_days) VALUES (?, ?, ?)",
            (user_id, datetime.now(UTC).isoformat(), duration_days)
        )

    def remove(self, user_id):
        """Remove a subscription."""
        self._execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))

    def contains(self, user_id):
        """Check if a user is subscribed and not expired."""
        row = self._execute("SELECT start_datetime, duration_days FROM subscriptions WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            return False
        start = datetime.fromisoformat(row["start_datetime"])
        duration = timedelta(days=row["duration_days"])
        return datetime.now(UTC) < start + duration

    def get_duration_remaining(self, user_id):
        """Calculate remaining subscription time."""
        row = self._execute("SELECT start_datetime, duration_days FROM subscriptions WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            return "Not subscribed"
        start = datetime.fromisoformat(row["start_datetime"])
        duration_days = row["duration_days"]
        if duration_days == 9999:
            return "Lifetime"
        end = start + timedelta(days=duration_days)
        remaining = end - datetime.now(UTC)
        return f"{remaining.days} days, {remaining.seconds // 3600} hours" if remaining.total_seconds() > 0 else "Expired"

    def get_time_subscribed(self, user_id):
        """Calculate how long a user has been subscribed."""
        row = self._execute("SELECT start_datetime FROM subscriptions WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            return "Not subscribed"
        start = datetime.fromisoformat(row["start_datetime"])
        duration = datetime.now(UTC) - start
        return f"{duration.days} days, {duration.seconds // 3600} hours"

    def get_subscribed_users(self):
        """Return a list of currently subscribed user IDs."""
        rows = self._execute("SELECT user_id, start_datetime, duration_days FROM subscriptions").fetchall()
        return [row["user_id"] for row in rows if self.contains(row["user_id"])]

class SubscriptionModal(discord.ui.Modal):
    def __init__(self, action, cog, ctx, duration_days=None):
        super().__init__(title=f"{action} Subscription")
        self.cog = cog
        self.ctx = ctx
        self.action = action
        self.duration_days = duration_days
        self.add_item(discord.ui.TextInput(label="User ID", placeholder="Enter a numeric user ID"))

    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission with deferral for async operations."""
        await interaction.response.defer(ephemeral=True)
        
        user_id_str = self.children[0].value.strip()
        try:
            user_id = int(user_id_str)
            if self.action == "Add" and self.duration_days is not None:
                await self.cog.handle_add_subscription(interaction, user_id, self.duration_days)
            elif self.action == "Check":
                await self.cog.handle_check_subscription(interaction, user_id)
        except ValueError:
            await interaction.followup.send(embed=self.cog.error_embed("Invalid User ID", "Please provide a valid numeric user ID."), ephemeral=True)

class SubscriptionLengthSelect(discord.ui.Select):
    def __init__(self, cog, ctx):
        self.cog = cog
        self.ctx = ctx
        options = [
            discord.SelectOption(label="1 Week", value="7", emoji="⏳"),
            discord.SelectOption(label="2 Weeks", value="14", emoji="⏳"),
            discord.SelectOption(label="1 Month", value="30", emoji="⏳"),
            discord.SelectOption(label="Lifetime", value="9999", emoji="⭐")
        ]
        super().__init__(placeholder="Select subscription length...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if await self.cog.check_interaction(interaction, self.ctx.author):
            await interaction.response.send_modal(SubscriptionModal("Add", self.cog, self.ctx, duration_days=int(self.values[0])))

class SubscribedUsersSelect(discord.ui.Select):
    def __init__(self, cog, ctx):
        self.cog = cog
        self.ctx = ctx
        subscribed_users = self.cog.subscribers.get_subscribed_users()
        options = [
            discord.SelectOption(label=str(user_id), value=str(user_id), description=f"Subscribed for {self.cog.subscribers.get_time_subscribed(user_id)}")
            for user_id in subscribed_users[:25]
        ] or [discord.SelectOption(label="No subscribers", value="none")]
        super().__init__(placeholder="View subscribed users...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if await self.cog.check_interaction(interaction, self.ctx.author):
            user_id = self.values[0]
            if user_id == "none":
                await interaction.response.send_message(embed=self.cog.info_embed("No Subscribers", "There are no active subscriptions."), ephemeral=True)
            else:
                await self.cog.handle_check_subscription(interaction, int(user_id))

class RemoveSubscriptionSelect(discord.ui.Select):
    def __init__(self, cog, ctx):
        self.cog = cog
        self.ctx = ctx
        subscribed_users = self.cog.subscribers.get_subscribed_users()
        options = [
            discord.SelectOption(label=str(user_id), value=str(user_id), description=f"Subscribed for {self.cog.subscribers.get_time_subscribed(user_id)}")
            for user_id in subscribed_users[:25]
        ] or [discord.SelectOption(label="No subscribers", value="none")]
        super().__init__(placeholder="Remove a subscriber...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if await self.cog.check_interaction(interaction, self.ctx.author):
            user_id = self.values[0]
            if user_id == "none":
                await interaction.response.send_message(embed=self.cog.info_embed("No Subscribers", "There are no active subscriptions to remove."), ephemeral=True)
            else:
                await self.cog.handle_remove_subscription(interaction, int(user_id))

class SubscriptionsView(discord.ui.View):
    def __init__(self, cog, ctx):
        super().__init__(timeout=300)
        self.cog = cog
        self.ctx = ctx
        self.requester = ctx.author
        self.message = None
        self.add_item(SubscriptionLengthSelect(self.cog, self.ctx))
        self.add_item(RemoveSubscriptionSelect(self.cog, self.ctx))
        self.add_item(SubscribedUsersSelect(self.cog, self.ctx))

    async def update_embed(self, closing=False):
        embed = discord.Embed(
            title="📋 Subscription Control Panel" if not closing else "📋 Panel Closed",
            color=discord.Color.blue() if not closing else discord.Color.greyple(),
            timestamp=datetime.now(UTC)
        ).set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png").set_footer(text=f"{BOT_NAME} v{BOT_VERSION}")
        embed.description = "Use the options below to manage subscriptions." if not closing else "The subscription control panel has been closed."
        if not closing:
            embed.add_field(name="Instructions", value=f"- Requested by: {self.requester.mention}\n- Only the requester (owner/dev) can use these controls.", inline=False)
        if self.message:
            await self.message.edit(embed=embed, view=self if not closing else None)

    @discord.ui.button(label="Check Subscription", style=discord.ButtonStyle.blurple, emoji="🔍")
    async def check_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await self.cog.check_interaction(interaction, self.requester):
            await interaction.response.send_modal(SubscriptionModal("Check", self.cog, self.ctx))

    @discord.ui.button(label="Close", style=discord.ButtonStyle.grey, emoji="❌")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await self.cog.check_interaction(interaction, self.requester):
            await self.update_embed(closing=True)
            self.stop()

    async def on_timeout(self):
        await self.update_embed(closing=True)
        self.stop()

class Subscriptions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.subscribers = SubscriptionManager()
        self.bot.subscribers = self.subscribers  # Make SubscriptionManager accessible globally
        self.check_expirations.start()

    def error_embed(self, title, description):
        return discord.Embed(title=f"❌ {title}", description=description, color=discord.Color.red(), timestamp=datetime.now(UTC)).set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png").set_footer(text=f"{BOT_NAME} v{BOT_VERSION}")

    def info_embed(self, title, description):
        return discord.Embed(title=f"📋 {title}", description=description, color=discord.Color.orange(), timestamp=datetime.now(UTC)).set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png").set_footer(text=f"{BOT_NAME} v{BOT_VERSION}")

    async def check_interaction(self, interaction: discord.Interaction, requester):
        if interaction.user != requester:
            await interaction.response.send_message(embed=self.error_embed("Access Denied", f"Only {requester.mention} (owner/dev) can use this panel."), ephemeral=True)
            return False
        return True

    async def assign_role(self, user_id):
        """Assign the subscription role to the user in any guild, optimized to stop after first success."""
        for guild in self.bot.guilds:
            member = guild.get_member(user_id)
            if member:
                role = discord.utils.get(guild.roles, name=SUBSCRIPTION_ROLE)
                if not role and self.bot.user.id in {OWNER_ID, *DEV_IDS}:
                    try:
                        role = await guild.create_role(name=SUBSCRIPTION_ROLE, color=ROLE_COLORS[SUBSCRIPTION_ROLE], reason="Subscription role creation")
                    except discord.Forbidden:
                        logger.warning(f"Failed to create role in {guild.name}: Insufficient permissions")
                        continue
                if role:
                    try:
                        await member.add_roles(role)
                        return True
                    except discord.Forbidden:
                        logger.warning(f"Failed to assign role in {guild.name}: Insufficient permissions")
                        continue
        return False

    async def remove_role(self, user_id):
        """Remove the subscription role from the user in any guild."""
        for guild in self.bot.guilds:
            member = guild.get_member(user_id)
            if member:
                role = discord.utils.get(guild.roles, name=SUBSCRIPTION_ROLE)
                if role:
                    try:
                        await member.remove_roles(role)
                        return True
                    except discord.Forbidden:
                        logger.warning(f"Failed to remove role in {guild.name}: Insufficient permissions")
                        continue
        return False

    async def handle_add_subscription(self, interaction: discord.Interaction, user_id: int, duration_days: int):
        """Handle adding a subscription with deferred response."""
        embed = discord.Embed(timestamp=datetime.now(UTC)).set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png").set_footer(text=f"{BOT_NAME} v{BOT_VERSION}")
        if self.subscribers.contains(user_id):
            embed.title, embed.description, embed.color = "❌ Already Subscribed", f"User ID `{user_id}` is already subscribed.", discord.Color.red()
        else:
            self.subscribers.add(user_id, duration_days)
            assigned = await self.assign_role(user_id)
            duration_text = "Lifetime" if duration_days == 9999 else f"{duration_days} days"
            embed.title, embed.description, embed.color = "✅ Subscription Added", f"User ID `{user_id}` added{' and assigned ' + SUBSCRIPTION_ROLE if assigned else ', but not found in any guild'} for {duration_text}.", discord.Color.green() if assigned else discord.Color.orange()
        await interaction.followup.send(embed=embed, ephemeral=True)

    async def handle_remove_subscription(self, interaction: discord.Interaction, user_id: int):
        embed = discord.Embed(timestamp=datetime.now(UTC)).set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png").set_footer(text=f"{BOT_NAME} v{BOT_VERSION}")
        if not self.subscribers.contains(user_id):
            embed.title, embed.description, embed.color = "❌ Not Subscribed", f"User ID `{user_id}` is not subscribed.", discord.Color.red()
        else:
            self.subscribers.remove(user_id)
            removed = await self.remove_role(user_id)
            embed.title, embed.description, embed.color = "✅ Subscription Removed", f"User ID `{user_id}` removed{' and ' + SUBSCRIPTION_ROLE + ' removed' if removed else ', but not found in any guild'}.", discord.Color.green() if removed else discord.Color.orange()
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def handle_check_subscription(self, interaction: discord.Interaction, user_id: int):
        """Handle checking a subscription with subscription status as a separate field."""
        embed = discord.Embed(title="📋 Subscription Status", description="", timestamp=datetime.now(UTC)).set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12724/12724695.png").set_footer(text=f"{BOT_NAME} v{BOT_VERSION}")
        
        is_subscribed = self.subscribers.contains(user_id)
        embed.add_field(name="User ID", value=f"`{user_id}`", inline=False)
        embed.add_field(name="Username", value=f"<@{user_id}>", inline=False)  # Clickable mention
        embed.add_field(name="Subscription Status", value="Subscribed" if is_subscribed else "Not Subscribed", inline=False)
        embed.add_field(name="Subscribed For", value=self.subscribers.get_time_subscribed(user_id), inline=True)
        embed.add_field(name="Remaining", value=self.subscribers.get_duration_remaining(user_id), inline=True)
        embed.color = discord.Color.green() if is_subscribed else discord.Color.red()
        
        # Check if the interaction is already responded to (deferred from modal)
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @tasks.loop(hours=1)
    async def check_expirations(self):
        """Check for expired subscriptions and remove them."""
        for user_id in self.subscribers.get_subscribed_users():
            if not self.subscribers.contains(user_id):
                await self.remove_role(user_id)
                self.subscribers.remove(user_id)
                logger.info(f"Removed expired subscription for user {user_id}")

    @check_expirations.before_loop
    async def before_check_expirations(self):
        await self.bot.wait_until_ready()

    @commands.command(name="subscriptions")
    @commands.check(lambda ctx: ctx.author.id in {OWNER_ID, *DEV_IDS})  # Restricted to owner/devs only
    async def subscriptions(self, ctx):
        """Manage subscriptions (owner/dev only)."""
        view = SubscriptionsView(self, ctx)
        view.message = await ctx.send(embed=discord.Embed(title="Loading Subscription Panel..."), view=view)
        await view.update_embed()

async def setup(bot):
    await bot.add_cog(Subscriptions(bot))