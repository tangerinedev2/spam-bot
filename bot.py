import asyncio
import logging
import os
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

# ─────────────────────────── AYARLAR ───────────────────────────
TOKEN = os.getenv("DISCORD_TOKEN")
MAIN_GUILD_ID = 1563800565581090846  # Ana sunucunun ID'si
REQUIRED_STATUS = ".gg/kosk"
SPAM_COUNT = 5
SPAM_DELAY = 0.3
COOLDOWN_SECONDS = 15
EMBED_COLOR = 0x2b2d31
OK_COLOR = 0x57f287
ERR_COLOR = 0xed4245
# ────────────────────────────────────────────────────────────────

if not TOKEN:
    raise ValueError("HATA: .env dosyasında DISCORD_TOKEN bulunamadı!")

logging.basicConfig(level=logging.INFO, format="[rat] %(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("kosk-bot")

intents = discord.Intents.default()
intents.presences = True
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!x!", intents=intents, help_command=None)


# ─────────────────────── YARDIMCI FONKSİYONLAR ───────────────────────

def has_required_status(member: discord.Member) -> bool:
    if not member or not member.activities:
        return False
    for activity in member.activities:
        if isinstance(activity, discord.CustomActivity):
            text = " ".join(filter(None, [activity.name, activity.state])).lower()
            if "kosk" in text or REQUIRED_STATUS in text:
                return True
    return False


def build_embed(title: str, description: str, color: int = EMBED_COLOR) -> discord.Embed:
    return discord.Embed(
        title=title, description=description, color=color, timestamp=datetime.now(timezone.utc)
    )


# ─────────────────────────── OLAYLAR ───────────────────────────

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        log.info("nest warm. %d slash komut senkronize edildi.", len(synced))
    except discord.HTTPException as e:
        log.error("slash sync hatası: %s", e)
    log.info("%s olarak giriş yapıldı.", bot.user)


@bot.event
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            embed=build_embed("cold wire", f"çok hızlı. `{error.retry_after:.1f}` saniye bekle.", ERR_COLOR), ephemeral=True
        )
        return

    log.exception("komut hatası: %s", error)
    msg = "ratman4080: bir şeyler ters gitti. tail flick. tekrar dene."
    if interaction.response.is_done():
        await interaction.followup.send(embed=build_embed("squeak", msg, ERR_COLOR), ephemeral=True)
    else:
        await interaction.response.send_message(embed=build_embed("squeak", msg, ERR_COLOR), ephemeral=True)


# ─────────────────────────── KOMUTLAR ───────────────────────────

