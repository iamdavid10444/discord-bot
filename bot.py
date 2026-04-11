import os
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

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
# VIEW CHIUSURA TICKET
# =========================
class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Chiudi",
        style=discord.ButtonStyle.red,
        emoji="🔒",
        custom_id="close_ticket_button"
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        staff_role = interaction.guild.get_role(STAFF_ROLE_ID)

        if staff_role is None or staff_role not in interaction.user.roles:
            await interaction.response.send_message(
                "❌ Solo lo staff può chiudere il ticket.",
                ephemeral=True
            )
            return

        await interaction.response.send_message("🔒 Ticket chiuso...")
        await interaction.channel.delete()


# =========================
# SELECT CATEGORIE
# =========================
class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Assistenza",
                emoji="🛠️",
                value="assistenza",
                description="Apri un ticket di assistenza"
            ),
            discord.SelectOption(
                label="Partnership",
                emoji="🤝",
                value="partnership",
                description="Apri un ticket per partnership"
            ),
            discord.SelectOption(
                label="Segnalazione",
                emoji="🚨",
                value="segnalazione",
                description="Apri un ticket di segnalazione"
            ),
            discord.SelectOption(
                label="Candidatura Staff",
                emoji="📋",
                value="staff",
                description="Apri un ticket per candidatura staff"
            ),
        ]

        super().__init__(
            placeholder="Scegli categoria...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="ticket_select_menu"
        )

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        category = guild.get_channel(TICKETS_CATEGORY_ID)

        if category is None:
            await interaction.response.send_message(
                "❌ Categoria ticket non trovata.",
                ephemeral=True
            )
            return

        selected = self.values[0]
        channel_name = f"{selected}-{user.name}".lower().replace(" ", "-")

        for ch in guild.text_channels:
            if ch.name == channel_name:
                await interaction.response.send_message(
                    f"❌ Hai già un ticket aperto: {ch.mention}",
                    ephemeral=True
                )
                return

        bot_member = guild.me

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True
            ),
            bot_member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
                manage_messages=True
            )
        }

        staff_role = guild.get_role(STAFF_ROLE_ID)
        partnership_role = guild.get_role(PARTNERSHIP_ROLE_ID)

        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )

        if selected == "partnership" and partnership_role:
            overwrites[partnership_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )

        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites
        )

        if selected == "assistenza":
            desc = (
                f"Ciao {user.mention}, benvenuto nel tuo ticket di **assistenza**.\n\n"
                "Spiega bene il tuo problema e aspetta una risposta dallo staff."
            )
        elif selected == "partnership":
            desc = (
                f"Ciao {user.mention}, benvenuto nel tuo ticket di **partnership**.\n\n"
                "Scrivi qui la tua proposta di partnership."
            )
        elif selected == "segnalazione":
            desc = (
                f"Ciao {user.mention}, benvenuto nel tuo ticket di **segnalazione**.\n\n"
                "Spiega bene cosa vuoi segnalare."
            )
        else:
            desc = (
                f"Ciao {user.mention}, benvenuto nel tuo ticket di **candidatura staff**.\n\n"
                "**Compila queste domande:**\n"
                "1. Quanti anni hai?\n"
                "2. Da quanto usi Discord?\n"
                "3. Hai già avuto esperienza come staff?\n"
                "4. Perché vuoi diventare staff?\n"
                "5. Quanto sei attivo al giorno?\n"
            )

        embed = discord.Embed(
            title="🎫 Ticket creato",
            description=desc,
            color=discord.Color.green()
        )

        mentions = [user.mention]

        if selected == "partnership" and partnership_role:
            mentions.append(partnership_role.mention)
        elif staff_role:
            mentions.append(staff_role.mention)

        await channel.send(
            content=" ".join(mentions),
            embed=embed,
            view=CloseTicketView()
        )

        await interaction.response.send_message(
            f"✅ Ticket creato: {channel.mention}",
            ephemeral=True
        )


class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


# =========================
# BOTTONE APRI TICKET
# =========================
class OpenView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Apri Ticket",
        style=discord.ButtonStyle.green,
        emoji="🎫",
        custom_id="open_ticket_button"
    )
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🎫 Apri un ticket",
            description="Scegli la categoria dal menu qui sotto.",
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(
            embed=embed,
            view=TicketView(),
            ephemeral=True
        )


# =========================
# READY
# =========================
@bot.event
async def on_ready():
    bot.add_view(OpenView())
    bot.add_view(CloseTicketView())
    bot.add_view(TicketView())
    print(f"Bot online come {bot.user}")


# =========================
# COMANDO PANNELLO TICKET
# =========================
@bot.command()
async def ticket(ctx):
    embed = discord.Embed(
        title="🎫 Ticket Supporto",
        description=(
            "Premi il bottone qui sotto per aprire un ticket.\n\n"
            "**Categorie disponibili:**\n"
            "🛠️ Assistenza\n"
            "🤝 Partnership\n"
            "🚨 Segnalazione\n"
            "📋 Candidatura Staff"
        ),
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed, view=OpenView())


# =========================
# COMANDO CANDIDATURA SI
# =========================
@bot.command()
async def candidaturasi(ctx, membro: discord.Member = None):
    if membro is None:
        await ctx.send("❌ Usa così: `!candidaturasi @utente`")
        return

    embed = discord.Embed(
        title="✅ Candidatura accettata",
        description=(
            f"Ciao {membro.mention},\n\n"
            "**La tua candidatura come Staffer è stata accettata!** 🎉\n\n"
            "Dopo aver letto con attenzione la tua candidatura, abbiamo deciso di accettarti.\n"
            "Le tue risposte ci hanno convinto e pensiamo che tu possa essere adatto a questo ruolo.\n\n"
            "A breve riceverai maggiori informazioni sui prossimi passaggi.\n"
            "Ti chiediamo di rimanere attivo, serio e rispettoso.\n\n"
            "**Benvenuto nel team staff di chillZone 💙**"
        ),
        color=discord.Color.green()
    )
    embed.set_footer(text="chillZone • Sistema candidature")
    await ctx.send(embed=embed)


# =========================
# COMANDO CANDIDATURA NO
# =========================
@bot.command()
async def candidaturano(ctx, membro: discord.Member = None):
    if membro is None:
        await ctx.send("❌ Usa così: `!candidaturano @utente`")
        return

    embed = discord.Embed(
        title="❌ Candidatura non accettata",
        description=(
            f"Ciao {membro.mention},\n\n"
            "grazie per aver inviato la tua candidatura come Staffer.\n\n"
            "Dopo averla valutata con attenzione, abbiamo deciso di **non accettarla al momento**.\n\n"
            "Questo non vuol dire che tu non possa riprovare in futuro.\n"
            "Continua a essere attivo nel server, mantieni un buon comportamento e migliora dove serve.\n\n"
            "Grazie comunque per il tempo che hai dedicato alla candidatura 💙"
        ),
        color=discord.Color.red()
    )
    embed.set_footer(text="chillZone • Sistema candidature")
    await ctx.send(embed=embed)


bot.run(os.getenv("TOKEN"))