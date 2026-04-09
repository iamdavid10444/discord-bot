import os
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# ID RUOLI / CATEGORIA
# =========================
OWNER_ROLE_ID = 1491874337769132076
ADMIN_ROLE_ID = 1491874337769132075
STAFF_ROLE_ID = 1491874337769132074
PARTNERSHIP_ROLE_ID = 1491874337769132073

TICKETS_CATEGORY_ID = 1491904885988397198


def safe_name(text: str) -> str:
    text = text.lower().replace(" ", "-")
    allowed = "abcdefghijklmnopqrstuvwxyz0123456789-_"
    return "".join(c for c in text if c in allowed)


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
        allowed_roles = {
            OWNER_ROLE_ID,
            ADMIN_ROLE_ID,
            STAFF_ROLE_ID,
            PARTNERSHIP_ROLE_ID
        }

        user_role_ids = {role.id for role in interaction.user.roles}

        if not user_role_ids.intersection(allowed_roles):
            await interaction.response.send_message(
                "❌ Non puoi chiudere questo ticket.",
                ephemeral=True
            )
            return

        await interaction.response.send_message("🔒 Ticket chiuso...")
        await interaction.channel.delete()


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
            options=options,
            custom_id="ticket_category_select"
        )

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user

        if guild is None:
            await interaction.response.send_message("❌ Errore: server non trovato.", ephemeral=True)
            return

        category = guild.get_channel(TICKETS_CATEGORY_ID)
        if category is None:
            await interaction.response.send_message(
                "❌ Categoria ticket non trovata. Controlla l'ID.",
                ephemeral=True
            )
            return

        selected = self.values[0]
        clean_user = safe_name(user.name)

        if selected == "assistenza":
            channel_name = f"assistenza-{clean_user}"
        elif selected == "partnership":
            channel_name = f"partnership-{clean_user}"
        elif selected == "segnalazione":
            channel_name = f"segnalazione-{clean_user}"
        else:
            channel_name = f"candidatura-{clean_user}"

        existing = discord.utils.get(guild.text_channels, name=channel_name)
        if existing:
            await interaction.response.send_message(
                f"❌ Hai già un ticket aperto: {existing.mention}",
                ephemeral=True
            )
            return

        bot_member = guild.get_member(bot.user.id)
        if bot_member is None:
            await interaction.response.send_message(
                "❌ Non riesco a trovare il bot nel server.",
                ephemeral=True
            )
            return

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
        owner_role = guild.get_role(OWNER_ROLE_ID)
        admin_role = guild.get_role(ADMIN_ROLE_ID)
        partnership_role = guild.get_role(PARTNERSHIP_ROLE_ID)

        if owner_role:
            overwrites[owner_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )

        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )

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
                "Spiega bene il problema e aspetta una risposta dallo staff."
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
        else:
            if staff_role:
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


class TicketCategoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCategorySelect())


class OpenTicketView(discord.ui.View):
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
            title="Scegli una categoria",
            description="Seleziona dal menu qui sotto la categoria del tuo ticket.",
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(
            embed=embed,
            view=TicketCategoryView(),
            ephemeral=True
        )


@bot.event
async def on_ready():
    bot.add_view(OpenTicketView())
    bot.add_view(CloseTicketView())
    bot.add_view(TicketCategoryView())
    print(f"Bot online come {bot.user}")


@bot.command()
async def ticket(ctx):
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