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
    return "Leave Bot Running"

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
WARN_CHANNEL = 1480389401535189065

LEAVE_ROLE = 1492607429249339502
WARN_ROLE1 = 1493332501811171470
WARN_ROLE2 = 1497389416719847474

# =========================
# FILES
# =========================

LEAVE_FILE = "leaves.json"
WARN_FILE = "warns.json"

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
# LEAVE MODAL
# =========================

class LeaveModal(Modal, title="طلب إجازة"):

    reason = TextInput(
        label="سبب الإجازة",
        required=True
    )

    days = TextInput(
        label="مدة الإجازة بالأيام (اقل شي 3)",
        required=True
    )

    async def on_submit(self, interaction):

        warns = load_json(WARN_FILE)

        if str(interaction.user.id) in warns:

            await interaction.response.send_message(
                "❌ لا يمكنك طلب إجازة لوجود إنذار عليك",
                ephemeral=True
            )
            return

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

            "start": start.timestamp(),
            "end": end.timestamp(),
            "withdraw": 0

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

            embed.add_field(
                name="السبب",
                value=self.reason.value
            )

            embed.timestamp = datetime.datetime.utcnow()

            await log.send(embed=embed)

        await interaction.response.send_message(
            "✅ تم تسجيل الإجازة",
            ephemeral=True
        )

# =========================
# WITHDRAW MODAL
# =========================

class WithdrawModal(Modal, title="سحب إجازة"):

    reason = TextInput(
        label="سبب السحب",
        required=True
    )

    async def on_submit(self, interaction):

        leaves = load_json(LEAVE_FILE)

        uid = str(interaction.user.id)

        if uid not in leaves:

            await interaction.response.send_message(
                "❌ ليس لديك إجازة",
                ephemeral=True
            )
            return

        data = leaves[uid]

        start_time = datetime.datetime.fromtimestamp(
            data["start"]
        )

        now = datetime.datetime.utcnow()

        if (now - start_time).total_seconds() > 86400:

            await interaction.response.send_message(
                "❌ ممنوع السحب بعد 24 ساعة",
                ephemeral=True
            )
            return

        data["withdraw"] += 1

        if data["withdraw"] >= 2:

            warns = load_json(WARN_FILE)

            warns[uid] = {

                "end": (
                    now + datetime.timedelta(days=3)
                ).timestamp()

            }

            save_json(WARN_FILE, warns)

            role_warn = interaction.guild.get_role(
                WARN_ROLE1
            )

            if role_warn:
                await interaction.user.add_roles(
                    role_warn
                )

        del leaves[uid]

        save_json(LEAVE_FILE, leaves)

        role = interaction.guild.get_role(
            LEAVE_ROLE
        )

        if role:
            await interaction.user.remove_roles(role)

        log = bot.get_channel(
            LEAVE_LOG
        )

        if log:
            await log.send(
                f"❌ تم سحب إجازة {interaction.user.mention}\n"
                f"📝 السبب: {self.reason.value}"
            )

        await interaction.response.send_message(
            "✅ تم سحب الإجازة",
            ephemeral=True
        )

# =========================
# BUTTON VIEW
# =========================

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

    @discord.ui.button(
        label="سحب إجازة",
        style=discord.ButtonStyle.red
    )
    async def withdraw_leave(
        self, interaction, button
    ):

        await interaction.response.send_modal(
            WithdrawModal()
        )

# =========================
# PANEL
# =========================

@bot.command()
async def leavepanel(ctx):

    if ctx.channel.id != LEAVE_CHANNEL:
        return

    await ctx.message.delete()

    embed = discord.Embed(
        title="📅 نظام الإجازات",
        description=(
            "📌 **تنبيه مهم**\n"
            "سحب الإجازة بعد 24 ساعة ممنوع\n"
            "السحب المتكرر يعرضك للإنذار"
        ),
        color=discord.Color.blue()
    )

    await ctx.send(
        embed=embed,
        view=LeaveView()
    )

# =========================
# WARN COMMAND
# =========================

@bot.command()
async def warn(ctx, member: discord.Member):

    if ctx.channel.id != WARN_CHANNEL:
        return

    await ctx.message.delete()

    warns = load_json(WARN_FILE)

    now = datetime.datetime.utcnow()

    if str(member.id) in warns:

        role = ctx.guild.get_role(
            WARN_ROLE2
        )

        text = "انذار ثاني"

    else:

        role = ctx.guild.get_role(
            WARN_ROLE1
        )

        text = "انذار اول"

    if role:
        await member.add_roles(role)

    warns[str(member.id)] = {

        "end": (
            now + datetime.timedelta(days=3)
        ).timestamp()

    }

    save_json(WARN_FILE, warns)

    msg = await ctx.send(
        f"⚠️ {text} {member.mention}"
    )

    await asyncio.sleep(5)

    await msg.delete()

# =========================
# CHECK LOOP
# =========================

@tasks.loop(minutes=1)
async def check_system():

    await bot.wait_until_ready()

    leaves = load_json(LEAVE_FILE)
    warns = load_json(WARN_FILE)

    now = datetime.datetime.utcnow()

    if not bot.guilds:
        return

    guild = bot.guilds[0]

    # انتهاء الاجازات

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

    # انتهاء الانذارات

    for uid in list(warns.keys()):

        end = datetime.datetime.fromtimestamp(
            warns[uid]["end"]
        )

        if now >= end:

            member = guild.get_member(int(uid))

            if member:

                r1 = guild.get_role(WARN_ROLE1)
                r2 = guild.get_role(WARN_ROLE2)

                if r1:
                    await member.remove_roles(r1)

                if r2:
                    await member.remove_roles(r2)

                ch = bot.get_channel(
                    WARN_CHANNEL
                )

                if ch:
                    await ch.send(
                        f"تم سحب الانذار {member.mention}"
                    )

            del warns[uid]

    save_json(WARN_FILE, warns)

# =========================
# READY
# =========================

@bot.event
async def on_ready():

    print(f"✅ Logged in as {bot.user}")

    if not check_system.is_running():
        check_system.start()

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
