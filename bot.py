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
POST_HOUR = int(os.getenv("POST_HOUR", "10"))
POST_MINUTE = int(os.getenv("POST_MINUTE", "0"))
TIMEZONE = os.getenv("TIMEZONE", "America/New_York")

VERSE_REFS = [
    "John 3:16", "Psalm 23:1-3", "Proverbs 3:5-6", "Romans 8:28",
    "Philippians 4:13", "Isaiah 40:31", "Jeremiah 29:11", "Matthew 6:33",
    "Joshua 1:9", "Psalm 46:1", "Romans 8:38-39", "1 Corinthians 13:4-7",
    "Psalm 91:1-2", "Hebrews 11:1", "James 1:2-4", "Galatians 5:22-23",
    "Ephesians 2:8-9", "Romans 12:2", "Psalm 119:105", "Matthew 5:3-5",
    "John 14:6", "1 John 4:19", "Psalm 37:4", "Isaiah 41:10",
    "Philippians 4:6-7", "Romans 5:8", "Lamentations 3:22-23", "Psalm 27:1",
    "Isaiah 26:3", "Colossians 3:23", "1 Peter 5:7", "Psalm 1:1-3",
    "Romans 15:13", "John 16:33", "Micah 6:8", "Psalm 139:14",
    "Matthew 11:28-30", "Deuteronomy 31:6", "Psalm 34:18", "2 Timothy 1:7",
    "Ephesians 3:20", "Psalm 46:10", "Romans 8:1", "John 15:5",
    "Proverbs 16:3", "Isaiah 43:2", "Psalm 73:26", "Matthew 6:34",
    "2 Corinthians 12:9", "Psalm 121:1-2", "Romans 12:19", "John 14:27",
    "Psalm 37:7", "Nahum 1:7", "Isaiah 55:8-9", "Psalm 40:1-3",
    "Hebrews 4:16", "Romans 5:1", "Psalm 62:1-2", "1 Peter 2:9",
    "Matthew 5:14-16", "Proverbs 4:23", "Psalm 51:10", "Romans 12:21",
    "John 8:32", "Ephesians 4:32", "Psalm 19:1", "Isaiah 40:29",
    "1 Corinthians 10:13", "Psalm 55:22", "Romans 8:37", "Matthew 22:37-39",
    "Psalm 145:18", "Proverbs 17:17", "Isaiah 58:6", "John 3:17",
    "2 Chronicles 7:14", "Psalm 30:5", "Romans 10:9", "Hebrews 13:5",
    "Psalm 16:11", "Colossians 3:2", "Isaiah 40:8", "Matthew 5:9",
    "1 John 1:9", "Psalm 103:12", "Romans 6:23", "John 10:10",
    "Ephesians 6:10-11", "Psalm 147:3", "Isaiah 41:13", "Proverbs 18:10",
    "Matthew 6:9-13", "1 Thessalonians 5:16-18", "Psalm 23:4", "Romans 8:28",
    "John 1:1", "Revelation 21:4", "Psalm 107:1", "Philippians 1:6",
    "Isaiah 54:10", "Matthew 5:6", "Hebrews 10:23", "Romans 12:12",
]

VERSE_NOTES = {
    "John 3:16": "God's greatest gift - His love for every person.",
    "Psalm 23:1-3": "The Lord as our shepherd, providing all we need.",
    "Proverbs 3:5-6": "Trust in God's wisdom above our own understanding.",
    "Romans 8:28": "All things - even hardships - work for God's purpose.",
    "Philippians 4:13": "Strength through Christ in every circumstance.",
    "Isaiah 40:31": "Renewed strength for those who wait on the Lord.",
    "Jeremiah 29:11": "God's plans for you are full of hope and a future.",
    "Matthew 6:33": "Seek God first, and everything else follows.",
}

def get_verse_note(reference):
    for key, note in VERSE_NOTES.items():
        if key.lower() in reference.lower():
            return note
    return "Meditate on this scripture and let it speak to your heart today."

async def fetch_verse(reference):
    try:
        encoded = reference.replace(" ", "%20").replace(":", "%3A")
        url = f"https://bible-api.com/{encoded}?translation=kjv"
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
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
scheduler = AsyncIOScheduler()

async def post_devotional():
    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        print(f"Could not find channel with ID {CHANNEL_ID}")
        return
    day_of_year = datetime.datetime.now().timetuple().tm_yday
    reference = VERSE_REFS[day_of_year % len(VERSE_REFS)]
    verse_text, canonical_ref = await fetch_verse(reference)
    if not verse_text:
        verse_text = "*Verse text could not be loaded - please open your Bible to read today's passage.*"
    note = get_verse_note(canonical_ref)
    tz = pytz.timezone(TIMEZONE)
    today = datetime.datetime.now(tz).strftime("%A, %B %d, %Y")
    embed = discord.Embed(title=f"Daily Devotional - {today}", color=discord.Color.gold())
    embed.add_field(name=f"{canonical_ref}", value=verse_text, inline=False)
    embed.add_field(name="Reflection", value=note, inline=False)
    embed.set_footer(text="May God's Word guide your day.")
    await channel.send(embed=embed)
    print(f"Posted devotional: {canonical_ref}")

@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")
    tz = pytz.timezone(TIMEZONE)
    scheduler.add_job(post_devotional, CronTrigger(hour=POST_HOUR, minute=POST_MINUTE, timezone=tz))
    scheduler.start()
    print(f"Scheduler started - posting daily at {POST_HOUR}:{POST_MINUTE:02d} {TIMEZONE}")

@bot.command(name="devotional")
async def manual_devotional(ctx):
    await post_devotional()

@bot.command(name="verse")
async def verse_command(ctx, *, reference: str):
    verse_text, canonical_ref = await fetch_verse(reference)
    if verse_text:
        embed = discord.Embed(title=f"{canonical_ref}", description=verse_text, color=discord.Color.blue())
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"Could not find verse: {reference}")

bot.run(TOKEN)
