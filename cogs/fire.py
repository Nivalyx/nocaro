import discord
import aiosqlite
import time as t
import csv
import asyncpg
from discord.ext import commands
from discord.ext import tasks

bank = "./data/database.sqlite"

fire = "🔥"


async def add_msg(reacts, msg, fb_msg_id, fbid, emoji):
    cid = msg.channel.id
    mid = msg.id
    gid = msg.guild.id
    uid = msg.author.id
    message = msg.content
    insane = msg.created_at
    unix = insane.timestamp()

    db = await aiosqlite.connect(bank, timeout=10)
    cursor = await db.cursor()

    query = """
        INSERT INTO fire(
            reacts, channel_id, message_id, guild_id, user_id, fb_id, 
            message, attachments, timestamp, fb_msg_id, emoji
        ) 
        values(?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?)
    """
    parameters = (
        reacts,
        cid,
        mid,
        gid,
        uid,
        fbid,
        message,
        int(unix),
        fb_msg_id,
        emoji,
    )

    await cursor.execute(query, parameters)
    await db.commit()

    await cursor.close()
    await db.close()


async def edit_msg(reacts, msg):
    mid = msg.id
    message = msg.content
    message = message.replace(r"'", r"''")
    db = await aiosqlite.connect(bank, timeout=10)
    cursor = await db.cursor()
    await cursor.execute(
        f"UPDATE fire SET message = '{message}' WHERE message_id={mid}"
    )
    await cursor.execute(f"UPDATE fire SET reacts = {reacts} WHERE message_id={mid}")
    await db.commit()
    await cursor.close()
    await db.close()


async def get_element(element, value_name, value):
    db = await aiosqlite.connect(bank, timeout=10)
    cursor = await db.cursor()
    await cursor.execute(f"SELECT {element} FROM fire WHERE {value_name}={value}")
    result = await cursor.fetchone()
    await cursor.close()
    await db.close()
    if result:
        return result[0]
    return None


async def delete_element(valuename, value):
    db = await aiosqlite.connect(bank, timeout=10)
    cursor = await db.cursor()
    await cursor.execute(f"DELETE FROM fire WHERE {valuename}={value}")
    await cursor.close()
    await db.close()


