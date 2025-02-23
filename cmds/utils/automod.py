import discord
from discord.ext import commands, tasks
import json
import os
import asyncio
import re
from datetime import datetime
import config

class AutoModUI(discord.ui.View):
    """Interactive UI for configuring auto-moderation settings."""
    def __init__(self, cog, guild_id):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild_id = guild_id
        self.settings = self.cog.get_guild_settings(guild_id)
        self.message = None

    async def update_embed(self, interaction):
        """Update the embed with current settings, Banned Words at bottom."""
        log_channel = await self.cog.get_log_channel(self.guild_id)
        warning_count = len(self.settings["warnings"])
        embed = self.cog.create_embed(
            "⚙️ Auto-Moderation Configuration",
            "Adjust settings using the controls below:",
            fields=[
                ("Status", f"{'✅ Enabled' if self.settings['enabled'] else '❌ Disabled'}"),
                ("Mute Threshold", f"{self.settings['mute_threshold']} warnings"),
                ("Ban Threshold", f"{self.settings['ban_threshold']} warnings"),
                ("Mute Duration", f"{self.settings['mute_duration']} min"),
                ("Default Offensive Words", f"{'✅ Enabled' if self.settings['ban_default_offensive'] else '❌ Disabled'}"),
                ("Log Channel", log_channel.mention if log_channel else "Not set"),
                ("Total Warnings", f"{warning_count}"),
                ("Custom Banned Words", f"```{', '.join(self.settings['banned_words']) or 'None'}```")
            ],
            color=discord.Color.dark_blue()
        )
        await interaction.response.edit_message(embed=embed, view=self)

    # Row 0: Core Controls
    @discord.ui.button(label="Toggle Enable", style=discord.ButtonStyle.primary, emoji="🔄", row=0)
    async def toggle_enable(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.settings["enabled"] = not self.settings["enabled"]
        self.cog.save_settings()
        await self.update_embed(interaction)

    @discord.ui.button(label="Toggle Offensive", style=discord.ButtonStyle.primary, emoji="🛡️", row=0)
    async def toggle_offensive(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.settings["ban_default_offensive"] = not self.settings["ban_default_offensive"]
        self.cog.save_settings()
        await self.update_embed(interaction)

    # Row 1: Thresholds and Duration
    @discord.ui.button(label="Set Mute Threshold", style=discord.ButtonStyle.secondary, emoji="📊", row=1)
    async def set_mute_threshold(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SetMuteThresholdModal(self))

    @discord.ui.button(label="Set Ban Threshold", style=discord.ButtonStyle.secondary, emoji="🚫", row=1)
    async def set_ban_threshold(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SetBanThresholdModal(self))

    @discord.ui.button(label="Set Duration", style=discord.ButtonStyle.secondary, emoji="⏱️", row=1)
    async def set_duration(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SetDurationModal(self))

    # Row 2: Word Management and Logging
    @discord.ui.button(label="Add Word", style=discord.ButtonStyle.grey, emoji="➕", row=2)
    async def add_word(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddWordModal(self))

    @discord.ui.button(label="Remove Word", style=discord.ButtonStyle.grey, emoji="➖", row=2)
    async def remove_word(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RemoveWordModal(self))

    @discord.ui.button(label="Set Log Channel", style=discord.ButtonStyle.grey, emoji="📜", row=2)
    async def set_log_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SetLogChannelModal(self))

    # Row 3: Clear and Finish
    @discord.ui.button(label="Clear Warnings", style=discord.ButtonStyle.red, emoji="🧹", row=3)
    async def clear_warnings(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.settings["warnings"] = []
        self.cog.save_settings()
        await self.update_embed(interaction)

    @discord.ui.button(label="Finish", style=discord.ButtonStyle.green, emoji="✅", row=3)
    async def finish(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True
        embed = self.cog.create_embed(
            "✅ Configuration Saved",
            "Settings have been updated successfully.",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        guild = self.cog.bot.get_guild(self.guild_id)
        member = guild.get_member(interaction.user.id)
        return member == guild.owner or member.guild_permissions.manage_guild

    async def on_timeout(self):
        if self.message:
            for item in self.children:
                item.disabled = True
            embed = self.cog.create_embed(
                "⏳ Session Expired",
                "This panel has timed out. Use `!automod` to start a new session.",
                color=discord.Color.orange()
            )
            try:
                await self.message.edit(embed=embed, view=self)
            except discord.NotFound:
                pass

class AddWordModal(discord.ui.Modal, title="Add Banned Word"):
    word = discord.ui.TextInput(label="Word to Ban", placeholder="Enter a word", max_length=50)

    def __init__(self, view):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        word = self.word.value.lower()
        if word not in self.view.settings["banned_words"]:
            self.view.settings["banned_words"].append(word)
            self.view.cog.save_settings()
        await self.view.update_embed(interaction)

class RemoveWordModal(discord.ui.Modal, title="Remove Banned Word"):
    word = discord.ui.TextInput(label="Word to Remove", placeholder="Enter a word", max_length=50)

    def __init__(self, view):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        word = self.word.value.lower()
        if word in self.view.settings["banned_words"]:
            self.view.settings["banned_words"].remove(word)
            self.view.cog.save_settings()
        await self.view.update_embed(interaction)

class SetMuteThresholdModal(discord.ui.Modal, title="Set Mute Threshold"):
    threshold = discord.ui.TextInput(label="Mute Threshold", placeholder="Enter a number (min 1)", style=discord.TextStyle.short)

    def __init__(self, view):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        try:
            value = int(self.threshold.value)
            if value < 1 or value >= self.view.settings["ban_threshold"]:
                raise ValueError
            self.view.settings["mute_threshold"] = value
            self.view.cog.save_settings()
            await self.view.update_embed(interaction)
        except ValueError:
            await interaction.response.send_message("❌ Please enter a number >= 1 and less than the ban threshold.", ephemeral=True)

class SetBanThresholdModal(discord.ui.Modal, title="Set Ban Threshold"):
    threshold = discord.ui.TextInput(label="Ban Threshold", placeholder="Enter a number (min mute threshold + 1)", style=discord.TextStyle.short)

    def __init__(self, view):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        try:
            value = int(self.threshold.value)
            if value <= self.view.settings["mute_threshold"]:
                raise ValueError
            self.view.settings["ban_threshold"] = value
            self.view.cog.save_settings()
            await self.view.update_embed(interaction)
        except ValueError:
            await interaction.response.send_message("❌ Please enter a number greater than the mute threshold.", ephemeral=True)

class SetDurationModal(discord.ui.Modal, title="Set Mute Duration"):
    duration = discord.ui.TextInput(label="Duration (min)", placeholder="Enter minutes (min 1)", style=discord.TextStyle.short)

    def __init__(self, view):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        try:
            value = int(self.duration.value)
            if value < 1:
                raise ValueError
            self.view.settings["mute_duration"] = value
            self.view.cog.save_settings()
            await self.view.update_embed(interaction)
        except ValueError:
            await interaction.response.send_message("❌ Please enter a number >= 1.", ephemeral=True)

class SetLogChannelModal(discord.ui.Modal, title="Set Logging Channel"):
    channel = discord.ui.TextInput(label="Channel ID", placeholder="Enter a channel ID", style=discord.TextStyle.short)

    def __init__(self, view):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel_id = int(self.channel.value)
            channel = self.view.cog.bot.get_channel(channel_id)
            if not channel or not isinstance(channel, discord.TextChannel) or channel.guild.id != self.view.guild_id:
                raise ValueError
            self.view.settings["log_channel"] = str(channel_id)
            self.view.cog.save_settings()
            await self.view.update_embed(interaction)
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid text channel ID from this guild.", ephemeral=True)

class AutoModeration(commands.Cog):
    DEFAULT_OFFENSIVE_WORDS = [
    # NSFW Terms (Profanity and Sexual Content)
    "fuck", "shit", "ass", "bitch", "damn",
    "cock", "dick", "pussy", "cunt", "tits",
    "asshole", "bastard", "whore", "slut", "fag",
    "faggot", "prick", "twat", "wank", "jerkoff",
    "blowjob", "porn", "sex", "nude", "cum",
    "semen", "vagina", "penis", "anal", "boob",
    "fuckboy", "shag", "bang", "screw", "nut",
    "jizz", "clit", "boner", "horny", "thot",
    "smut", "skank", "slut", "pimp", "dildo",

    # Racial Slurs and Derogatory Terms
    "nigger", "nigga", "coon", "spic", "chink",
    "gook", "kike", "wetback", "jap", "paki",
    "raghead", "cracker", "redskin", "negro", "slant",
    "dago", "wop", "gypsy", "mick", "yid",
    "beaner", "cholo", "zip", "oreo", "towelhead",
    "cameljockey", "gringo", "honky", "junglebunny", "sandnigger",

    # Additional Offensive Terms (Disabilities, Identities, etc.)
    "retard", "cripple", "tranny", "dyke", "queer",
    "homo", "sperg", "autist", "mong", "spaz",
    "idiot", "moron", "dumbass", "shithead", "piss",
    "lame", "freak", "weirdo", "psycho", "nutjob",
    "fairy", "pansy", "sissy", "perv", "creep",

    # Variants and Common Misspellings
    "fuk", "sh1t", "azz", "b1tch", "d1ck",
    "p0rn", "c0ck", "pu55y", "n1gger", "f4g",
    "sh!t", "a$$", "b!tch", "d!ck", "p0rno",
    "c*nt", "f*ck", "n*gga", "r*tard", "tr*nny"
    ]

    def __init__(self, bot):
        self.bot = bot
        self.data_dir = "data"
        os.makedirs(self.data_dir, exist_ok=True)
        self.settings_file = os.path.join(self.data_dir, "automod_data.json")
        self.settings = self.load_settings()
        self.url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        self.automod_task.start()

    def load_settings(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, "r") as f:
                try:
                    settings = json.load(f)
                    for guild_id in settings:
                        if "ban_default_offensive" not in settings[guild_id]:
                            settings[guild_id]["ban_default_offensive"] = False
                        if not isinstance(settings[guild_id].get("warnings"), list):
                            settings[guild_id]["warnings"] = [{"reason": "Legacy warning", "issuer": "Unknown", "timestamp": datetime.utcnow().isoformat(), "user_id": "unknown"}] if settings[guild_id].get("warnings", 0) > 0 else []
                    return settings
                except json.JSONDecodeError:
                    return {}
        return {}

    def save_settings(self):
        with open(self.settings_file, "w") as f:
            json.dump(self.settings, f, indent=4)

    def get_guild_settings(self, guild_id):
        guild_id_str = str(guild_id)
        if guild_id_str not in self.settings:
            self.settings[guild_id_str] = {
                "enabled": False,
                "banned_words": [],
                "mute_threshold": 5,
                "ban_threshold": 10,
                "mute_duration": 60,
                "warnings": [],
                "log_channel": None,
                "ban_default_offensive": False
            }
        else:
            if "warn_threshold" in self.settings[guild_id_str] and "mute_threshold" not in self.settings[guild_id_str]:
                self.settings[guild_id_str]["mute_threshold"] = self.settings[guild_id_str].pop("warn_threshold")
            if "mute_threshold" not in self.settings[guild_id_str]:
                self.settings[guild_id_str]["mute_threshold"] = 5
            if "ban_threshold" not in self.settings[guild_id_str]:
                self.settings[guild_id_str]["ban_threshold"] = 10
            if "mute_duration" not in self.settings[guild_id_str]:
                self.settings[guild_id_str]["mute_duration"] = 60
            if "warnings" not in self.settings[guild_id_str] or not isinstance(self.settings[guild_id_str]["warnings"], list):
                self.settings[guild_id_str]["warnings"] = [{"reason": "Legacy warning", "issuer": "Unknown", "timestamp": datetime.utcnow().isoformat(), "user_id": "unknown"}] if self.settings[guild_id_str].get("warnings", 0) > 0 else []
            if "enabled" not in self.settings[guild_id_str]:
                self.settings[guild_id_str]["enabled"] = False
            if "banned_words" not in self.settings[guild_id_str]:
                self.settings[guild_id_str]["banned_words"] = []
            if "log_channel" not in self.settings[guild_id_str]:
                self.settings[guild_id_str]["log_channel"] = None
            if "ban_default_offensive" not in self.settings[guild_id_str]:
                self.settings[guild_id_str]["ban_default_offensive"] = False
        self.save_settings()
        return self.settings[guild_id_str]

    def create_embed(self, title, description, color=discord.Color.blue(), fields=None):
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.utcnow()
        )
        if fields:
            for name, value in fields:
                embed.add_field(name=name, value=value, inline=True)
        embed.set_footer(
            text=f"{config.BOT_NAME} v{config.BOT_VERSION}",
            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
        )
        return embed

    async def send_temp_message(self, ctx, embed, delay=10):
        message = await ctx.send(embed=embed)
        await asyncio.sleep(delay)
        try:
            await message.delete()
        except discord.NotFound:
            pass

    async def get_log_channel(self, guild_id):
        settings = self.get_guild_settings(guild_id)
        channel_id = settings.get("log_channel")
        if channel_id:
            return self.bot.get_channel(int(channel_id))
        return None

    def get_current_time(self):
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    def contains_url(self, message):
        return self.url_pattern.search(message.content) is not None

    def get_effective_banned_words(self, settings):
        banned_words = settings["banned_words"].copy()
        if settings["ban_default_offensive"]:
            banned_words.extend(self.DEFAULT_OFFENSIVE_WORDS)
        return banned_words

    def cog_unload(self):
        self.automod_task.cancel()

    @tasks.loop(minutes=1)
    async def automod_task(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        guild_id_str = str(message.guild.id)
        settings = self.get_guild_settings(message.guild.id)
        log_channel = await self.get_log_channel(message.guild.id)
        timestamp = self.get_current_time()

        if log_channel:
            if message.attachments:
                file_names = [attachment.filename for attachment in message.attachments]
                embed = self.create_embed(
                    "📎 File Sent",
                    f"**User:** {message.author.mention}\n**Files:** {', '.join(file_names)}\n**Time:** {timestamp}",
                    color=discord.Color.blue()
                )
                await log_channel.send(embed=embed)

            if self.contains_url(message):
                urls = self.url_pattern.findall(message.content)
                embed = self.create_embed(
                    "🔗 URL Sent",
                    f"**User:** {message.author.mention}\n**URLs:** {', '.join(urls)}\n**Time:** {timestamp}",
                    color=discord.Color.blue()
                )
                await log_channel.send(embed=embed)

        if not settings["enabled"]:
            return

        content = message.content.lower()
        banned_words = self.get_effective_banned_words(settings)
        detected_word = next((word for word in banned_words if word in content), None)
        if detected_word:
            await message.delete()
            user_id_str = str(message.author.id)
            warning = {
                "reason": f"Used banned word: {detected_word}",
                "issuer": f"{self.bot.user.name} (AutoMod)",
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": user_id_str
            }
            settings["warnings"].append(warning)
            user_warnings = [w for w in settings["warnings"] if w.get("user_id", "unknown") == user_id_str]
            warning_count = len(user_warnings)
            self.save_settings()

            warn_embed = self.create_embed(
                "⚠️ Warning Issued",
                f"You received a warning in **{message.guild.name}**.",
                color=discord.Color.orange(),
                fields=[
                    ("Reason", warning["reason"]),
                    ("Issuer", warning["issuer"]),
                    ("Timestamp", warning["timestamp"]),
                    ("Warning Count", f"{warning_count}/{settings['mute_threshold']} Before Mute | (Ban at {settings['ban_threshold']})")
                ]
            )
            try:
                await message.author.send(embed=warn_embed)
            except discord.Forbidden:
                pass

            if log_channel:
                log_embed = self.create_embed(
                    "⚠️ Auto-Moderation Warning",
                    f"**User:** {message.author.mention} (`{message.author.id}`)",
                    color=discord.Color.orange(),
                    fields=[
                        ("Reason", warning["reason"]),
                        ("Issuer", warning["issuer"]),
                        ("Timestamp", warning["timestamp"]),
                        ("Warnings", f"{warning_count}/{settings['mute_threshold']} Before Mute | (Ban at {settings['ban_threshold']})")
                    ]
                )
                await log_channel.send(embed=log_embed)

            if warning_count >= settings["ban_threshold"]:
                try:
                    await message.author.ban(reason=f"Auto-moderation: Exceeded ban threshold ({warning_count}/{settings['ban_threshold']})")
                    ban_embed = self.create_embed(
                        "⛔ Banned",
                        f"You’ve been banned from **{message.guild.name}** for exceeding the warning threshold.",
                        color=discord.Color.red(),
                        fields=[
                            ("Warnings", f"{warning_count}/{settings['ban_threshold']}"),
                            ("Last Reason", warning["reason"]),
                            ("Timestamp", warning["timestamp"])
                        ]
                    )
                    await message.author.send(embed=ban_embed)

                    if log_channel:
                        log_embed = self.create_embed(
                            "⛔ Auto-Moderation Ban",
                            f"**User:** {message.author.mention} (`{message.author.id}`)",
                            color=discord.Color.red(),
                            fields=[
                                ("Reason", f"Exceeded ban threshold ({warning_count}/{settings['ban_threshold']})"),
                                ("Last Warning", warning["reason"]),
                                ("Timestamp", warning["timestamp"])
                            ]
                        )
                        await log_channel.send(embed=log_embed)
                    settings["warnings"] = [w for w in settings["warnings"] if w.get("user_id", "unknown") != user_id_str]
                    self.save_settings()
                except discord.Forbidden:
                    pass
            elif warning_count >= settings["mute_threshold"]:
                mute_role = discord.utils.get(message.guild.roles, name=config.TIMEOUT_ROLE_NAME)
                if not mute_role:
                    return
                try:
                    await message.author.add_roles(mute_role, reason=f"Auto-moderation: Exceeded mute threshold ({warning_count}/{settings['mute_threshold']})")
                    mute_embed = self.create_embed(
                        "🤐 Muted",
                        f"You’ve been muted in **{message.guild.name}** for {settings['mute_duration']} minutes.",
                        color=discord.Color.red(),
                        fields=[
                            ("Reason", warning["reason"]),
                            ("Issuer", warning["issuer"]),
                            ("Timestamp", warning["timestamp"]),
                            ("Warnings", f"{warning_count}/{settings['mute_threshold']} Before Mute | (Ban at {settings['ban_threshold']})")
                        ]
                    )
                    await message.author.send(embed=mute_embed)

                    if log_channel:
                        log_embed = self.create_embed(
                            "🤐 Auto-Moderation Mute",
                            f"**User:** {message.author.mention} (`{message.author.id}`)",
                            color=discord.Color.red(),
                            fields=[
                                ("Duration", f"{settings['mute_duration']} minutes"),
                                ("Reason", f"Exceeded mute threshold ({warning_count}/{settings['mute_threshold']})"),
                                ("Last Warning", warning["reason"]),
                                ("Timestamp", warning["timestamp"])
                            ]
                        )
                        await log_channel.send(embed=log_embed)

                    await asyncio.sleep(settings["mute_duration"] * 60)
                    await message.author.remove_roles(mute_role)
                    if log_channel:
                        log_embed = self.create_embed(
                            "🔊 Auto-Moderation Unmute",
                            f"**User:** {message.author.mention} (`{message.author.id}`)",
                            color=discord.Color.green(),
                            fields=[
                                ("Reason", "Mute duration expired"),
                                ("Timestamp", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
                            ]
                        )
                        await log_channel.send(embed=log_embed)
                except discord.Forbidden:
                    pass

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        log_channel = await self.get_log_channel(after.guild.id)
        if log_channel:
            timestamp = self.get_current_time()
            timeout_role = discord.utils.get(after.guild.roles, name=config.TIMEOUT_ROLE_NAME)
            if timeout_role:
                if timeout_role not in before.roles and timeout_role in after.roles:
                    embed = self.create_embed(
                        "🔇 User Muted",
                        f"**User:** {after.mention}\n**Time:** {timestamp}",
                        color=discord.Color.red()
                    )
                    await log_channel.send(embed=embed)
                elif timeout_role in before.roles and timeout_role not in after.roles:
                    embed = self.create_embed(
                        "🔊 User Unmuted",
                        f"**User:** {after.mention}\n**Time:** {timestamp}",
                        color=discord.Color.green()
                    )
                    await log_channel.send(embed=embed)

            if before.nick != after.nick:
                embed = self.create_embed(
                    "✏️ User Nickname Changed",
                    f"**User:** {after.mention}\n**Old Nickname:** {before.nick or 'None'}\n**New Nickname:** {after.nick or 'None'}\n**Time:** {timestamp}",
                    color=discord.Color.blue()
                )
                await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        log_channel = await self.get_log_channel(member.guild.id)
        if log_channel:
            timestamp = self.get_current_time()
            embed = self.create_embed(
                "👋 User Joined",
                f"**User:** {member.mention}\n**Account Created:** {member.created_at}\n**Time:** {timestamp}",
                color=discord.Color.green()
            )
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        log_channel = await self.get_log_channel(member.guild.id)
        if log_channel:
            timestamp = self.get_current_time()
            embed = self.create_embed(
                "👋 User Left",
                f"**User:** {member.mention}\n**Joined At:** {member.joined_at}\n**Time:** {timestamp}",
                color=discord.Color.red()
            )
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        log_channel = await self.get_log_channel(guild.id)
        if log_channel:
            timestamp = self.get_current_time()
            embed = self.create_embed(
                "🔨 User Banned",
                f"**User:** {user.mention}\n**User ID:** {user.id}\n**Time:** {timestamp}",
                color=discord.Color.red()
            )
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        log_channel = await self.get_log_channel(guild.id)
        if log_channel:
            timestamp = self.get_current_time()
            embed = self.create_embed(
                "🔓 User Unbanned",
                f"**User:** {user.mention}\n**User ID:** {user.id}\n**Time:** {timestamp}",
                color=discord.Color.green()
            )
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        log_channel = await self.get_log_channel(channel.guild.id)
        if log_channel:
            timestamp = self.get_current_time()
            embed = self.create_embed(
                "🆕 Channel Created",
                f"**Channel:** #{channel.name}\n**Type:** {channel.type}\n**Time:** {timestamp}",
                color=discord.Color.green()
            )
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        log_channel = await self.get_log_channel(channel.guild.id)
        if log_channel:
            timestamp = self.get_current_time()
            embed = self.create_embed(
                "❌ Channel Deleted",
                f"**Channel:** #{channel.name}\n**Type:** {channel.type}\n**Time:** {timestamp}",
                color=discord.Color.red()
            )
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        log_channel = await self.get_log_channel(member.guild.id)
        if log_channel:
            timestamp = self.get_current_time()
            if before.channel != after.channel:
                if after.channel:
                    embed = self.create_embed(
                        "🎤 User Joined Voice Channel",
                        f"**User:** {member.mention}\n**Channel:** {after.channel.name}\n**Time:** {timestamp}",
                        color=discord.Color.green()
                    )
                else:
                    embed = self.create_embed(
                        "🎤 User Left Voice Channel",
                        f"**User:** {member.mention}\n**Channel:** {before.channel.name}\n**Time:** {timestamp}",
                        color=discord.Color.red()
                    )
                await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        log_channel = await self.get_log_channel(role.guild.id)
        if log_channel:
            timestamp = self.get_current_time()
            embed = self.create_embed(
                "📝 Role Created",
                f"**Role:** {role.name}\n**Time:** {timestamp}",
                color=discord.Color.green()
            )
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        log_channel = await self.get_log_channel(role.guild.id)
        if log_channel:
            timestamp = self.get_current_time()
            embed = self.create_embed(
                "❌ Role Deleted",
                f"**Role:** {role.name}\n**Time:** {timestamp}",
                color=discord.Color.red()
            )
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        log_channel = await self.get_log_channel(after.guild.id)
        if log_channel:
            timestamp = self.get_current_time()
            if before.permissions != after.permissions or before.name != after.name:
                changes = []
                if before.name != after.name:
                    changes.append(f"Name: {before.name} → {after.name}")
                if before.permissions != after.permissions:
                    changes.append("Permissions Updated")
                embed = self.create_embed(
                    "⚙️ Role Updated",
                    f"**Role:** {after.name}\n**Changes:** {'; '.join(changes)}\n**Time:** {timestamp}",
                    color=discord.Color.blue()
                )
                await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if after.guild is None or after.author.bot:
            return
        log_channel = await self.get_log_channel(after.guild.id)
        if log_channel:
            timestamp = self.get_current_time()
            if before.content != after.content:
                embed = self.create_embed(
                    "✏️ Message Edited",
                    f"**User:** {after.author.mention}\n**Channel:** {after.channel.mention}\n**Old Message:** {before.content[:1000]}\n**New Message:** {after.content[:1000]}\n**Time:** {timestamp}",
                    color=discord.Color.blue()
                )
                await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.guild is None or message.author.bot:
            return
        log_channel = await self.get_log_channel(message.guild.id)
        if log_channel:
            timestamp = self.get_current_time()
            embed = self.create_embed(
                "🗑️ Message Deleted",
                f"**User:** {message.author.mention}\n**Channel:** {message.channel.mention}\n**Content:** {message.content[:1000]}\n**Time:** {timestamp}",
                color=discord.Color.red()
            )
            await log_channel.send(embed=embed)

    @commands.command(name="automod")
    async def automod(self, ctx):
        if not ctx.guild:
            embed = self.create_embed(
                "❌ Guild-Only Feature",
                "This command can only be used in a server, not in DMs.",
                color=discord.Color.red()
            )
            await self.send_temp_message(ctx, embed)
            return

        view = AutoModUI(self, ctx.guild.id)
        log_channel = await self.get_log_channel(ctx.guild.id)
        warning_count = len(self.get_guild_settings(ctx.guild.id)["warnings"])
        embed = self.create_embed(
            "⚙️ Auto-Moderation Configuration",
            "Adjust settings using the controls below:",
            fields=[
                ("Status", f"{'✅ Enabled' if self.get_guild_settings(ctx.guild.id)['enabled'] else '❌ Disabled'}"),
                ("Mute Threshold", f"{self.get_guild_settings(ctx.guild.id)['mute_threshold']} warnings"),
                ("Ban Threshold", f"{self.get_guild_settings(ctx.guild.id)['ban_threshold']} warnings"),
                ("Mute Duration", f"{self.get_guild_settings(ctx.guild.id)['mute_duration']} min"),
                ("Default Offensive Words", f"{'✅ Enabled' if self.get_guild_settings(ctx.guild.id)['ban_default_offensive'] else '❌ Disabled'}"),
                ("Log Channel", log_channel.mention if log_channel else "Not set"),
                ("Total Warnings", f"{warning_count}"),
                ("Custom Banned Words", f"```{', '.join(self.get_guild_settings(ctx.guild.id)['banned_words']) or 'None'}```")
            ],
            color=discord.Color.dark_blue()
        )
        view.message = await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(AutoModeration(bot))