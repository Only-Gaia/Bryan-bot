import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
from datetime import datetime, timedelta, timezone
import data


# In-memory: raccoglie le risposte della candidatura staff mentre l'utente
# compila i vari step (non serve persistenza su disco, il flusso dura pochi minuti)
STAFF_APPLICATIONS: dict[int, dict] = {}


# =========================================================
#                  CANDIDATURA STAFF (MODALI)
# =========================================================
# Un modal Discord supporta al massimo 5 campi di testo, quindi le 11
# domande sono divise in 3 step collegati da un pulsante "Continua ➡️".

class StaffModal3(Modal, title="Candidatura Staff (3/3)"):
    descrizione = TextInput(
        label="Descrizione di te stesso (facoltativo)",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=1000,
    )

    def __init__(self, cog: "Moderation"):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        answers = STAFF_APPLICATIONS.pop(interaction.user.id, {})
        answers["descrizione"] = self.descrizione.value or "Non fornita"
        await self.cog.send_application(interaction, answers)


class StaffModal2(Modal, title="Candidatura Staff (2/3)"):
    server_membri = TextInput(
        label="Se sì, quale? E quanti membri?",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=300,
    )
    comandi_conosciuti = TextInput(
        label="Quali comandi conosci?",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500,
    )
    ore_discord = TextInput(
        label="Quante ore sei su Discord (al giorno)?",
        required=True,
        max_length=100,
    )
    scenario_litigio = TextInput(
        label="2 membri litigano con insulti pesanti?",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500,
    )
    scenario_insulti_staff = TextInput(
        label="Cosa fai se insultano lo staff?",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500,
    )

    def __init__(self, cog: "Moderation"):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        answers = STAFF_APPLICATIONS.setdefault(interaction.user.id, {})
        answers["server_membri"] = self.server_membri.value or "N/A"
        answers["comandi_conosciuti"] = self.comandi_conosciuti.value
        answers["ore_discord"] = self.ore_discord.value
        answers["scenario_litigio"] = self.scenario_litigio.value
        answers["scenario_insulti_staff"] = self.scenario_insulti_staff.value

        view = View(timeout=300)
        continue_button = Button(label="Continua ➡️", style=discord.ButtonStyle.blurple)

        async def continue_callback(inter: discord.Interaction):
            await inter.response.send_modal(StaffModal3(self.cog))

        continue_button.callback = continue_callback
        view.add_item(continue_button)

        await interaction.response.send_message(
            "✅ Passo 2/3 completato. Premi il pulsante per continuare.", view=view, ephemeral=True
        )


class StaffModal1(Modal, title="Candidatura Staff (1/3)"):
    nome = TextInput(label="Come ti chiami?", required=True, max_length=100)
    eta = TextInput(label="1) Quanti anni hai?", required=True, max_length=10)
    ruolo = TextInput(label="2) Per che ruolo ti candidi?", required=True, max_length=100)
    motivazione = TextInput(
        label="3) Perché vuoi candidarti staff?",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500,
    )
    gia_staff = TextInput(label="4) Sei già stato staff altrove?", required=True, max_length=50)

    def __init__(self, cog: "Moderation"):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        STAFF_APPLICATIONS[interaction.user.id] = {
            "nome": self.nome.value,
            "eta": self.eta.value,
            "ruolo": self.ruolo.value,
            "motivazione": self.motivazione.value,
            "gia_staff": self.gia_staff.value,
        }

        view = View(timeout=300)
        continue_button = Button(label="Continua ➡️", style=discord.ButtonStyle.blurple)

        async def continue_callback(inter: discord.Interaction):
            await inter.response.send_modal(StaffModal2(self.cog))

        continue_button.callback = continue_callback
        view.add_item(continue_button)

        await interaction.response.send_message(
            "✅ Passo 1/3 completato. Premi il pulsante per continuare.", view=view, ephemeral=True
        )


