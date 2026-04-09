import os
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# ID
# =========================
STAFF_ROLE_ID = 1491874337769132074
PARTNERSHIP_ROLE_ID = 1491874337769132073
TICKETS_CATEGORY_ID = 1491904885988397198

# =========================
# SELECT MENU
# =========================
class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Assistenza", emoji="🛠️", value="assistenza"),
            discord.SelectOption(label="Partnership", emoji="🤝", value="partnership"),
            discord.SelectOption(label="Segnalazione", emoji="🚨", value="segnalazione"),
            discord.SelectOption(label="Candidatura Staff", emoji="📋", value="staff"),
        ]
        super().__init__(placeholder="Scegli categoria...", options=options)

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        category = guild.get_channel(TICKETS_CATEGORY_ID)

        if not category:
            return await interaction.response.send_message("Errore categoria", ephemeral=True)

        name = f"{self.values[0]}-{user.name}".lower()

        # evita doppio ticket
        for ch in guild.channels:
            if ch.name == name:
                return await interaction.response.send_message("Hai già un ticket!", ephemeral=True)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True)
        }

        staff = guild.get_role(STAFF_ROLE_ID)
        if staff:
            overwrites[staff] = discord.PermissionOverwrite(view_channel=True)

        if self.values[0] == "partnership":
            part = guild.get_role(PARTNERSHIP_ROLE_ID)
            if part:
                overwrites[part] = discord.PermissionOverwrite(view_channel=True)

        channel = await guild.create_text_channel(name=name, category=category, overwrites=overwrites)

        embed = discord.Embed(
            title="🎫 Ticket",
            description=f"{user.mention} spiega il problema.\nCategoria: **{self.values[0]}**",
            color=discord.Color.green()
        )

        await channel.send(content=f"{user.mention}", embed=embed, view=CloseView())

        await interaction.response.send_message(f"Ticket creato: {channel.mention}", ephemeral=True)


class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


# =========================
# BOTTONE APRI
# =========================
class OpenView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Apri Ticket", style=discord.ButtonStyle.green, emoji="🎫")
    async def open(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Scegli categoria:", view=TicketView(), ephemeral=True)


# =========================
# CHIUDI
# =========================
class CloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Chiudi", style=discord.ButtonStyle.red, emoji="🔒")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        staff = interaction.guild.get_role(STAFF_ROLE_ID)

        if staff not in interaction.user.roles:
            return await interaction.response.send_message("Solo staff!", ephemeral=True)

        await interaction.response.send_message("Chiudo...")
        await interaction.channel.delete()


# =========================
# READY
# =========================
@bot.event
async def on_ready():
    bot.add_view(OpenView())
    bot.add_view(CloseView())
    print(f"Bot online {bot.user}")


# =========================
# COMANDO
# =========================
@bot.command()
async def ticket(ctx):
    embed = discord.Embed(
        title="🎫 Ticket Supporto",
        description="Premi il bottone per aprire un ticket.",
        color=discord.Color.blurple()
    )

    await ctx.send(embed=embed, view=OpenView())


bot.run(os.getenv("TOKEN"))