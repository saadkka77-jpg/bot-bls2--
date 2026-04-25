import discord
from discord.ext import commands, tasks
from discord.ui import View, Modal, TextInput
import datetime
import json
import os
import asyncio

from flask import Flask
from threading import Thread

# =========================
# KEEP ALIVE
# =========================

app = Flask('')

@app.route('/')
def home():
    return "Bot Running"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run_web).start()

# =========================
# BOT
# =========================

intents = discord.Intents.all()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# =========================
# IDS
# =========================

LEAVE_CHANNEL = 1490070238270718013
LEAVE_LOG = 1490820000477610036

POINT_CHANNEL = 1497204458680090779
RESET_CHANNEL = 1497642199859593388

LEAVE_ROLE = 1492607429249339502

ALLOWED_ROLES = [
1478970736717598840,
1495873706923393205,
1490386915629989948,
1478971845729583276
]

POINT_ROLES = [
1482194383515422752,
1480443913557905499
]

# =========================
# FILES
# =========================

LEAVE_FILE = "leaves.json"
POINT_FILE = "points.json"
DOUBLE_FILE = "double.json"

def load_json(file):

    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f)

    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):

    with open(file, "w") as f:
        json.dump(data, f, indent=4)

# =========================
# نقاط الكتابة
# =========================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if any(r.id in POINT_ROLES for r in message.author.roles):

        points = load_json(POINT_FILE)
        double = load_json(DOUBLE_FILE)

        uid = str(message.author.id)

        add = 2

        if double.get("active"):
            add = 5

        points[uid] = points.get(uid, 0) + add

        save_json(POINT_FILE, points)

    await bot.process_commands(message)

# =========================
# نقاط الصوت
# =========================

voice_times = {}