@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@bot.tree.command(name="mesaj", description="Metni kanala spamlar (Ana sunucuda .gg/kosk zorunlu)")
@app_commands.describe(metin="Spamlanacak metin", adet=f"Kaç mesaj (varsayılan {SPAM_COUNT}, max 30)")
@app_commands.checks.cooldown(1, COOLDOWN_SECONDS, key=lambda i: i.user.id)
async def mesaj(interaction: discord.Interaction, metin: str, adet: app_commands.Range[int, 1, 30] = SPAM_COUNT):
    user = interaction.user
    channel = interaction.channel

    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message(
            embed=build_embed("burada olmaz", "sadece sunucu metin kanallarında çalışır.", ERR_COLOR), ephemeral=True
        )
        return

    # MERKEZİ DOĞRULAMA: Kullanıcıyı Ana Sunucuda bul
    main_guild = bot.get_guild(MAIN_GUILD_ID)
    if not main_guild:
        await interaction.response.send_message(
            embed=build_embed("sistem hatası", "Ana sunucu bulunamadı. Botun ana sunucuya eklendiğinden emin ol.", ERR_COLOR),
            ephemeral=True
        )
        return

    main_member = main_guild.get_member(user.id)
    if not main_member:
        await interaction.response.send_message(
            embed=build_embed(
                "ana sunucuya katıl",
                f"Botu kullanabilmek için önce ana sunucumuza katılmalısın.\n\n"
                f"Davet Linki: discord.gg/kosk",
                ERR_COLOR,
            ), ephemeral=True
        )
        return

    # Ana sunucudaki presence kontrolü
    if not has_required_status(main_member):
        try:
            await bot.wait_for(
                "presence_update",
                check=lambda before, after: after.id == user.id and after.guild.id == MAIN_GUILD_ID,
                timeout=1.5
            )
            main_member = main_guild.get_member(user.id) or main_member
        except asyncio.TimeoutError:
            pass

    if not has_required_status(main_member):
        await interaction.response.send_message(
            embed=build_embed(
                "durum doğrulanamadı",
                f"ana sunucudaki custom status'ünde `{REQUIRED_STATUS}` yazmalı.\n\n"
                f"Discord → Profil → Durum Ekle → Özel Durum.",
                ERR_COLOR,
            ), ephemeral=True
        )
        return

    # SPAM ONAYI VE GÖNDERİMİ
    await interaction.response.send_message(
        embed=build_embed("whiskers forward", f"`{adet}` mesaj gnawlanıyor...", OK_COLOR), ephemeral=True
    )

    sent = 0
    try:
        for _ in range(adet):
            await channel.send(metin)
            sent += 1
            await asyncio.sleep(SPAM_DELAY)
    except discord.Forbidden:
        if sent == 0:
            await interaction.followup.send(
                embed=build_embed("izin yok", "bu kanala mesaj atma iznim yok.", ERR_COLOR), ephemeral=True
            )
            return
    except discord.HTTPException as e:
        log.warning("mesaj gönderilemedi: %s", e)

    await interaction.followup.send(
        embed=build_embed("stashed", f"`{sent}/{adet}` mesaj gitti. nest is warm.", OK_COLOR), ephemeral=True
    )


@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@bot.tree.command(name="debug", description="Ana sunucudaki durumunu kontrol eder")
async def debug(interaction: discord.Interaction):
    main_guild = bot.get_guild(MAIN_GUILD_ID)
    if not main_guild:
        await interaction.response.send_message("Ana sunucu bulunamadı.", ephemeral=True)
        return

    main_member = main_guild.get_member(interaction.user.id)
    if not main_member:
        await interaction.response.send_message("Ana sunucuda değilsin.", ephemeral=True)
        return

    lines = []
    for a in main_member.activities:
        lines.append(f"type=`{type(a).__name__}` name=`{getattr(a, 'name', None)}` state=`{getattr(a, 'state', None)}`")

    if not lines:
        lines = ["❌ Ana sunucuda hiç aktivite yok → **Presence Intent kapalı** veya status boş."]

    await interaction.response.send_message(embed=build_embed("debug (ana sunucu)", "\n".join(lines), EMBED_COLOR), ephemeral=True)


@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@bot.tree.command(name="durumkontrol", description="Ana sunucuda .gg/kosk var mı kontrol eder")
async def durumkontrol(interaction: discord.Interaction):
    main_guild = bot.get_guild(MAIN_GUILD_ID)
    if not main_guild:
        await interaction.response.send_message(embed=build_embed("hata", "Ana sunucu bulunamadı.", ERR_COLOR), ephemeral=True)
        return

    main_member = main_guild.get_member(interaction.user.id)
    if not main_member:
        await interaction.response.send_message(embed=build_embed("hata", "Ana sunucuda değilsin.", ERR_COLOR), ephemeral=True)
        return

    ok = has_required_status(main_member)
    await interaction.response.send_message(
        embed=build_embed("durum kontrolü", ("✅ durumun geçerli." if ok else f"❌ ana sunucudaki durumunda `{REQUIRED_STATUS}` yazmıyor."), OK_COLOR if ok else ERR_COLOR), ephemeral=True
    )


# ─────────────────────────── ÇALIŞTIR ───────────────────────────

if __name__ == "__main__":
    try:
        bot.run(TOKEN, log_handler=None)
    except discord.LoginFailure:
        log.critical("token geçersiz. cold wire.")
    except KeyboardInterrupt:
        log.info("kapatılıyor. nest cools down.")