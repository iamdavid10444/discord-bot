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
# CONFIG SERVER
# =========================
SERVER_NAME = "JustChill"

# =========================
# ID RUOLI
# =========================
STAFF_ROLE_ID = 1491874337769132074
PARTNERSHIP_ROLE_ID = 1491874337769132073
CO_OWNER_ROLE_ID = 1492661581383733459

# =========================
# ID CATEGORIA TICKETS
# =========================
TICKETS_CATEGORY_ID = 1491904885988397198


# =========================
# FUNZIONI UTILI
# =========================
def make_safe_channel_name(prefix: str, username: str) -> str:
    safe_name = username.lower().replace(" ", "-")
    safe_name = "".join(c for c in safe_name if c.isalnum() or c == "-")
    return f"{prefix}-{safe_name}"[:90]


def get_ticket_topic(user_id: int, category_name: str, username: str) -> str:
    return f"ticket_owner_id={user_id};category={category_name};username={username}"


def extract_ticket_owner_id(topic: str):
    if not topic:
        return None

    parts = topic.split(";")
    for part in parts:
        if part.startswith("ticket_owner_id="):
            try:
                return int(part.replace("ticket_owner_id=", ""))
            except:
                return None
    return None


def extract_ticket_category(topic: str):
    if not topic:
        return "sconosciuta"

    parts = topic.split(";")
    for part in parts:
        if part.startswith("category="):
            return part.replace("category=", "")
    return "sconosciuta"


async def send_dm_safe(user: discord.abc.User, embed: discord.Embed):
    try:
        await user.send(embed=embed)
    except:
        pass


