import discord
from discord.ext import commands, tasks
from discord.ui import View, Button, Modal, TextInput
from flask import Flask
from threading import Thread
import datetime
import asyncio
import json
import os

# =========================
# KEEP ALIVE (Render)
# =========================

app = Flask('')

@app.route('/')
def home():
    return "Bot is Online!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# =========================
# IDS
# =========================

LEAVE_COMMAND_CHANNEL = 1490070238270718013
LEAVE_LOG_CHANNEL = 1490820000477610036
WARN_COMMAND_CHANNEL = 1480389401535189065

LEAVE_ROLE = 1492607429249339502
WARN_ROLE_1 = 1493332501811171470
WARN_ROLE_2 = 1497389416719847474

# =========================
# FILES
# =========================

LEAVE_FILE = "leaves.json"
WARN_FILE = "warns.json"

def load_data(file):
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f)
    with open(file, "r") as f:
        return json.load(f)

def save_data(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

# =========================
# BOT
# =========================

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# LEAVE MODAL
# =========================

class LeaveModal(Modal, title="طلب إجازة"):

    reason = TextInput(
        label="سبب الإجازة",
        placeholder="اكتب السبب هنا",
        required=True
    )

    days = TextInput(
        label="مدة الإجازة بالأيام (اقل شي 3)",
        placeholder="مثال: 5",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):

        warns = load_data(WARN_FILE)

        if str(interaction.user.id) in warns:
            await interaction.response.send_message(
                "لا يمكنك طلب اجازه لوجود انذار عليك",
                ephemeral=True
            )
            return

        try:
            days = int(self.days.value)
        except:
            await interaction.response.send_message(
                "اكتب رقم صحيح",
                ephemeral=True
            )
            return

        if days < 3:
            await interaction.response.send_message(
                "اقل مدة 3 ايام",
                ephemeral=True
            )
            return

        leaves = load_data(LEAVE_FILE)

        start = datetime.datetime.utcnow()
        end = start + datetime.timedelta(days=days)

        leaves[str(interaction.user.id)] = {
            "start": start.timestamp(),
            "end": end.timestamp(),
            "days": days
        }

        save_data(LEAVE_FILE, leaves)

        role = interaction.guild.get_role(LEAVE_ROLE)
        await interaction.user.add_roles(role)

        log_channel = bot.get_channel(LEAVE_LOG_CHANNEL)

        await log_channel.send(
            f"📩 طلب اجازه\n"
            f"👤 {interaction.user.mention}\n"
            f"📅 المدة: {days} يوم\n"
            f"📝 السبب: {self.reason.value}\n"
            f"⏰ {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )

        await interaction.response.send_message(
            "تم تسجيل طلب الاجازه",
            ephemeral=True
        )

# =========================
# WITHDRAW MODAL
# =========================

class WithdrawModal(Modal, title="سحب إجازة"):

    reason = TextInput(
        label="سبب سحب الاجازه",
        placeholder="اكتب السبب",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):

        leaves = load_data(LEAVE_FILE)

        if str(interaction.user.id) not in leaves:
            await interaction.response.send_message(
                "ليس لديك اجازه",
                ephemeral=True
            )
            return

        start_time = datetime.datetime.fromtimestamp(
            leaves[str(interaction.user.id)]["start"]
        )

        now = datetime.datetime.utcnow()

        if (now - start_time).total_seconds() > 86400:
            await interaction.response.send_message(
                "ممنوع السحب السبب مرت 24 ساعه",
                ephemeral=True
            )
            return

        del leaves[str(interaction.user.id)]
        save_data(LEAVE_FILE, leaves)

        role = interaction.guild.get_role(LEAVE_ROLE)
        await interaction.user.remove_roles(role)

        log_channel = bot.get_channel(LEAVE_LOG_CHANNEL)

        await log_channel.send(
            f"❌ تم سحب اجازه\n"
            f"👤 {interaction.user.mention}\n"
            f"📝 السبب: {self.reason.value}\n"
            f"⏰ {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )

        await interaction.response.send_message(
            "تم سحب الاجازه",
            ephemeral=True
        )

# =========================
# BUTTON VIEW
# =========================

class LeaveView(View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="طلب اجازه",
        style=discord.ButtonStyle.green
    )
    async def request_leave(self, interaction, button):

        await interaction.response.send_modal(
            LeaveModal()
        )

    @discord.ui.button(
        label="سحب اجازه",
        style=discord.ButtonStyle.red
    )
    async def withdraw_leave(self, interaction, button):

        await interaction.response.send_modal(
            WithdrawModal()
        )

# =========================
# WARN MODAL
# =========================

class WarnModal(Modal):

    def __init__(self, member):

        super().__init__(title="انذار")

        self.member = member

        self.reason = TextInput(
            label="سبب الانذار",
            required=True
        )

        self.days = TextInput(
            label="مدة الانذار بالايام",
            required=True
        )

        self.add_item(self.reason)
        self.add_item(self.days)

    async def on_submit(self, interaction):

        warns = load_data(WARN_FILE)

        try:
            days = int(self.days.value)
        except:
            await interaction.response.send_message(
                "اكتب رقم صحيح",
                ephemeral=True
            )
            return

        end = datetime.datetime.utcnow() + datetime.timedelta(days=days)

        role1 = interaction.guild.get_role(WARN_ROLE_1)
        role2 = interaction.guild.get_role(WARN_ROLE_2)

        if str(self.member.id) in warns:

            await self.member.add_roles(role2)

            warns[str(self.member.id)] = {
                "end": end.timestamp(),
                "level": 2
            }

            msg = "انذار ثاني"

        else:

            await self.member.add_roles(role1)

            warns[str(self.member.id)] = {
                "end": end.timestamp(),
                "level": 1
            }

            msg = "انذار اول"

        save_data(WARN_FILE, warns)

        await interaction.channel.send(
            f"⚠️ {msg}\n"
            f"{self.member.mention}\n"
            f"📝 السبب: {self.reason.value}"
        )

        await interaction.response.send_message(
            "تم تسجيل الانذار",
            ephemeral=True
        )

# =========================
# WARN COMMAND
# =========================

@bot.command()
async def warn(ctx, member: discord.Member):

    if ctx.channel.id != WARN_COMMAND_CHANNEL:
        return

    await ctx.message.delete()

    await ctx.send_modal(
        WarnModal(member)
    )

# =========================
# SEND PANEL
# =========================

@bot.command()
async def leavepanel(ctx):

    if ctx.channel.id != LEAVE_COMMAND_CHANNEL:
        return

    await ctx.message.delete()

    await ctx.send(
        "نظام الاجازات\nاختر من الخيارات",
        view=LeaveView()
    )

# =========================
# CHECK TASK
# =========================

@tasks.loop(minutes=1)
async def check_times():

    leaves = load_data(LEAVE_FILE)
    warns = load_data(WARN_FILE)

    now = datetime.datetime.utcnow()

    guild = bot.guilds[0]

    # انتهاء الاجازات
    for user_id in list(leaves.keys()):

        end_time = datetime.datetime.fromtimestamp(
            leaves[user_id]["end"]
        )

        if now >= end_time:

            member = guild.get_member(int(user_id))

            if member:

                role = guild.get_role(LEAVE_ROLE)

                await member.remove_roles(role)

                try:
                    await member.send(
                        "انتهت الاجازه الخاصه بك"
                    )
                except:
                    pass

            del leaves[user_id]

    save_data(LEAVE_FILE, leaves)

    # انتهاء الانذارات
    for user_id in list(warns.keys()):

        end_time = datetime.datetime.fromtimestamp(
            warns[user_id]["end"]
        )

        if now >= end_time:

            member = guild.get_member(int(user_id))

            if member:

                role1 = guild.get_role(WARN_ROLE_1)
                role2 = guild.get_role(WARN_ROLE_2)

                await member.remove_roles(role1)
                await member.remove_roles(role2)

                channel = bot.get_channel(
                    WARN_COMMAND_CHANNEL
                )

                await channel.send(
                    f"تم سحب الانذار {member.mention}"
                )

            del warns[user_id]

    save_data(WARN_FILE, warns)

# =========================
# READY
# =========================

@bot.event
async def on_ready():

    print(f"Logged in as {bot.user}")

    check_times.start()

    bot.add_view(LeaveView())

# =========================
# START
# =========================

keep_alive()

token = os.getenv("DISCORD_TOKEN")

bot.run(token)
