import os
import discord
from discord.ext import commands

# =========================
# INTENTS
# =========================
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

# =========================
# BOT SETUP
# =========================
bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# CONFIG SERVER JUSTCHILL
# =========================
SERVER_NAME = "JustChill"

# =========================
# ID RUOLI
# =========================
STAFF_ROLE_ID = 1491874337769132074
PARTNERSHIP_ROLE_ID = 1491874337769132073

# =========================
# ID CATEGORIA TICKETS
# =========================
TICKETS_CATEGORY_ID = 1491904885988397198


# =========================
# FUNZIONE UTILE
# =========================
def make_channel_name(category_value: str, username: str) -> str:
    safe_name = username.lower().replace(" ", "-")
    return f"{category_value}-{safe_name}"


# =========================
# VIEW CHIUSURA TICKET
# =========================
class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Chiudi Ticket",
        style=discord.ButtonStyle.red,
        emoji="🔒",
        custom_id="close_ticket_button"
    )
    async def close_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        if guild is None:
            await interaction.response.send_message(
                "❌ Errore: server non trovato.",
                ephemeral=True
            )
            return

        staff_role = guild.get_role(STAFF_ROLE_ID)

        if staff_role is None:
            await interaction.response.send_message(
                "❌ Errore: ruolo staff non trovato.",
                ephemeral=True
            )
            return

        if staff_role not in user.roles:
            await interaction.response.send_message(
                "❌ Solo lo staff di JustChill può chiudere il ticket.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🔒 Ticket chiuso correttamente. Il canale verrà eliminato adesso."
        )
        await interaction.channel.delete()