def is_staff_or_coowner(member: discord.Member) -> bool:
    role_ids = {role.id for role in member.roles}
    return STAFF_ROLE_ID in role_ids or CO_OWNER_ROLE_ID in role_ids


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
        channel = interaction.channel
        user = interaction.user

        if guild is None or channel is None:
            await interaction.response.send_message(
                "❌ Errore: server o canale non trovato.",
                ephemeral=True
            )
            return

        if not isinstance(user, discord.Member):
            await interaction.response.send_message(
                "❌ Errore: utente non valido.",
                ephemeral=True
            )
            return

        if not is_staff_or_coowner(user):
            await interaction.response.send_message(
                f"❌ Solo lo staff di **{SERVER_NAME}** può chiudere questo ticket.",
                ephemeral=True
            )
            return

        topic = channel.topic or ""
        owner_id = extract_ticket_owner_id(topic)
        category_name = extract_ticket_category(topic)

        if owner_id is not None:
            try:
                ticket_owner = await bot.fetch_user(owner_id)
                close_embed = discord.Embed(
                    title=f"🔒 Ticket chiuso • {SERVER_NAME}",
                    description=(
                        f"Il tuo ticket è stato chiuso nel server **{SERVER_NAME}**.\n\n"
                        f"**Canale:** `{channel.name}`\n"
                        f"**Categoria:** `{category_name}`\n"
                        f"**Chiuso da:** {user.mention}\n\n"
                        f"Grazie per aver usato il sistema ticket di **{SERVER_NAME}**."
                    ),
                    color=discord.Color.red()
                )
                close_embed.set_footer(text=f"{SERVER_NAME} • Ticket Logs Privati")
                await send_dm_safe(ticket_owner, close_embed)
            except:
                pass

        await interaction.response.send_message(
            "🔒 Ticket chiuso correttamente. Il canale verrà eliminato tra poco."
        )

        try:
            await channel.delete(reason=f"Ticket chiuso da {user}")
        except discord.Forbidden:
            await channel.send("❌ Non posso eliminare il canale: mi manca il permesso **Gestisci Canali**.")
        except discord.HTTPException:
            await channel.send("❌ Errore Discord durante l'eliminazione del canale.")


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
                description="Apri un ticket per partnership o collaborazioni",
                emoji="🤝",
                value="partnership"
            ),
            discord.SelectOption(
                label="Segnalazione",
                description="Apri un ticket per fare una segnalazione",
                emoji="🚨",
                value="segnalazione"
            ),
            discord.SelectOption(
                label="Candidatura Staff",
                description="Apri un ticket per candidarti staff",
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

        if not isinstance(user, discord.Member):
            await interaction.response.send_message(
                "❌ Errore: utente non valido.",
                ephemeral=True
            )
            return

        category_channel = guild.get_channel(TICKETS_CATEGORY_ID)
        if category_channel is None:
            await interaction.response.send_message(
                "❌ Errore: la categoria ticket non è stata trovata. Controlla l'ID.",
                ephemeral=True
            )
            return

        selected_category = self.values[0]
        ticket_channel_name = make_safe_channel_name(selected_category, user.name)

        for existing_channel in guild.text_channels:
            if existing_channel.name == ticket_channel_name:
                await interaction.response.send_message(
                    f"❌ Hai già un ticket aperto: {existing_channel.mention}",
                    ephemeral=True
                )
                return

        bot_member = guild.get_member(bot.user.id) if bot.user else None
        if bot_member is None:
            await interaction.response.send_message(
                "❌ Errore: il bot non è stato trovato nel server.",
                ephemeral=True
            )
            return

        staff_role = guild.get_role(STAFF_ROLE_ID)
        partnership_role = guild.get_role(PARTNERSHIP_ROLE_ID)
        co_owner_role = guild.get_role(CO_OWNER_ROLE_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
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
                attach_files=True,
                embed_links=True
            )
        }

        if staff_role is not None:
            overwrites[staff_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            )

        if co_owner_role is not None:
            overwrites[co_owner_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            )

        if selected_category == "partnership" and partnership_role is not None:
            overwrites[partnership_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            )

        topic_text = get_ticket_topic(user.id, selected_category, user.name)

        try:
            created_channel = await guild.create_text_channel(
                name=ticket_channel_name,
                category=category_channel,
                overwrites=overwrites,
                topic=topic_text,
                reason=f"Ticket {selected_category} aperto da {user}"
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Non posso creare il ticket: mi manca il permesso **Gestisci Canali** oppure il mio ruolo è troppo basso.",
                ephemeral=True
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                "❌ Discord ha dato errore mentre creavo il ticket.",
                ephemeral=True
            )
            return

        if selected_category == "assistenza":
            ticket_description = (
                f"Ciao {user.mention}, benvenuto nel tuo ticket di **assistenza** su **{SERVER_NAME}**.\n\n"
                "Spiega qui sotto il tuo problema nel modo più chiaro possibile.\n\n"
                "**Ti consigliamo di scrivere:**\n"
                "• cosa è successo\n"
                "• quando è successo\n"
                "• eventuali screen o prove\n"
                "• se il problema riguarda bot, canali o utenti\n\n"
                "Lo staff risponderà appena possibile."
            )
        elif selected_category == "partnership":
            ticket_description = (
                f"Ciao {user.mention}, benvenuto nel tuo ticket di **partnership** su **{SERVER_NAME}**.\n\n"
                "Scrivi qui la tua proposta di collaborazione.\n\n"
                "**Puoi includere:**\n"
                "• nome del server/progetto\n"
                "• numero membri\n"
                "• tipo di partnership\n"
                "• eventuali link utili\n\n"
                "Il gestore partnership o lo staff controlleranno appena possibile."
            )
        elif selected_category == "segnalazione":
            ticket_description = (
                f"Ciao {user.mention}, benvenuto nel tuo ticket di **segnalazione** su **{SERVER_NAME}**.\n\n"
                "Scrivi bene cosa vuoi segnalare.\n\n"
                "**Ti consigliamo di includere:**\n"
                "• utente coinvolto\n"
                "• cosa è successo\n"
                "• prove o screenshot\n"
                "• contesto della situazione\n\n"
                "Lo staff valuterà tutto con attenzione."
            )
        else:
            ticket_description = (
                f"Ciao {user.mention}, benvenuto nel tuo ticket di **candidatura staff** su **{SERVER_NAME}**.\n\n"
                "Compila con calma queste domande:\n\n"
                "**Domande candidatura:**\n"
                "1. Quanti anni hai?\n"
                "2. Da quanto tempo usi Discord?\n"
                "3. Hai già avuto esperienze come staff?\n"
                "4. Perché vuoi diventare staff di JustChill?\n"
                "5. Quanto sei attivo al giorno?\n"
                "6. Quali qualità pensi di avere per questo ruolo?\n\n"
                "Rispondi bene a tutto e aspetta la valutazione dello staff."
            )

        open_ticket_embed = discord.Embed(
            title=f"🎫 Ticket {SERVER_NAME}",
            description=ticket_description,
            color=discord.Color.green()
        )
        open_ticket_embed.set_footer(text=f"{SERVER_NAME} • Sistema Ticket")

        mentions = [user.mention]

        if co_owner_role is not None:
            mentions.append(co_owner_role.mention)

        if selected_category == "partnership" and partnership_role is not None:
            mentions.append(partnership_role.mention)
        elif staff_role is not None:
            mentions.append(staff_role.mention)

        await created_channel.send(
            content=" ".join(mentions),
            embed=open_ticket_embed,
            view=CloseTicketView()
        )

        dm_open_embed = discord.Embed(
            title=f"📂 Ticket aperto • {SERVER_NAME}",
            description=(
                f"Hai aperto un ticket nel server **{SERVER_NAME}**.\n\n"
                f"**Canale:** `{created_channel.name}`\n"
                f"**Categoria:** `{selected_category}`\n\n"
                "Conserva questo messaggio come log privato del tuo ticket."
            ),
            color=discord.Color.blurple()
        )
        dm_open_embed.set_footer(text=f"{SERVER_NAME} • Ticket Logs Privati")

        await send_dm_safe(user, dm_open_embed)

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
        category_embed = discord.Embed(
            title=f"🎫 Apri un ticket • {SERVER_NAME}",
            description=(
                f"Benvenuto nel pannello ticket di **{SERVER_NAME}**.\n\n"
                "Seleziona dal menu qui sotto la categoria più adatta alla tua richiesta."
            ),
            color=discord.Color.blurple()
        )
        category_embed.set_footer(text=f"{SERVER_NAME} • Selezione Categoria")

        await interaction.response.send_message(
            embed=category_embed,
            view=TicketCategoryView(),
            ephemeral=True
        )


