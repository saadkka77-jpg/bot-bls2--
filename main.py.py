import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
import os

# كود عشان البوت ما يطفي في Render
app = Flask('')

@app.route('/')
def home():
    return "Bot is Online!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# إعدادات البوت
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command()
async def ping(ctx):
    await ctx.send("Pong! 🏓")

# تشغيل نظام الـ keep_alive
keep_alive()

# جلب التوكن من Environment Variables في Render
token = os.getenv("DISCORD_TOKEN")

if token:
    bot.run(token)
else:
    print("خطأ: لم يتم العثور على DISCORD_TOKEN في إعدادات Render!")