# =========================
# SELECT MENU CATEGORIE
# =========================
class TicketCategorySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Assistenza",
                description="Apri un ticket per ricevere aiuto dallo staff",
                emoji="🛠️",
                value="assistenza"
            ),
            discord.SelectOption(
                label="Partnership",
                description="Apri un ticket per una collaborazione o partnership",
                emoji="🤝",
                value="partnership"
            ),
            discord.SelectOption(
                label="Segnalazione",
                description="Apri un ticket per segnalare un problema o un utente",
                emoji="🚨",
                value="segnalazione"
            ),
            discord.SelectOption(
                label="Candidatura Staff",
                description="Apri un ticket per candidarti come staffer",
                emoji="📋",
                value="candidatura-staff"
            ),
        ]

        super().__init__(
            placeholder="Scegli la categoria del tuo ticket...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="ticket_category_select"
        )

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user

        if guild is None:
            await interaction.response.send_message(
                "❌ Errore: server non trovato.",
                ephemeral=True
            )
            return

        category = guild.get_channel(TICKETS_CATEGORY_ID)

        if category is None:
            await interaction.response.send_message(
                "❌ Errore: la categoria ticket non è stata trovata. Controlla l'ID della categoria.",
                ephemeral=True
            )
            return

        selected_category = self.values[0]
        channel_name = make_channel_name(selected_category, user.name)

        existing_channel = discord.utils.get(guild.text_channels, name=channel_name)
        if existing_channel is not None:
            await interaction.response.send_message(
                f"❌ Hai già un ticket aperto per questa categoria: {existing_channel.mention}",
                ephemeral=True
            )
            return

        bot_member = guild.me
        if bot_member is None:
            await interaction.response.send_message(
                "❌ Errore: non riesco a trovare il bot nel server.",
                ephemeral=True
            )
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),
            user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            ),
            bot_member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
                manage_messages=True,
                embed_links=True
            )
        }

        staff_role = guild.get_role(STAFF_ROLE_ID)
        partnership_role = guild.get_role(PARTNERSHIP_ROLE_ID)

        if staff_role is not None:
            overwrites[staff_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True
            )

        if selected_category == "partnership" and partnership_role is not None:
            overwrites[partnership_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True
            )

        created_channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"Ticket {selected_category} di {user.name} | Server: {SERVER_NAME}"
        )

        if selected_category == "assistenza":
            description_text = (
                f"Ciao {user.mention}, benvenuto nel tuo ticket di **assistenza** su **{SERVER_NAME}**.\n\n"
                "Qui puoi spiegare con calma il tuo problema.\n"
                "Più dettagli scrivi, più sarà facile per lo staff aiutarti nel modo giusto.\n\n"
                "**Cose utili da scrivere:**\n"
                "• cosa è successo\n"
                "• quando è successo\n"
                "• eventuali screen o prove\n"
                "• se il problema riguarda un canale, bot o utente\n\n"
                "Uno staffer ti risponderà appena possibile."
            )
        elif selected_category == "partnership":
            description_text = (
                f"Ciao {user.mention}, benvenuto nel tuo ticket di **partnership** su **{SERVER_NAME}**.\n\n"
                "Scrivi qui la tua proposta di collaborazione.\n\n"
                "**Ti consigliamo di includere:**\n"
                "• nome del tuo server o progetto\n"
                "• numero membri\n"
                "• tipo di partnership che vuoi proporre\n"
                "• eventuali link utili\n\n"
                "Il gestore partnership o lo staff controlleranno il prima possibile."
            )
        elif selected_category == "segnalazione":
            description_text = (
                f"Ciao {user.mention}, benvenuto nel tuo ticket di **segnalazione** su **{SERVER_NAME}**.\n\n"
                "Scrivi qui la tua segnalazione in modo chiaro.\n\n"
                "**Ti consigliamo di includere:**\n"
                "• chi vuoi segnalare\n"
                "• cosa è successo\n"
                "• prove, screenshot o messaggi\n"
                "• orario o contesto\n\n"
                "Lo staff valuterà la situazione con attenzione."
            )
        else:
            description_text = (
                f"Ciao {user.mention}, benvenuto nel tuo ticket di **candidatura staff** su **{SERVER_NAME}**.\n\n"
                "Compila con calma questo piccolo modulo direttamente qui sotto.\n\n"
                "**Domande candidatura:**\n"
                "1. Quanti anni hai?\n"
                "2. Da quanto tempo usi Discord?\n"
                "3. Hai già avuto esperienza come staff? Se sì, dove?\n"
                "4. Perché vuoi diventare staff di JustChill?\n"
                "5. Quanto sei attivo al giorno?\n"
                "6. Quali qualità pensi di avere per questo ruolo?\n\n"
                "Rispondi bene a tutto e aspetta la valutazione dello staff."
            )

        ticket_embed = discord.Embed(
            title=f"🎫 Ticket {SERVER_NAME}",
            description=description_text,
            color=discord.Color.green()
        )
        ticket_embed.set_footer(text=f"{SERVER_NAME} • Sistema Ticket")

        mentions = [user.mention]

        if selected_category == "partnership" and partnership_role is not None:
            mentions.append(partnership_role.mention)
        elif staff_role is not None:
            mentions.append(staff_role.mention)

        await created_channel.send(
            content=" ".join(mentions),
            embed=ticket_embed,
            view=CloseTicketView()
        )

        await interaction.response.send_message(
            f"✅ Il tuo ticket è stato creato correttamente: {created_channel.mention}",
            ephemeral=True
        )


# =========================
# VIEW SELECT
# =========================
class TicketCategoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCategorySelect())


# =========================
# VIEW APRI TICKET
# =========================
class OpenTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Apri Ticket",
        style=discord.ButtonStyle.green,
        emoji="🎫",
        custom_id="open_ticket_button"
    )
    async def open_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        open_embed = discord.Embed(
            title=f"🎫 Ticket {SERVER_NAME}",
            description=(
                f"Benvenuto nel pannello ticket di **{SERVER_NAME}**.\n\n"
                "Seleziona dal menu la categoria più adatta al tuo problema o alla tua richiesta."
            ),
            color=discord.Color.blurple()
        )
        open_embed.set_footer(text=f"{SERVER_NAME} • Selezione Categoria")

        await interaction.response.send_message(
            embed=open_embed,
            view=TicketCategoryView(),
            ephemeral=True
        )