# =========================
# AVVIO STABILE VIEWS
# =========================
async def setup_views():
    bot.add_view(OpenTicketView())
    bot.add_view(CloseTicketView())
    bot.add_view(TicketCategoryView())

@bot.event
async def setup_hook():
    await setup_views()


@bot.event
async def on_ready():
    print(f"Bot ticket online come {bot.user} nel server {SERVER_NAME}")


# =========================
# COMANDO PANNELLO TICKET
# =========================
@bot.command()
@commands.has_any_role(STAFF_ROLE_ID, CO_OWNER_ROLE_ID)
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
@commands.has_any_role(STAFF_ROLE_ID, CO_OWNER_ROLE_ID)
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
            "Hai dimostrato interesse, impegno e buone qualità.\n\n"
            "A breve riceverai maggiori informazioni sui prossimi passaggi.\n"
            "Ti chiediamo di essere attivo, serio, rispettoso e disponibile con tutti.\n\n"
            f"**Benvenuto nel team di {SERVER_NAME} 💙**"
        ),
        color=discord.Color.green()
    )
    accepted_embed.set_footer(text=f"{SERVER_NAME} • Sistema Candidature")

    await ctx.send(embed=accepted_embed)

    dm_accept_embed = discord.Embed(
        title=f"✅ Candidatura accettata • {SERVER_NAME}",
        description=(
            f"La tua candidatura come **Staffer** nel server **{SERVER_NAME}** è stata accettata.\n\n"
            "Complimenti e benvenuto nel team 💙"
        ),
        color=discord.Color.green()
    )
    dm_accept_embed.set_footer(text=f"{SERVER_NAME} • Candidature")

    await send_dm_safe(membro, dm_accept_embed)


# =========================
# COMANDO CANDIDATURA RIFIUTATA
# =========================
@bot.command()
@commands.has_any_role(STAFF_ROLE_ID, CO_OWNER_ROLE_ID)
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
            "Questo però non significa che tu non possa riprovare in futuro.\n"
            "Continua a essere attivo nel server, comportati bene e migliora dove serve.\n\n"
            "Ti ringraziamo comunque per il tempo che hai dedicato alla candidatura 💙"
        ),
        color=discord.Color.red()
    )
    refused_embed.set_footer(text=f"{SERVER_NAME} • Sistema Candidature")

    await ctx.send(embed=refused_embed)

    dm_refused_embed = discord.Embed(
        title=f"❌ Candidatura non accettata • {SERVER_NAME}",
        description=(
            f"La tua candidatura come **Staffer** su **{SERVER_NAME}** non è stata accettata al momento.\n\n"
            "Potrai riprovare più avanti."
        ),
        color=discord.Color.red()
    )
    dm_refused_embed.set_footer(text=f"{SERVER_NAME} • Candidature")

    await send_dm_safe(membro, dm_refused_embed)


# =========================
# ERROR HANDLER
# =========================
@ticket.error
@candidaturasi.error
@candidaturano.error
async def role_error(ctx, error):
    if isinstance(error, commands.MissingAnyRole):
        await ctx.send("❌ Non hai il ruolo giusto per usare questo comando.")
    else:
        await ctx.send(f"❌ Errore: {error}")


# =========================
# AVVIO BOT
# =========================
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    print("ERRORE: variabile TOKEN non trovata.")
else:
    bot.run(TOKEN)