import discord
import os
import random
import time
import aiosqlite
import asyncio
from discord.ext import commands
import discord.ext
import cogs.utils.miscfuncs as mf

bank = "./data/database.sqlite"


class database(commands.Cog):
    """Commands which utilize a message database."""

    def __init__(self, client):
        self.client = client
        self.nocaro_cooldowns = {}

    # events
    @commands.Cog.listener()
    async def on_ready(self):
        db = await aiosqlite.connect(bank, timeout=10)
        cursor = await db.cursor()
        await cursor.execute(
            "CREATE TABLE IF NOT EXISTS messages("
            "num INTEGER NOT NULL PRIMARY KEY,"
            ""
            "messageID INTEGER NOT NULL,"
            "channelID INTEGER NOT NULL,"
            "guildID INTEGER NOT NULL"
            ")"
        )
        print("Database ready")

    async def check_ignored(self, channel):
        async with aiosqlite.connect(bank) as db:
            cursor = await db.cursor()
            await cursor.execute(
                "SELECT * FROM ignore WHERE channelID = ?", (channel.id,)
            )
            result = await cursor.fetchone()
            if result is not None:
                return True
            else:
                return False

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def ignore(self, ctx, channel: discord.TextChannel):
        """Make Nocaro ignore a channel"""
        async with aiosqlite.connect(bank) as db:
            await db.execute(
                "INSERT INTO ignore (channelID, guildID) VALUES (?, ?)",
                (channel.id, ctx.guild.id),
            )
            await db.commit()

        await ctx.reply(f"Ignored {channel.mention}.")

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def unignore(self, ctx, channel: discord.TextChannel):
        """Make Nocaro not ignore a channel"""
        async with aiosqlite.connect(bank) as db:
            await db.execute("DELETE FROM ignore WHERE channelID = ?", (channel.id,))
            await db.commit()

        await ctx.reply(f"Unignored {channel.mention}.")

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        async with aiosqlite.connect(bank) as db:
            cursor = await db.cursor()
            await cursor.execute(
                "DELETE FROM messages WHERE messageID = ?", (message.id,)
            )
            await db.commit()

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        async with aiosqlite.connect(bank) as db:
            cursor = await db.cursor()
            await cursor.execute(
                "DELETE FROM messages WHERE channelID = ?", (channel.id,)
            )
            await db.commit()

    @commands.command(aliases=["privacy", "policy", "pp", "dinfo"])
    async def privacypolicy(self, ctx):
        """Short privacy policy."""
        await ctx.reply(
            "Nocaro stores **Message IDs** in a database. Not actual messages. This means that if you delete your message or remove Nocaro from your server, Nocaro will no longer be able to access said messages. Otherwise, Nocaro does not store any information related to you. Nocaro also does not contain any LLMs. Nocaro is not responsible for any messages it regurgitates. When Nocaro regurgitates messages, it only picks from messages in the channel its currently in. Your messages will not leave whatever server you are in.\nIf you do not agree to any of these terms, please remove Nocaro from your server.\n\nNocaro is open source: <https://github.com/Bobbyperson/nocaro>"
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        msg = str.lower(message.content)  # semi-redundant
        if message.author.bot:
            return
        if not message.content:
            return
        if msg[0] == ",":  # make sure its not a command
            return
        if msg in [
            "hit",
            "stand",
            "double",
            "split",
            "h",
            "s",
            "d",
            "p",
            "cash out",
            "c",
            "co",
        ]:
            return
        guild_member = message.guild.get_member(
            self.client.user.id
        )  # need member object
        if (
            "nocaro" in msg
            or (guild_member.nick and guild_member.nick in msg)
            or random.randint(1, 500) == 1
        ):
            if await self.check_ignored(message.channel):
                return
            user_id = message.author.id
            current_time = time.time()
            cooldown_period = 2  # Cooldown period in seconds

            # Check if the user is in cooldown
            if (
                user_id in self.nocaro_cooldowns
                and current_time - self.nocaro_cooldowns[user_id] < cooldown_period
            ):
                return
            async with aiosqlite.connect(bank) as db:
                cursor = await db.cursor()
                await cursor.execute(
                    "SELECT * FROM messages WHERE channelID = ?", (message.channel.id,)
                )
                rows = await cursor.fetchall()
                if not rows:
                    return
            for _ in range(10):
                chosen = random.choice(rows)
                orgchannel = await self.client.fetch_channel(
                    chosen[2]
                )  # lookup channel
                try:
                    message_to_send = await orgchannel.fetch_message(
                        chosen[1]
                    )  # lookup message
                except discord.NotFound:
                    async with aiosqlite.connect(bank) as db:
                        cursor = await db.cursor()
                        await cursor.execute(
                            "DELETE FROM messages WHERE messageID = ?", (chosen[1],)
                        )
                        await db.commit()
                    continue
                mentions = message_to_send.role_mentions
                if not any(role in mentions for role in message.guild.roles):
                    break

            await message.channel.send(
                discord.utils.escape_mentions(message_to_send.content)
            )  # send that bitch
            self.nocaro_cooldowns[user_id] = current_time
        else:
            async with aiosqlite.connect(bank) as db:
                cursor = await db.cursor()
                await cursor.execute(
                    f"INSERT INTO messages(messageID, channelID, guildID) values({message.id}, {message.channel.id}, {message.guild.id})"
                )
                await db.commit()
        if ("https://x.com" in msg or "https://twitter.com" in msg) and (
            "fixupx.com" not in msg
            and "fxtwitter.com" not in msg
            and "vxtwitter.com" not in msg
        ):
            try:
                await message.delete()
            except discord.Forbidden:
                return
            newmsg = msg.replace("x.com", "fixupx.com")
            newmsg = newmsg.replace("twitter.com", "fxtwitter.com")
            await mf.send_webhook(
                ctx=message,
                name=message.author.display_name,
                avatar=message.author.display_avatar,
                message=newmsg,
            )

    @commands.command()
    @commands.is_owner()
    async def moveoldtonew(self, ctx):
        async with aiosqlite.connect(bank) as db:
            cursor = await db.cursor()
            for filename in os.listdir("data"):
                if filename.endswith(".txt"):
                    with open("data/" + filename, "r", encoding="utf-8") as f:
                        file_lines = [line.rstrip() for line in f.readlines()]
                        for line in file_lines:
                            length = line.find("-")
                            message_id = line[length + 1 :]
                            channel_id = line[0:length]
                            await cursor.execute(
                                "INSERT INTO messages(messageID, channelID, guildID) values(?, ?, ?)",
                                (message_id, channel_id, int(filename[:-4])),
                            )
                        await db.commit()
                    os.remove("data/" + filename)
        await ctx.send("Done")

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, commands.BucketType.user)
    async def rmessage(self, ctx):
        """Send a random message."""
        async with aiosqlite.connect(bank) as db:
            cursor = await db.cursor()
            await cursor.execute(
                "SELECT * FROM messages WHERE channelID = ?", (ctx.channel.id,)
            )
            rows = await cursor.fetchall()
            if not rows:
                return
        for _ in range(10):
            chosen = random.choice(rows)
            orgchannel = await self.client.fetch_channel(chosen[2])  # lookup channel
            try:
                message_to_send = await orgchannel.fetch_message(
                    chosen[1]
                )  # lookup message
            except discord.NotFound:
                async with aiosqlite.connect(bank) as db:
                    cursor = await db.cursor()
                    await cursor.execute(
                        "DELETE FROM messages WHERE messageID = ?", (chosen[1],)
                    )
                    await db.commit()
                continue
            mentions = message_to_send.role_mentions
            if not any(role in mentions for role in ctx.guild.roles):
                break
        await mf.send_webhook(
            ctx=ctx,
            avatar=message_to_send.author.avatar,
            name=message_to_send.author.name,
            message=discord.utils.escape_mentions(message_to_send.content),
        )  # send that bitch

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def conversation(self, ctx, number: int = 5):
        """Generate a whole conversation between random users."""
        if number > 10:
            number = 10
        async with aiosqlite.connect(bank) as db:
            cursor = await db.cursor()
            await cursor.execute(
                "SELECT * FROM messages WHERE channelID = ?", (ctx.channel.id,)
            )
            rows = await cursor.fetchall()
            if not rows:
                return
        for _ in range(number):
            message_to_send = random.choice(rows)
            chosen = random.choice(rows)
            orgchannel = await self.client.fetch_channel(chosen[2])  # lookup channel
            try:
                message_to_send = await orgchannel.fetch_message(
                    chosen[1]
                )  # lookup message
            except discord.NotFound:
                async with aiosqlite.connect(bank) as db:
                    cursor = await db.cursor()
                    await cursor.execute(
                        "DELETE FROM messages WHERE messageID = ?", (chosen[1],)
                    )
                    await db.commit()
                continue
            mentions = message_to_send.role_mentions
            if any(role in mentions for role in ctx.guild.roles):
                continue
            await mf.send_webhook(
                ctx=ctx,
                avatar=message_to_send.author.avatar,
                name=message_to_send.author.name,
                message=discord.utils.escape_mentions(message_to_send.content),
            )
            await asyncio.sleep(1)


async def setup(client):
    await client.add_cog(database(client))
