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
STAFF_ROLE_ID = 1491874337769132074  # Staffer
PARTNERSHIP_ROLE_ID = 1491874337769132073  # Gestore partnership

# =========================
# ID CATEGORIA TICKETS
# =========================
TICKETS_CATEGORY_ID = 1491904885988397198

# =========================
# SELECT MENU CATEGORIE
# =========================
class TicketCategorySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Assistenza",
                description="Apri un ticket per ricevere aiuto",
                emoji="🛠️",
                value="assistenza"
            ),
            discord.SelectOption(
                label="Partnership",
                description="Apri un ticket per partnership",
                emoji="🤝",
                value="partnership"
            ),
            discord.SelectOption(
                label="Segnalazione",
                description="Apri un ticket per segnalare qualcosa",
                emoji="🚨",
                value="segnalazione"
            ),
            discord.SelectOption(
                label="Candidatura Staff",
                description="Apri un ticket per candidarti staff",
                emoji="📋",
                value="candidatura_staff"
            ),
        ]

        super().__init__(
            placeholder="Scegli la categoria del ticket...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        category = guild.get_channel(TICKETS_CATEGORY_ID)

        if category is None:
            await interaction.response.send_message(
                "❌ Categoria ticket non trovata. Controlla l'ID.",
                ephemeral=True
            )
            return

        selected = self.values[0]

        if selected == "assistenza":
            channel_name = f"assistenza-{user.name}".lower().replace(" ", "-")
        elif selected == "partnership":
            channel_name = f"partnership-{user.name}".lower().replace(" ", "-")
        elif selected == "segnalazione":
            channel_name = f"segnalazione-{user.name}".lower().replace(" ", "-")
        elif selected == "candidatura_staff":
            channel_name = f"candidatura-{user.name}".lower().replace(" ", "-")
        else:
            channel_name = f"ticket-{user.name}".lower().replace(" ", "-")

        for channel in guild.text_channels:
            if channel.name == channel_name:
                await interaction.response.send_message(
                    f"❌ Hai già un ticket aperto: {channel.mention}",
                    ephemeral=True
                )
                return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                read_message_history=True
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
            description = (
                f"Ciao {user.mention}, benvenuto nel tuo ticket di **assistenza**.\n\n"
                "Spiega bene il problema e aspetta una risposta dallo staff."
            )
        elif selected == "partnership":
            description = (
                f"Ciao {user.mention}, benvenuto nel tuo ticket di **partnership**.\n\n"
                "Scrivi qui la tua proposta di partnership."
            )
        elif selected == "segnalazione":
            description = (
                f"Ciao {user.mention}, benvenuto nel tuo ticket di **segnalazione**.\n\n"
                "Spiega bene cosa vuoi segnalare."
            )
        elif selected == "candidatura_staff":
            description = (
                f"Ciao {user.mention}, benvenuto nel tuo ticket di **candidatura staff**.\n\n"
                "**Compila queste domande:**\n"
                "1. Quanti anni hai?\n"
                "2. Da quanto usi Discord?\n"
                "3. Hai già avuto esperienza come staff?\n"
                "4. Perché vuoi diventare staff?\n"
                "5. Quanto sei attivo al giorno?\n"
            )
        else:
            description = f"Ciao {user.mention}, benvenuto nel tuo ticket."

        embed = discord.Embed(
            title="🎫 Ticket creato",
            description=description,
            color=discord.Color.green()
        )

        view = CloseTicketView()

        if selected == "partnership" and partnership_role:
            await channel.send(
                content=f"{user.mention} {partnership_role.mention}",
                embed=embed,
                view=view
            )
        elif staff_role:
            await channel.send(
                content=f"{user.mention} {staff_role.mention}",
                embed=embed,
                view=view
            )
        else:
            await channel.send(
                content=f"{user.mention}",
                embed=embed,
                view=view
            )

        await interaction.response.send_message(
            f"✅ Ticket creato: {channel.mention}",
            ephemeral=True
        )


class TicketCategoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCategorySelect())


# =========================
# BOTTONE APRI TICKET
# =========================
class OpenTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Apri Ticket", style=discord.ButtonStyle.green, emoji="🎫", custom_id="open_ticket_button")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="Scegli una categoria",
            description="Seleziona dal menu qui sotto la categoria del tuo ticket.",
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(
            embed=embed,
            view=TicketCategoryView(),
            ephemeral=True
        )


# =========================
# BOTTONE CHIUDI TICKET
# =========================
class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Chiudi", style=discord.ButtonStyle.red, emoji="🔒", custom_id="close_ticket_button")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        staff_role = interaction.guild.get_role(STAFF_ROLE_ID)

        if staff_role not in interaction.user.roles:
            await interaction.response.send_message(
                "❌ Solo lo staff può chiudere il ticket.",
                ephemeral=True
            )
            return

        await interaction.response.send_message("🔒 Ticket chiuso...")
        await interaction.channel.delete()


# =========================
# READY
# =========================
@bot.event
async def on_ready():
    bot.add_view(OpenTicketView())
    bot.add_view(CloseTicketView())
    print(f"Bot online come {bot.user}")


# =========================
# COMANDO PANNELLO
# =========================
@bot.command()
@commands.has_permissions(administrator=True)
async def panel(ctx):
    embed = discord.Embed(
        title="🎫 Supporto Tickets",
        description=(
            "Clicca il bottone qui sotto per aprire un ticket.\n\n"
            "**Categorie disponibili:**\n"
            "🛠️ Assistenza\n"
            "🤝 Partnership\n"
            "🚨 Segnalazione\n"
            "📋 Candidatura Staff"
        ),
        color=discord.Color.blurple()
    )

    await ctx.send(embed=embed, view=OpenTicketView())


bot.run(os.getenv("TOKEN"))