@bot.event
async def on_voice_state_update(member, before, after):

    if not any(r.id in POINT_ROLES for r in member.roles):
        return

    uid = str(member.id)

    if after.channel:

        voice_times[uid] = datetime.datetime.utcnow()

    elif before.channel:

        if uid in voice_times:

            start = voice_times[uid]

            mins = (
                datetime.datetime.utcnow() - start
            ).total_seconds() / 60

            count = int(mins // 5)

            if count > 0:

                points = load_json(POINT_FILE)
                double = load_json(DOUBLE_FILE)

                add = 15

                if double.get("active"):
                    add = 30

                total = add * count

                points[uid] = points.get(uid, 0) + total

                save_json(POINT_FILE, points)

            del voice_times[uid]

# =========================
# عرض النقاط
# =========================

@bot.command(name="تفاعل")
async def show_points(ctx):

    if ctx.channel.id != POINT_CHANNEL:
        return

    await ctx.message.delete()

    points = load_json(POINT_FILE)

    uid = str(ctx.author.id)

    total = points.get(uid, 0)

    embed = discord.Embed(
        title="📊 نقاط التفاعل",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="المستخدم",
        value=ctx.author.mention
    )

    embed.add_field(
        name="مجموع النقاط",
        value=f"{total} نقطة"
    )

    embed.timestamp = datetime.datetime.utcnow()

    msg = await ctx.send(embed=embed)

    await asyncio.sleep(10)

    await msg.delete()

# =========================
# تصفير نقاط
# =========================

@bot.command(name="تصفير")
async def reset_points(ctx, member: discord.Member):

    if ctx.channel.id != RESET_CHANNEL:
        return

    await ctx.message.delete()

    if not any(r.id in ALLOWED_ROLES for r in ctx.author.roles):

        msg = await ctx.send(
            "❌ لا يسمح لك باستخدام الامر"
        )

        await asyncio.sleep(5)
        await msg.delete()

        return

    points = load_json(POINT_FILE)

    points[str(member.id)] = 0

    save_json(POINT_FILE, points)

    msg = await ctx.send(
        f"✅ تم تصفير نقاط {member.mention}"
    )

    await asyncio.sleep(5)
    await msg.delete()

# =========================
# إضافة نقاط
# =========================

@bot.command(name="اضف")
async def add_points(ctx, member: discord.Member, amount: int):

    if ctx.channel.id != RESET_CHANNEL:
        return

    await ctx.message.delete()

    if not any(r.id in ALLOWED_ROLES for r in ctx.author.roles):

        msg = await ctx.send(
            "❌ لا يسمح لك باستخدام الامر"
        )

        await asyncio.sleep(5)
        await msg.delete()

        return

    points = load_json(POINT_FILE)

    uid = str(member.id)

    points[uid] = points.get(uid, 0) + amount

    save_json(POINT_FILE, points)

    msg = await ctx.send(
        f"➕ تم إضافة {amount} نقطة إلى {member.mention}"
    )

    await asyncio.sleep(5)
    await msg.delete()

# =========================
# دبل تفاعل
# =========================

@bot.command()
async def double(ctx):

    await ctx.message.delete()

    double = {"active": True}

    save_json(DOUBLE_FILE, double)

    msg = await ctx.send(
        "🔥 تم تفعيل الدبل"
    )

    await asyncio.sleep(5)
    await msg.delete()

@bot.command()
async def doubleoff(ctx):

    await ctx.message.delete()

    double = {"active": False}

    save_json(DOUBLE_FILE, double)

    msg = await ctx.send(
        "❄️ تم إيقاف الدبل"
    )

    await asyncio.sleep(5)
    await msg.delete()

# =========================
# لوحة الإجازات
# =========================

class LeaveModal(Modal, title="طلب إجازة"):

    reason = TextInput(label="سبب الإجازة")

    days = TextInput(label="عدد الأيام")

    async def on_submit(self, interaction):

        try:
            days = int(self.days.value)
        except:

            await interaction.response.send_message(
                "❌ اكتب رقم صحيح",
                ephemeral=True
            )
            return

        if days < 3:

            await interaction.response.send_message(
                "❌ أقل مدة 3 أيام",
                ephemeral=True
            )
            return

        leaves = load_json(LEAVE_FILE)

        start = datetime.datetime.utcnow()
        end = start + datetime.timedelta(days=days)

        leaves[str(interaction.user.id)] = {

            "end": end.timestamp()

        }

        save_json(LEAVE_FILE, leaves)

        role = interaction.guild.get_role(
            LEAVE_ROLE
        )

        if role:
            await interaction.user.add_roles(role)

        log = bot.get_channel(
            LEAVE_LOG
        )

        if log:

            embed = discord.Embed(
                title="📩 طلب إجازة",
                color=discord.Color.green()
            )

            embed.add_field(
                name="المستخدم",
                value=interaction.user.mention
            )

            embed.add_field(
                name="المدة",
                value=f"{days} يوم"
            )

            embed.timestamp = datetime.datetime.utcnow()

            await log.send(embed=embed)

        await interaction.response.send_message(
            "✅ تم تسجيل الإجازة",
            ephemeral=True
        )

class LeaveView(View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="طلب إجازة",
        style=discord.ButtonStyle.green
    )
    async def request_leave(
        self, interaction, button
    ):

        await interaction.response.send_modal(
            LeaveModal()
        )

@bot.command()
async def leavepanel(ctx):

    if ctx.channel.id != LEAVE_CHANNEL:
        return

    await ctx.message.delete()

    embed = discord.Embed(
        title="📅 نظام الإجازات",
        description="سحب الإجازة بعد 24 ساعة ممنوع",
        color=discord.Color.blue()
    )

    await ctx.send(
        embed=embed,
        view=LeaveView()
    )

# =========================
# انتهاء الاجازات
# =========================

@tasks.loop(minutes=1)
async def check_leave():

    leaves = load_json(LEAVE_FILE)

    now = datetime.datetime.utcnow()

    if not bot.guilds:
        return

    guild = bot.guilds[0]

    for uid in list(leaves.keys()):

        end = datetime.datetime.fromtimestamp(
            leaves[uid]["end"]
        )

        if now >= end:

            member = guild.get_member(int(uid))

            if member:

                role = guild.get_role(
                    LEAVE_ROLE
                )

                if role:
                    await member.remove_roles(role)

                try:
                    await member.send(
                        "انتهت الاجازه الخاصه بك"
                    )
                except:
                    pass

            del leaves[uid]

    save_json(LEAVE_FILE, leaves)

# =========================
# READY
# =========================

@bot.event
async def on_ready():

    print(f"✅ Logged in as {bot.user}")

    check_leave.start()

    bot.add_view(LeaveView())

# =========================
# START
# =========================

keep_alive()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if DISCORD_TOKEN:
    bot.run(DISCORD_TOKEN)
else:
    print("❌ لم يتم العثور على DISCORD_TOKEN")