# =========================
# READY EVENT
# =========================
@bot.event
async def on_ready():
    bot.add_view(OpenTicketView())
    bot.add_view(CloseTicketView())
    bot.add_view(TicketCategoryView())
    print(f"Bot ticket online come {bot.user} nel server {SERVER_NAME}")


# =========================
# COMANDO PANNELLO TICKET
# =========================
@bot.command()
async def ticket(ctx):
    panel_embed = discord.Embed(
        title=f"🎫 Supporto {SERVER_NAME}",
        description=(
            f"Benvenuto nel sistema ticket di **{SERVER_NAME}**.\n\n"
            "Premi il bottone qui sotto per aprire un ticket.\n\n"
            "**Categorie disponibili:**\n"
            "🛠️ Assistenza\n"
            "🤝 Partnership\n"
            "🚨 Segnalazione\n"
            "📋 Candidatura Staff"
        ),
        color=discord.Color.blurple()
    )
    panel_embed.set_footer(text=f"{SERVER_NAME} • Pannello Ticket")

    await ctx.send(embed=panel_embed, view=OpenTicketView())


# =========================
# COMANDO CANDIDATURA ACCETTATA
# =========================
@bot.command()
async def candidaturasi(ctx, membro: discord.Member = None):
    if membro is None:
        await ctx.send("❌ Usa così: `!candidaturasi @utente`")
        return

    accepted_embed = discord.Embed(
        title=f"✅ Candidatura accettata • {SERVER_NAME}",
        description=(
            f"Ciao {membro.mention},\n\n"
            f"siamo felici di dirti che la tua candidatura come **Staffer** in **{SERVER_NAME}** è stata **accettata**! 🎉\n\n"
            "Abbiamo letto con attenzione le tue risposte e pensiamo che tu possa essere adatto a questo ruolo.\n"
            "Hai dimostrato impegno, interesse e una buona base per entrare nel team.\n\n"
            "A breve riceverai maggiori informazioni sui prossimi passaggi.\n"
            "Ti chiediamo di essere attivo, serio, rispettoso e di dare sempre una mano quando serve.\n\n"
            f"**Benvenuto nel team di {SERVER_NAME} 💙**"
        ),
        color=discord.Color.green()
    )
    accepted_embed.set_footer(text=f"{SERVER_NAME} • Sistema Candidature")

    await ctx.send(embed=accepted_embed)


# =========================
# COMANDO CANDIDATURA RIFIUTATA
# =========================
@bot.command()
async def candidaturano(ctx, membro: discord.Member = None):
    if membro is None:
        await ctx.send("❌ Usa così: `!candidaturano @utente`")
        return

    refused_embed = discord.Embed(
        title=f"❌ Candidatura non accettata • {SERVER_NAME}",
        description=(
            f"Ciao {membro.mention},\n\n"
            f"grazie per aver inviato la tua candidatura come **Staffer** su **{SERVER_NAME}**.\n\n"
            "Dopo averla valutata con attenzione, abbiamo deciso di **non accettarla al momento**.\n\n"
            "Questo però non vuol dire che tu non possa riprovare in futuro.\n"
            "Continua a essere attivo nel server, mantieni un bel comportamento e prova a migliorare ancora.\n\n"
            "Ti ringraziamo comunque per il tempo che hai dedicato alla candidatura e per l’interesse verso il server 💙"
        ),
        color=discord.Color.red()
    )
    refused_embed.set_footer(text=f"{SERVER_NAME} • Sistema Candidature")

    await ctx.send(embed=refused_embed)


# =========================
# AVVIO BOT
# =========================
bot.run(os.getenv("TOKEN"))