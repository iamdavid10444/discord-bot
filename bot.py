import discord
from discord.ext import commands
from discord.ui import View, Button

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

CATEGORY_NAME = "TICKETS"
STAFF_ROLE_ID = 1422587221600501780  # 


def is_staff_or_owner(member: discord.Member) -> bool:
    if member.guild.owner_id == member.id:
        return True
    return any(role.id == STAFF_ROLE_ID for role in member.roles)


class TicketPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Apri Ticket",
        emoji="🎫",
        style=discord.ButtonStyle.green,
        custom_id="open_ticket_button"
    )
    async def open_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        user = interaction.user

        if guild is None or not isinstance(user, discord.Member):
            await interaction.response.send_message(
                "Errore: questo bottone può essere usato solo nel server.",
                ephemeral=True
            )
            return

        staff_role = guild.get_role(STAFF_ROLE_ID)
        if staff_role is None:
            await interaction.response.send_message(
                "Non trovo il ruolo staff. Controlla l'ID nel codice.",
                ephemeral=True
            )
            return

        category = discord.utils.get(guild.categories, name=CATEGORY_NAME)
        if category is None:
            category = await guild.create_category(CATEGORY_NAME)

        safe_name = user.name.lower().replace(" ", "-")
        channel_name = f"ticket-{safe_name}"

        existing_channel = discord.utils.get(guild.text_channels, name=channel_name)
        if existing_channel:
            await interaction.response.send_message(
                f"Hai già un ticket aperto: {existing_channel.mention}",
                ephemeral=True
            )
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            ),
            staff_role: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
                manage_messages=True
            )
        }

        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="🎫 Ticket Aperto",
            description=(
                f"Ciao {user.mention}, descrivi qui il tuo problema.\n\n"
                f"Lo staff {staff_role.mention} ti risponderà appena possibile."
            ),
            color=discord.Color.green()
        )
        embed.set_footer(text="Usa il bottone qui sotto per chiudere il ticket.")

        await channel.send(
            content=f"{user.mention} {staff_role.mention}",
            embed=embed,
            view=CloseTicketView()
        )

        await interaction.response.send_message(
            f"✅ Ticket creato: {channel.mention}",
            ephemeral=True
        )


class CloseTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Chiudi Ticket",
        emoji="🔒",
        style=discord.ButtonStyle.red,
        custom_id="close_ticket_button"
    )
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        user = interaction.user
        channel = interaction.channel

        if guild is None or channel is None or not isinstance(user, discord.Member):
            await interaction.response.send_message(
                "Errore nel controllo chiusura ticket.",
                ephemeral=True
            )
            return

        if not channel.name.startswith("ticket-"):
            await interaction.response.send_message(
                "Questo bottone si può usare solo nei ticket.",
                ephemeral=True
            )
            return

        if not is_staff_or_owner(user):
            await interaction.response.send_message(
                "❌ Solo staff o owner possono chiudere il ticket.",
                ephemeral=True
            )
            return

        await interaction.response.send_message("🔒 Chiusura ticket in corso...")
        await channel.delete()


@bot.command()
async def pannello(ctx):
    embed = discord.Embed(
        title="Supporto Ticket",
        description=(
            "Hai bisogno di aiuto?\n"
            "Premi il bottone qui sotto per aprire un ticket privato con lo staff."
        ),
        color=discord.Color.blurple()
    )
    embed.set_footer(text="Un solo ticket aperto per utente.")

    await ctx.send(embed=embed, view=TicketPanelView())


@bot.event
async def on_ready():
    bot.add_view(TicketPanelView())
    bot.add_view(CloseTicketView())
    print(f"Bot online come {bot.user}")


import os
bot.run(os.getenv("TOKEN"))