class StaffPanelView(View):
    def __init__(self, cog: "Moderation"):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Candidati", style=discord.ButtonStyle.green, emoji="📝", custom_id="staff_apply_start")
    async def apply(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(StaffModal1(self.cog))


# =========================================================
#                        MODERAZIONE
# =========================================================

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(StaffPanelView(self))

    # ---------- WARN ----------
    @commands.hybrid_command(name="warn", description="Warna un utente")
    @commands.has_permissions(moderate_members=True)
    async def warn(self, ctx, member: discord.Member, *, reason: str = "Nessun motivo specificato"):
        warns = data.load("warns")
        g = warns.setdefault(str(ctx.guild.id), {})
        user_warns = g.setdefault(str(member.id), [])
        user_warns.append({
            "reason": reason,
            "moderator": ctx.author.id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        data.save("warns", warns)

        embed = discord.Embed(title="⚠️ Utente warnato", color=discord.Color.orange())
        embed.add_field(name="Utente", value=member.mention)
        embed.add_field(name="Moderatore", value=ctx.author.mention)
        embed.add_field(name="Motivo", value=reason, inline=False)
        embed.add_field(name="Totale warn", value=str(len(user_warns)))
        await ctx.send(embed=embed)

        try:
            await member.send(f"⚠️ Sei stato warnato in **{ctx.guild.name}**.\nMotivo: {reason}")
        except discord.Forbidden:
            pass

    # ---------- CLEARWARN (rimuove tutti i warn) ----------
    @commands.hybrid_command(name="clearwarn", aliases=["leavearn"], description="Rimuove tutti i warn di un utente")
    @commands.has_permissions(moderate_members=True)
    async def clearwarn(self, ctx, member: discord.Member):
        warns = data.load("warns")
        g = warns.setdefault(str(ctx.guild.id), {})
        if not g.get(str(member.id)):
            return await ctx.send(f"✅ {member.mention} non ha warn da rimuovere.")
        g[str(member.id)] = []
        data.save("warns", warns)
        await ctx.send(f"✅ Tutti i warn di {member.mention} sono stati rimossi.")

    # ---------- WARNSHOW ----------
    @commands.hybrid_command(name="warnshow", description="Mostra i warn di un utente")
    async def warnshow(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        warns = data.load("warns").get(str(ctx.guild.id), {}).get(str(member.id), [])
        if not warns:
            return await ctx.send(f"✅ {member.mention} non ha warn.")

        embed = discord.Embed(title=f"⚠️ Warn di {member}", color=discord.Color.orange())
        for i, w in enumerate(warns, start=1):
            mod = ctx.guild.get_member(w.get("moderator"))
            embed.add_field(
                name=f"#{i}",
                value=f"Motivo: {w.get('reason', 'N/A')}\nModeratore: {mod.mention if mod else w.get('moderator')}",
                inline=False,
            )
        embed.set_footer(text=f"Totale: {len(warns)} warn")
        await ctx.send(embed=embed)

    # ---------- BAN / UNBAN ----------
    @commands.hybrid_command(name="ban", description="Banna un utente")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str = "Nessun motivo specificato"):
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send("❌ Non puoi bannare un utente con un ruolo pari o superiore al tuo.")
        try:
            await member.ban(reason=f"{reason} (da {ctx.author})")
        except discord.Forbidden:
            return await ctx.send("❌ Non ho i permessi per bannare questo utente.")

        embed = discord.Embed(title="🔨 Utente bannato", color=discord.Color.red())
        embed.add_field(name="Utente", value=f"{member} ({member.id})")
        embed.add_field(name="Moderatore", value=ctx.author.mention)
        embed.add_field(name="Motivo", value=reason, inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="unban", description="Rimuove il ban a un utente tramite ID")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: str):
        try:
            uid = int(user_id)
        except ValueError:
            return await ctx.send("❌ ID utente non valido.")

        try:
            user = await self.bot.fetch_user(uid)
            await ctx.guild.unban(user, reason=f"Unban richiesto da {ctx.author}")
        except discord.NotFound:
            return await ctx.send("❌ Utente non trovato o non bannato.")
        except discord.Forbidden:
            return await ctx.send("❌ Non ho i permessi per rimuovere il ban.")

        await ctx.send(f"✅ {user} è stato sbannato.")

    # ---------- KICK ----------
    @commands.hybrid_command(name="kick", description="Espelle un utente")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = "Nessun motivo specificato"):
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send("❌ Non puoi espellere un utente con un ruolo pari o superiore al tuo.")
        try:
            await member.kick(reason=f"{reason} (da {ctx.author})")
        except discord.Forbidden:
            return await ctx.send("❌ Non ho i permessi per espellere questo utente.")

        embed = discord.Embed(title="👢 Utente espulso", color=discord.Color.orange())
        embed.add_field(name="Utente", value=f"{member} ({member.id})")
        embed.add_field(name="Moderatore", value=ctx.author.mention)
        embed.add_field(name="Motivo", value=reason, inline=False)
        await ctx.send(embed=embed)

    # ---------- MUTE / UNMUTE (timeout) ----------
    @commands.hybrid_command(name="mute", description="Mette in timeout un utente (durata in minuti)")
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx, member: discord.Member, minutes: int, *, reason: str = "Nessun motivo specificato"):
        if minutes <= 0:
            return await ctx.send("❌ La durata deve essere maggiore di 0 minuti.")

        try:
            await member.timeout(timedelta(minutes=minutes), reason=f"{reason} (da {ctx.author})")
        except discord.Forbidden:
            return await ctx.send("❌ Non ho i permessi per mutare questo utente.")

        embed = discord.Embed(title="🔇 Utente mutato", color=discord.Color.dark_grey())
        embed.add_field(name="Utente", value=member.mention)
        embed.add_field(name="Durata", value=f"{minutes} minuti")
        embed.add_field(name="Motivo", value=reason, inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="unmute", description="Rimuove il timeout a un utente")
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx, member: discord.Member):
        try:
            await member.timeout(None, reason=f"Unmute richiesto da {ctx.author}")
        except discord.Forbidden:
            return await ctx.send("❌ Non ho i permessi per smutare questo utente.")
        await ctx.send(f"✅ {member.mention} è stato smutato.")

    # ---------- LOCK / UNLOCK ----------
    @commands.hybrid_command(name="lock", description="Blocca il canale corrente (o quello specificato)")
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        try:
            await channel.set_permissions(ctx.guild.default_role, send_messages=False)
        except discord.Forbidden:
            return await ctx.send("❌ Non ho i permessi per bloccare questo canale.")
        await ctx.send(f"🔒 {channel.mention} è stato bloccato.")

    @commands.hybrid_command(name="unlock", description="Sblocca il canale corrente (o quello specificato)")
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        try:
            await channel.set_permissions(ctx.guild.default_role, send_messages=None)
        except discord.Forbidden:
            return await ctx.send("❌ Non ho i permessi per sbloccare questo canale.")
        await ctx.send(f"🔓 {channel.mention} è stato sbloccato.")

    # ---------- PURGE ----------
    @commands.hybrid_command(name="purge", description="Cancella un numero di messaggi dal canale (max 100)")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int):
        amount = max(1, min(amount, 100))

        if ctx.interaction:
            await ctx.defer(ephemeral=True)
            deleted = await ctx.channel.purge(limit=amount)
            await ctx.send(f"🧹 Cancellati {len(deleted)} messaggi.", ephemeral=True)
        else:
            deleted = await ctx.channel.purge(limit=amount + 1)  # +1 include il messaggio del comando
            msg = await ctx.send(f"🧹 Cancellati {len(deleted) - 1} messaggi.")
            await msg.delete(delay=3)

    # ---------- PEX / DEPEX ----------
    @commands.hybrid_command(name="pex", description="Assegna un ruolo a un utente")
    @commands.has_permissions(manage_roles=True)
    async def pex(self, ctx, member: discord.Member, role: discord.Role):
        if role >= ctx.guild.me.top_role:
            return await ctx.send("❌ Non posso assegnare un ruolo pari o superiore al mio ruolo più alto.")
        try:
            await member.add_roles(role, reason=f"Pex da {ctx.author}")
        except discord.Forbidden:
            return await ctx.send("❌ Non ho i permessi per assegnare questo ruolo.")
        await ctx.send(f"✅ Ruolo {role.mention} assegnato a {member.mention}.")

    @commands.hybrid_command(name="depex", description="Rimuove un ruolo a un utente")
    @commands.has_permissions(manage_roles=True)
    async def depex(self, ctx, member: discord.Member, role: discord.Role):
        if role >= ctx.guild.me.top_role:
            return await ctx.send("❌ Non posso rimuovere un ruolo pari o superiore al mio ruolo più alto.")
        try:
            await member.remove_roles(role, reason=f"Depex da {ctx.author}")
        except discord.Forbidden:
            return await ctx.send("❌ Non ho i permessi per rimuovere questo ruolo.")
        await ctx.send(f"✅ Ruolo {role.mention} rimosso da {member.mention}.")

    # ---------- CANDIDATURA STAFF ----------
    @commands.hybrid_command(name="staff", description="Apri il modulo di candidatura staff")
    async def staff(self, ctx):
        embed = discord.Embed(
            title="📋 CANDIDATURA STAFF",
            description=(
                "Vuoi entrare a far parte del nostro team? Premi il pulsante qui sotto "
                "e rispondi alle domande che ti verranno proposte in 3 step.\n\n"
                "**Come ti chiami?**\n"
                "1) Quanti anni hai?\n"
                "2) Per che ruolo ti candidi?\n"
                "3) Perché vuoi candidarti staff?\n"
                "4) Sei già stato staff in altri server?\n"
                "5) Se sì, quale? E quanti membri?\n"
                "6) Quali comandi conosci?\n"
                "7) Quante ore sei su Discord?\n"
                "8) Cosa faresti se due membri iniziano a litigare usando insulti pesanti?\n"
                "9) Cosa fai se un membro insulta lo staff?\n"
                "10) Fai una descrizione di te stesso (facoltativo)"
            ),
            color=discord.Color.gold(),
        )
        embed.set_footer(text="Premi 'Candidati' per iniziare • Risponderai in 3 step")
        await ctx.send(embed=embed, view=StaffPanelView(self))

    @commands.hybrid_command(name="setstafflog", description="Imposta il canale dove arrivano le candidature staff")
    @commands.has_permissions(administrator=True)
    async def setstafflog(self, ctx, channel: discord.TextChannel):
        settings = data.load("settings")
        g = settings.setdefault(str(ctx.guild.id), {})
        g["staff_applications_channel"] = channel.id
        data.save("settings", settings)
        await ctx.send(f"✅ Le candidature staff verranno inviate in {channel.mention}")

    # ---------- INVIO CANDIDATURA COMPILATA ----------
    async def send_application(self, interaction: discord.Interaction, answers: dict):
        guild = interaction.guild
        settings = data.load("settings").get(str(guild.id), {}) if guild else {}
        log_id = settings.get("staff_applications_channel")
        log_channel = guild.get_channel(log_id) if (guild and log_id) else None

        embed = discord.Embed(title="📋 Nuova candidatura staff", color=discord.Color.gold())
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="Come ti chiami?", value=answers.get("nome", "N/A"), inline=False)
        embed.add_field(name="1) Quanti anni hai?", value=answers.get("eta", "N/A"))
        embed.add_field(name="2) Per che ruolo ti candidi?", value=answers.get("ruolo", "N/A"))
        embed.add_field(name="3) Perché vuoi candidarti staff?", value=answers.get("motivazione", "N/A"), inline=False)
        embed.add_field(name="4) Sei già stato staff altrove?", value=answers.get("gia_staff", "N/A"))
        embed.add_field(name="5) Se sì, quale? E quanti membri?", value=answers.get("server_membri", "N/A"), inline=False)
        embed.add_field(name="6) Quali comandi conosci?", value=answers.get("comandi_conosciuti", "N/A"), inline=False)
        embed.add_field(name="7) Quante ore sei su Discord?", value=answers.get("ore_discord", "N/A"))
        embed.add_field(
            name="8) Due membri litigano con insulti pesanti, cosa fai?",
            value=answers.get("scenario_litigio", "N/A"),
            inline=False,
        )
        embed.add_field(
            name="9) Cosa fai se un membro insulta lo staff?",
            value=answers.get("scenario_insulti_staff", "N/A"),
            inline=False,
        )
        embed.add_field(name="10) Descrizione di te stesso", value=answers.get("descrizione", "Non fornita"), inline=False)
        embed.set_footer(text=f"Candidato: {interaction.user} • ID: {interaction.user.id}")
        embed.timestamp = datetime.now(timezone.utc)

        if log_channel:
            await log_channel.send(embed=embed)
            await interaction.response.send_message("✅ Candidatura inviata con successo allo staff!", ephemeral=True)
        else:
            await interaction.response.send_message(
                "⚠️ Candidatura completata ma nessun canale per le candidature è stato configurato "
                "(un admin deve usare `setstafflog`). Contatta un amministratore.",
                ephemeral=True,
            )


async def setup(bot):
    await bot.add_cog(Moderation(bot))
