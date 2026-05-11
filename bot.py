import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import aiohttp
import os
import datetime
import pytz
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
POST_HOUR = int(os.getenv("POST_HOUR", "8"))
POST_MINUTE = int(os.getenv("POST_MINUTE", "0"))
TIMEZONE = os.getenv("TIMEZONE", "America/New_York")

# 365 rotating verse references (KJV via bible-api.com)
VERSE_REFS = [
    "John 3:16", "Psalm 23:1-3", "Proverbs 3:5-6", "Romans 8:28",
    "Philippians 4:13", "Isaiah 40:31", "Jeremiah 29:11", "Matthew 6:33",
    "Joshua 1:9", "Psalm 46:1", "Romans 8:38-39", "1 Corinthians 13:4-7",
    "Psalm 91:1-2", "Hebrews 11:1", "James 1:2-4", "Galatians 5:22-23",
    "Ephesians 2:8-9", "Romans 12:2", "Psalm 119:105", "Matthew 5:3-5",
    "John 14:6", "1 John 4:19", "Psalm 37:4", "Isaiah 41:10",
    "Philippians 4:6-7", "Romans 5:8", "Lamentations 3:22-23", "Psalm 27:1",
    "Matthew 11:28-30", "John 10:10", "2 Timothy 1:7", "Psalm 34:18",
    "Isaiah 26:3", "Colossians 3:23", "1 Peter 5:7", "Psalm 1:1-3",
    "Romans 15:13", "John 16:33", "Micah 6:8", "Psalm 139:14",
    "2 Corinthians 12:9", "Deuteronomy 31:6", "Psalm 121:1-2", "Mark 11:24",
    "Luke 1:37", "Ephesians 3:20", "Psalm 145:18", "Matthew 28:19-20",
    "Hebrews 4:16", "Revelation 3:20", "John 8:36", "Romans 6:23",
    "Psalm 51:10", "Isaiah 55:8-9", "1 Thessalonians 5:16-18", "Proverbs 31:25",
    "John 15:13", "Romans 12:12", "Psalm 63:1", "Galatians 6:9",
    "Matthew 5:14-16", "Colossians 1:16-17", "Psalm 16:8", "Acts 2:38",
    "Isaiah 43:2", "John 14:27", "Psalm 100:1-3", "2 Chronicles 7:14",
    "Romans 8:1", "Ephesians 6:10-11", "Psalm 32:8", "Proverbs 16:3",
    "1 John 1:9", "Isaiah 40:28-29", "Matthew 6:9-13", "John 11:25-26",
    "Psalm 46:10", "Romans 1:16", "Hebrews 12:1-2", "Psalm 150:6",
    "Ephesians 4:32", "James 4:7", "Psalm 23:4", "John 1:1-3",
    "Matthew 22:37-39", "Romans 10:9", "Isaiah 53:5", "Psalm 19:14",
    "1 Corinthians 10:13", "Philippians 1:6", "Psalm 42:1-2", "Titus 3:5",
    "John 3:30", "Romans 8:5-6", "Proverbs 18:10", "Psalm 71:5",
    "Matthew 6:25-26", "2 Peter 3:9", "Psalm 40:1-3", "Zephaniah 3:17",
]

# Short devotional context notes per verse
VERSE_NOTES = {
    "John 3:16": "The most well-known verse in all of Scripture — a reminder that God's love for us is boundless and unconditional.",
    "Psalm 23:1-3": "The Lord is your shepherd. You lack nothing. Rest in His provision today.",
    "Proverbs 3:5-6": "Let go of your own understanding and trust that God is guiding your path.",
    "Romans 8:28": "Even in difficulty, God is working all things together for your good.",
    "Philippians 4:13": "Your strength doesn't come from within — it comes from Christ who dwells in you.",
    "Isaiah 40:31": "When you feel weary, wait on the Lord. He renews strength like an eagle.",
    "Jeremiah 29:11": "God's plans for you are full of hope — not harm. He sees your future.",
    "Matthew 6:33": "Seek first the Kingdom and trust that everything you need will be provided.",
    "Joshua 1:9": "Be strong and courageous. The Lord your God is with you wherever you go.",
    "Psalm 46:1": "God is not just near — He is your very present help in times of trouble.",
}

def get_verse_note(reference):
    for key, note in VERSE_NOTES.items():
        if key.lower() in reference.lower() or reference.lower() in key.lower():
            return note
    return "Take a moment to meditate on this verse and let God's Word speak to your heart today."


async def fetch_verse(reference):
    """Fetch verse text from bible-api.com (free, no auth needed)."""
    try:
        url = f"https://bible-api.com/{reference.replace(' ', '%20')}?translation=kjv"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    text = data.get("text", "").strip()
                    canonical_ref = data.get("reference", reference)
                    return text, canonical_ref
    except Exception as e:
        print(f"Error fetching verse: {e}")
    return None, reference


intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
scheduler = AsyncIOScheduler()


async def post_devotional():
    """Build and send the daily devotional embed."""
    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        print(f"Could not find channel with ID {CHANNEL_ID}")
        return

    # Pick today's verse deterministically by day of year
    day_of_year = datetime.datetime.now().timetuple().tm_yday
    reference = VERSE_REFS[day_of_year % len(VERSE_REFS)]

    verse_text, canonical_ref = await fetch_verse(reference)

    # Fallback if API is down
    if not verse_text:
        verse_text = "*Verse text could not be loaded — please open your Bible to read today's passage.*"

    note = get_verse_note(canonical_ref)

    # Build the embed
    embed = discord.Embed(
        title="Daily Devotional",
        color=0xD4AF37,
        timestamp=datetime.datetime.now(pytz.utc),
    )
    embed.add_field(name=canonical_ref, value=f'"{verse_text}"', inline=False)
    embed.add_field(name="Reflection", value=note, inline=False)
    embed.set_footer(text="May God's Word guide your steps today  |  Bible Bot")

    await channel.send(embed=embed)
    print(f"[{datetime.datetime.now()}] Posted devotional: {canonical_ref}")


@bot.command(name="devotional")
async def manual_devotional(ctx):
    """!devotional -- manually trigger today's devotional."""
    await ctx.message.delete()
    await post_devotional()


@bot.command(name="verse")
async def verse_command(ctx, *, reference: str):
    """!verse <reference> -- look up any Bible verse on demand."""
    verse_text, canonical_ref = await fetch_verse(reference)
    if not verse_text:
        await ctx.send("Could not find that verse. Try a format like John 3:16 or Psalm 23:1-3.")
        return
    embed = discord.Embed(title=canonical_ref, color=0xD4AF37)
    embed.description = f'"{verse_text}"'
    embed.set_footer(text="King James Version  |  Bible Bot")
    await ctx.send(embed=embed)


@bot.event
async def on_ready():
    tz = pytz.timezone(TIMEZONE)
    print(f"Logged in as {bot.user}")
    print(f"Daily devotional scheduled for {POST_HOUR:02d}:{POST_MINUTE:02d} {TIMEZONE}")

    scheduler.add_job(
        post_devotional,
        CronTrigger(hour=POST_HOUR, minute=POST_MINUTE, timezone=tz),
        id="daily_devotional",
        replace_existing=True,
    )
    scheduler.start()


bot.run(TOKEN)