class Fire(commands.Cog):
    """Starboard if it were awesome..."""

    def __init__(self, client):
        self.client = client
        self.weekly.add_exception_type(asyncpg.PostgresConnectionError)
        self.weekly.start()

    def cog_unload(self):
        self.weekly.cancel()

    async def add_to_board(self, added_msg, fireboard, total_reacts, emoji):
        exists = await get_element("fb_msg_id", "message_id", added_msg.id)
        if not exists:
            em = discord.Embed(
                color=discord.Color(0xFA43EE), description=added_msg.content
            )
            em.add_field(
                name="Original",
                value=f"[Message Link](https://discord.com/channels/{added_msg.guild.id}/{added_msg.channel.id}/{added_msg.id})",
                inline=True,
            )
            em.timestamp = added_msg.created_at
            em.set_author(name=added_msg.author.name, icon_url=added_msg.author.avatar)
            if added_msg.attachments:
                file = added_msg.attachments[0]
                spoiler = file.is_spoiler()
                if not spoiler and file.url.lower().endswith(
                    ("png", "jpeg", "jpg", "gif", "webp")
                ):
                    em.set_image(url=file.url)
                elif spoiler:
                    em.add_field(
                        name="Attachment",
                        value=f"||[{file.filename}]({file.url})||",
                        inline=False,
                    )
                else:
                    em.add_field(
                        name="Attachment",
                        value=f"[{file.filename}]({file.url})",
                        inline=False,
                    )
            if emoji == "unfire":
                newfb = await fireboard.send(
                    content=f"<:unfire:1128853116129923093> **{total_reacts}**",
                    embed=em,
                )
            else:
                newfb = await fireboard.send(
                    content=f"{fire} **{total_reacts}**", embed=em
                )
            # newfb = await fireboard.send(f"{added_msg.author.name}'s message '{added_msg.content}' has {total_reacts} {fire}.")
            await add_msg(total_reacts, added_msg, newfb.id, fireboard.id, emoji)
        else:
            existingMessage = await fireboard.fetch_message(exists)
            emoji = await get_element("emoji", "message_id", added_msg.id)
            if emoji == "unfire":
                await existingMessage.edit(
                    content=f"<:unfire:1128853116129923093> **{total_reacts}**"
                )
            else:
                await existingMessage.edit(content=f"{fire} **{total_reacts}**")
            await edit_msg(total_reacts, added_msg)

    # events
    @commands.Cog.listener()
    async def on_ready(self):
        print("Fire ready")
        db = await aiosqlite.connect(bank, timeout=10)
        cursor = await db.cursor()
        await cursor.execute(
            "CREATE TABLE IF NOT EXISTS fire("
            "num INTEGER NOT NULL PRIMARY KEY,"
            ""
            "reacts INTEGER NOT NULL,"
            "channel_id INTEGER NOT NULL,"
            "message_id INTEGER NOT NULL,"
            "guild_id INTEGER NOT NULL,"
            "user_id INTEGER NOT NULL,"
            "fb_id INTEGER NOT NULL,"
            "message TEXT,"
            "attachments TEXT,"
            "timestamp INTEGER NOT NULL"
            ")"
        )
        await cursor.close()
        await db.commit()
        await db.close()

    @commands.command()
    async def howtofire(self, ctx):
        await ctx.send(
            "Create a channel named #fireboard, give me permission to talk there, and then I will automatically post messages with 5 :fire: reactions. Also, once a week I'll list the most fired messages."
        )

    @commands.command(hidden=True)
    @commands.is_owner()
    async def downloadserver(self, ctx):
        fields = [
            "userid",
            "username",
            "content",
            "messageid",
            "attachments",
            "reactions",
        ]
        await ctx.send("ok i am downloading, this will take an extremely long time")
        for channel in ctx.guild.text_channels:
            # done = [800957030461472828, 800958063410151454, 800958363240235028, 887862056664051722, 800969682454446091, 975865331505561701, 851570154432102441]
            done = []
            if channel.id not in done:
                csvfile = f"{channel.id}.csv"
                with open(csvfile, "a+", encoding="utf8", newline="") as csvf:
                    # creating a csv writer object
                    csvwriter = csv.writer(csvf)
                    # writing the fields
                    csvwriter.writerow(fields)
                print(f"ok doing {channel.name}")
                await ctx.send(f"ok doing {channel.name}")
                themessages = list()
                async for message in channel.history(limit=9999999):
                    themessages.append(message)
                # messages = [item for sublist in themessages for item in sublist]
                messages = themessages
                print("i got the messages lol")
                await ctx.send(
                    f"successfully downloaded every message in {channel.name}, i have to loop through {len(messages)} fucking messages."
                )
                rows = []
                for i, message in enumerate(messages):
                    if i % 10000 == 0:
                        print(i)
                    row = [
                        message.author.id,
                        message.author.name,
                        message.content,
                        message.id,
                        message.attachments,
                        message.reactions,
                    ]
                    rows.append(row)
                    # link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
                with open(csvfile, "a+", encoding="utf8", newline="") as csvf:
                    # creating a csv writer object
                    csvwriter = csv.writer(csvf)
                    # writing the data rows
                    csvwriter.writerows(rows)

        await ctx.send("ok done")
        print("ok done")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        fire = "🔥"
        react_channel = self.client.get_channel(payload.channel_id)
        added_msg = await react_channel.fetch_message(payload.message_id)
        react = payload.emoji.name
        total_reacts = 0
        if react_channel.name in [
            "flop-or-fire",
            "fireboard",
            "unfireboard",
        ]:
            return
        if len(added_msg.reactions) == 1:  # wooo i love inconsistencies woooo
            total_reacts = added_msg.reactions[0].count
        else:
            for i, reaction in enumerate(added_msg.reactions):
                if reaction.emoji == fire:
                    total_reacts = added_msg.reactions[i].count
                    break
        if react == fire:
            if total_reacts >= 5:
                fireboard = None
                for channel in added_msg.guild.text_channels:
                    if channel.name == "fireboard":
                        fireboard = channel
                        break
                if fireboard:
                    if fireboard.id == react_channel.id:
                        return
                    await self.add_to_board(added_msg, fireboard, total_reacts, "fire")
        elif react == "unfire":
            if total_reacts >= 5:
                fireboard = None
                for channel in added_msg.guild.text_channels:
                    if channel.name == "unfireboard":
                        fireboard = channel
                        break
                if fireboard:
                    if fireboard.id == react_channel.id:
                        return
                    await self.add_to_board(
                        added_msg, fireboard, total_reacts, "unfire"
                    )

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        fire = "🔥"
        react_channel = self.client.get_channel(payload.channel_id)
        added_msg = await react_channel.fetch_message(payload.message_id)
        react = payload.emoji.name
        total_reacts = 0
        if react_channel.name in [
            "flop-or-fire",
            "fireboard",
            "unfireboard",
        ]:
            return
        if len(added_msg.reactions) == 1:  # wooo i love inconsistencies woooo
            total_reacts = added_msg.reactions[0].count
        else:
            for i, reaction in enumerate(added_msg.reactions):
                if reaction.emoji == fire:
                    total_reacts = added_msg.reactions[i].count
                    break
        if react == fire:
            if total_reacts >= 5:
                fireboard = None
                for channel in added_msg.guild.text_channels:
                    if channel.name == "fireboard":
                        fireboard = channel
                        break
                if fireboard:
                    if fireboard.id == react_channel.id:
                        return
                    await self.add_to_board(added_msg, fireboard, total_reacts, "fire")
            if total_reacts < 5:
                exists = await get_element("fb_id", "message_id", added_msg.id)
                if exists:
                    await delete_element("message_id", added_msg.id)
        elif react == "unfire":
            if total_reacts >= 5:
                fireboard = None
                for channel in added_msg.guild.text_channels:
                    if channel.name == "unfireboard":
                        fireboard = channel
                        break
                if fireboard:
                    if fireboard.id == react_channel.id:
                        return
                    await self.add_to_board(
                        added_msg, fireboard, total_reacts, "unfire"
                    )
            if total_reacts < 5:
                exists = await get_element("fb_id", "message_id", added_msg.id)
                if exists:
                    await delete_element("message_id", added_msg.id)

    @commands.command()
    async def unix(self, ctx):
        await ctx.send("The current unix time is `" + (str(int(t.time()))) + "`")

    @tasks.loop(seconds=30)
    async def weekly(self):
        async def getfuckingdata():
            db = await aiosqlite.connect(bank, timeout=10)
            cursor = await db.cursor()
            await cursor.execute("SELECT data FROM misc WHERE pointer='weeklyFire'")
            result = await cursor.fetchone()
            await cursor.close()
            if result is not None:
                old = int(result[0])
            else:
                old = None
            await cursor.close()
            await db.close()
            return old

        async def setfuckingdata(old):
            db = await aiosqlite.connect(bank, timeout=10)
            cursor = await db.cursor()
            await cursor.execute(
                f"UPDATE misc SET data = {old + 604800} WHERE pointer='weeklyFire'"
            )
            await db.commit()
            await cursor.close()
            await db.close()

        async def getmessages(unix):
            db = await aiosqlite.connect(bank, timeout=10)
            cursor = await db.cursor()
            await cursor.execute(
                f"SELECT * FROM fire WHERE timestamp > {unix - 604800} AND emoji = 'fire' ORDER BY reacts DESC"
            )
            result = await cursor.fetchall()
            await cursor.close()
            return result

        old = await getfuckingdata()
        unix = int(t.time())
        if not old:
            print(
                "Old returned none in getfuckingdata() in fire.py!!! This should never happen!!!"
            )
            return
        if unix > old:
            for server in self.client.guilds:
                fireboard = None
                for channel in server.text_channels:
                    if channel.name == "fireboard":
                        fireboard = channel
                        print("found fireboard")
                if fireboard:
                    result = await getmessages(unix)
                    msgtosend = "Congrats to the following people for getting the top 5 hottest messages this week:\n"
                    # num, reacts, channel_id, message_id, guild_id, user_id, fb_id, message, attachments, timestamp
                    h = 0
                    for i, msg in enumerate(result):
                        if msg[6] == fireboard.id:
                            h += 1
                            if h == 6:
                                break
                            try:
                                user = self.client.get_user(msg[5])
                                msgtosend += f"{fire} **{msg[1]}** - {user.mention} - https://discord.com/channels/{msg[4]}/{msg[2]}/{msg[3]}\n"
                            except:  # noqa: E722
                                print("couldn't get user!!!")
                                user = msg[5]
                                msgtosend += f"{fire} **{msg[1]}** - {user} - https://discord.com/channels/{msg[4]}/{msg[2]}/{msg[3]}\n"
                    if (
                        msgtosend
                        == "Congrats to the following people for getting the top 5 hottest messages this week:\n"
                    ):
                        pass
                    else:
                        await fireboard.send(msgtosend)

            await setfuckingdata(old)

    @commands.command()
    async def highestfire(self, ctx, channel: discord.TextChannel = None):
        if not channel:
            db = await aiosqlite.connect(bank, timeout=10)
            cursor = await db.cursor()
            await cursor.execute(
                f"SELECT * FROM fire WHERE guild_id = {ctx.guild.id} AND emoji = 'fire' ORDER BY reacts DESC LIMIT 1"
            )
            result = await cursor.fetchone()
            await cursor.close()
            await db.close()
            if not result:
                await ctx.send(
                    "something went wrong, either there are no fire reacts in this server, or my creator is a dumbass. the latter is more likely."
                )
                return
            await ctx.send(
                f"https://discord.com/channels/{result[4]}/{result[2]}/{result[3]}"
            )
        else:
            db = await aiosqlite.connect(bank, timeout=10)
            cursor = await db.cursor()
            await cursor.execute(
                f"SELECT * FROM fire WHERE channel_id = {channel.id} AND emoji = 'fire' ORDER BY reacts DESC LIMIT 1"
            )
            result = await cursor.fetchone()
            await cursor.close()
            await db.close()
            if not result:
                await ctx.send(
                    "something went wrong, either there are no fire reacts in this channel, or my creator is a dumbass. the latter is more likely."
                )
                return
            await ctx.send(
                f"https://discord.com/channels/{result[4]}/{result[2]}/{result[3]}"
            )

    @commands.command()
    async def highestunfire(self, ctx, channel: discord.TextChannel = None):
        if not channel:
            db = await aiosqlite.connect(bank, timeout=10)
            cursor = await db.cursor()
            await cursor.execute(
                f"SELECT * FROM fire WHERE guild_id = {ctx.guild.id} AND emoji = 'unfire' ORDER BY reacts DESC LIMIT 1"
            )
            result = await cursor.fetchone()
            await cursor.close()
            await db.close()
            if not result:
                await ctx.send(
                    "something went wrong, either there are no fire reacts in this server, or my creator is a dumbass. the latter is more likely."
                )
                return
            await ctx.send(
                f"https://discord.com/channels/{result[4]}/{result[2]}/{result[3]}"
            )
        else:
            db = await aiosqlite.connect(bank, timeout=10)
            cursor = await db.cursor()
            await cursor.execute(
                f"SELECT * FROM fire WHERE channel_id = {channel.id} AND emoji = 'unfire' ORDER BY reacts DESC LIMIT 1"
            )
            result = await cursor.fetchone()
            await cursor.close()
            await db.close()
            if not result:
                await ctx.send(
                    "something went wrong, either there are no fire reacts in this channel, or my creator is a dumbass. the latter is more likely."
                )
                return
            await ctx.send(
                f"https://discord.com/channels/{result[4]}/{result[2]}/{result[3]}"
            )

    @commands.command()
    async def fireleaderboard(self, ctx, fire: str = None):
        # get users, count fire for each, display on leaderboard
        if not fire:
            fire = "fire"
        data = {}
        messageids = []
        db = await aiosqlite.connect(bank, timeout=10)
        cursor = await db.cursor()
        await cursor.execute(
            "SELECT * FROM fire"
        )  # num, reacts, channel_id, message_id, guild_id, user_id, fb_id, message, attachments, timestamp, x, emoji
        results = await cursor.fetchall()
        for result in results:
            if result[3] not in messageids and result[11] == fire:
                messageids.append(result[3])
                try:
                    data[f"{result[5]}"] += result[1]
                except KeyError:
                    data[f"{result[5]}"] = result[1]
        # sort dictionary by value
        sorted_data = {
            k: v
            for k, v in sorted(data.items(), key=lambda item: item[1], reverse=True)
        }
        em = discord.Embed(title="Top 10 Fire Havers", color=discord.Color(0xFA43EE))
        index = 0
        for key, value in sorted_data.items():
            if index == 10:
                break
            index += 1
            bal = value
            user_id = key
            try:
                username = await self.client.fetch_user(user_id)
                em.add_field(name=f"{index}. {username}", value=f"{bal}", inline=False)
            except:  # noqa: E722
                index -= 1
        await ctx.send(embed=em)
        await cursor.close()
        await db.close()


async def setup(client):
    await client.add_cog(Fire(client))
