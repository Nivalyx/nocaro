import discord
import random

# import asyncio
from discord.ext import commands


class Fun(commands.Cog):
    def __init__(self, client):
        self.client = client

    # events
    @commands.Cog.listener()
    async def on_ready(self):
        print("Fun ready.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.content.startswith(","):
            return
        if message.content.lower() in ["share", "steal", "yes", "no"]:
            return
        if isinstance(message.channel, discord.channel.DMChannel):
            blacklisted = [691685357498138635, 677830735754952726]
            if message.author.id in blacklisted:
                await message.channel.send(
                    "You've been blacklisted from all DMs. There is no chance for appeal."
                )
                return
            me = await self.client.fetch_user(248984895940984832)
            await me.send(
                f"DM from {message.author.name} ({message.author.id})\n{message.content}\n`,dm {message.author.id}`"
            )
            if message.attachments:
                for attachment in message.attachments:
                    await me.send(attachment.url)

    # commands

    @commands.command()
    async def ip(self, ctx, user: discord.Member = None):
        ip1 = random.randint(1, 255)
        ip2 = random.randint(0, 255)
        ip3 = random.randint(0, 255)
        ip4 = random.randint(1, 255)
        while ip1 == 192 and ip2 == 168:
            ip1 = random.randint(1, 255)
            ip2 = random.randint(0, 255)
        if user is not None:
            await ctx.send(f"{user.name}'s ip address is {ip1}.{ip2}.{ip3}.{ip4}")
        else:
            await ctx.send(f"{ip1}.{ip2}.{ip3}.{ip4}")

    @commands.command(aliases=["8ball", "ask"], hidden=True)
    async def _8ball(self, ctx, *, question):
        responses = [
            "It is certain.",
            "It is decidedly so.",
            "Without a doubt.",
            "Yes - definitely.",
            "You may rely on it.",
            "As I see it, yes.",
            "Most likely.",
            "Outlook good.",
            "Yes.",
            "Signs point to yes.",
            "Reply hazy, try again.",
            "Ask again later.",
            "Better not tell you now.",
            "Cannot predict now.",
            "Concentrate and ask again.",
            "Don't count on it.",
            "My reply is no.",
            "My sources say no.",
            "Outlook not so good.",
            "Very doubtful.",
        ]
        await ctx.send(
            discord.utils.escape_mentions(
                f"Question: {question}\nAnswer: {random.choice(responses)}"
            )
        )

    @commands.command(hidden=True)
    @commands.is_owner()
    async def dmid(self, ctx, member: int = 0, content=None):
        if not member:
            return
        try:
            member = await self.client.fetch_user(member)
        except discord.NotFound:
            try:
                member = await self.client.get_user(member)
            except discord.NotFound:
                await ctx.send("Fucked up bro")
                return
        await member.send(content)  # type: ignore
        await ctx.add_reaction("✅")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def dm(self, ctx, user: discord.Member, *, message: str):
        """DM the user of your choice"""
        if not f"{user}":
            return await ctx.send(f"Could not find any UserID matching **{user.name}**")

        try:
            await user.send(message)
            await ctx.send(f"✉️ Sent a DM to **{user.name}**")
        except discord.Forbidden:
            await ctx.send(
                "This user might be having DMs blocked or it's a bot account..."
            )

    @commands.command()
    async def createpoll(self, ctx, amount: int = 0):
        """Make a poll"""
        if amount > 10 or amount < 1:
            await ctx.send("Number must be between 1 and 10 inclusive.")
        if ctx.message.reference:
            original = await ctx.fetch_message(ctx.message.reference.message_id)
            emojis = [
                "1️⃣",
                "2️⃣",
                "3️⃣",
                "4️⃣",
                "5️⃣",
                "6️⃣",
                "7️⃣",
                "8️⃣",
                "9️⃣",
                "0️⃣",
            ]
            for i in range(amount):
                await original.add_reaction(emojis[i])
            await ctx.message.delete()
        else:
            await ctx.send("reply to a message and try again")


async def setup(client):
    await client.add_cog(Fun(client))
