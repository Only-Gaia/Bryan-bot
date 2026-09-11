import discord
from discord.ext import commands
import config


# ---------------- ELENCO COMANDI ----------------

COMMANDS = [
    ("warn <member> [reason]", "🔒 Warna un utente"),
    ("clearwarn <member>", "🔒 Rimuove tutti i warn di un utente (alias: leavearn)"),
    ("warnshow [member]", "Mostra i warn di un utente"),
    ("ban <member> [reason]", "🔒 Banna un utente"),
    ("unban <user_id>", "🔒 Rimuove il ban a un utente"),
    ("kick <member> [reason]", "🔒 Espelle un utente"),
    ("mute <member> <minutes> [reason]", "🔒 Mette in timeout un utente"),
    ("unmute <member>", "🔒 Rimuove il timeout a un utente"),
    ("lock [channel]", "🔒 Blocca il canale corrente (o quello specificato)"),
    ("unlock [channel]", "🔒 Sblocca il canale corrente (o quello specificato)"),
    ("purge <amount>", "🔒 Cancella N messaggi dal canale (max 100)"),
    ("pex <member> <role>", "🔒 Assegna un ruolo a un utente"),
    ("depex <member> <role>", "🔒 Rimuove un ruolo a un utente"),
    ("staff", "Apri il modulo di candidatura staff"),
    ("setstafflog <channel>", "🔒 Imposta il canale dove arrivano le candidature staff"),
]


def build_help_embed(guild: discord.Guild) -> discord.Embed:
    embed = discord.Embed(
        title="🛡️ Centro Assistenza - Moderazione",
        description=(
            f"Elenco di tutti i comandi disponibili.\n"
            f"Funzionano sia con il prefisso `{config.PREFIX}` che come slash `/`.\n"
            "🔒 = richiede permessi specifici"
        ),
        color=config.EMBED_COLOR,
    )
    for name, desc in COMMANDS:
        embed.add_field(name=f"`{name}`", value=desc, inline=False)
    embed.set_footer(text=f"{guild.name if guild else 'Bot'} • {len(COMMANDS)} comandi")
    return embed


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="help", description="Mostra la lista dei comandi del bot")
    async def help(self, ctx: commands.Context):
        embed = build_help_embed(ctx.guild)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Help(bot))
