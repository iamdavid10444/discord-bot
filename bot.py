import discord
from discord.ext import commands
from discord.ui import View, Button

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

CATEGORY_NAME = "TICKETS"
STAFF_ROLE_ID = 1422587221600501780  # 


def is_staff(member):
    return (
        any(role.id == STAFF_ROLE_ID for role in member.roles)
        or member.guild_permissions.administrator
    )


class TicketPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🎫 Apri Ticket",
        style=discord.ButtonStyle.green,
        custom_id="open_ticket_button"
    )
    async def open_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        user = interaction.user

        if guild is None or not isinstance(user, discord.Member):
            await interaction.response.send_message(
                "Errore: usa il bottone nel server.",
                ephemeral=True
            )
            return

        staff_role = guild.get_role(STAFF_ROLE_ID)
        if staff_role is None:
            await interaction.response.send_message(
                "Non trovo il ruolo staff. Controlla STAFF_ROLE_ID.",
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
                read_message_history=True
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
                f"Lo staff {staff_role.mention} può reclamare questo ticket."
            ),
            color=discord.Color.green()
        )
        embed.set_footer(text="Uno staff può premere 'Reclama Ticket'.")

        await channel.send(
            content=f"{user.mention} {staff_role.mention}",
            embed=embed,
            view=TicketControlView(ticket_owner_id=user.id)
        )

        await interaction.response.send_message(
            f"✅ Ticket creato: {channel.mention}",
            ephemeral=True
        )


class TicketControlView(View):
    def __init__(self, ticket_owner_id: int):
        super().__init__(timeout=None)
        self.ticket_owner_id = ticket_owner_id

    @discord.ui.button(
        label="📌 Reclama Ticket",
        style=discord.ButtonStyle.blurple,
        custom_id="claim_ticket_button"
    )
    async def claim_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        channel = interaction.channel
        user = interaction.user

        if guild is None or channel is None or not isinstance(user, discord.Member):
            await interaction.response.send_message(
                "Errore nel claim del ticket.",
                ephemeral=True
            )
            return

        if not is_staff(user):
            await interaction.response.send_message(
                "❌ Solo lo staff può reclamare il ticket.",
                ephemeral=True
            )
            return

        ticket_owner = guild.get_member(self.ticket_owner_id)
        staff_role = guild.get_role(STAFF_ROLE_ID)

        if ticket_owner is None or staff_role is None:
            await interaction.response.send_message(
                "Errore: ticket owner o ruolo staff non trovato.",
                ephemeral=True
            )
            return

        # Tutto lo staff continua a vedere, ma non può più scrivere
        await channel.set_permissions(
            staff_role,
            view_channel=True,
            send_messages=False,
            read_message_history=True
        )

        # Lo staff che reclama può scrivere
        await channel.set_permissions(
            user,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_messages=True
        )

        # L'owner del ticket continua a scrivere
        await channel.set_permissions(
            ticket_owner,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True
        )

        button.disabled = True
        button.label = f"📌 Reclamato da {user.display_name}"

        await interaction.response.edit_message(view=self)

        embed = discord.Embed(
            title="📌 Ticket Reclamato",
            description=f"Questo ticket è stato reclamato da {user.mention}.",
            color=discord.Color.blurple()
        )
        await channel.send(embed=embed)

    @discord.ui.button(
        label="🔒 Chiudi Ticket",
        style=discord.ButtonStyle.red,
        custom_id="close_ticket_button"
    )
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        channel = interaction.channel
        user = interaction.user

        if guild is None or channel is None or not isinstance(user, discord.Member):
            await interaction.response.send_message(
                "Errore nella chiusura ticket.",
                ephemeral=True
            )
            return

        if not is_staff(user):
            await interaction.response.send_message(
                "❌ Solo lo staff può chiudere il ticket.",
                ephemeral=True
            )
            return

        await interaction.response.send_message("🔒 Chiusura ticket in corso...")
        await channel.delete()


@bot.command()
async def pannello(ctx):
    embed = discord.Embed(
        title="Supporto Ticket",
        description="Premi il bottone qui sotto per aprire un ticket privato con lo staff.",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Un solo ticket aperto per utente.")
    await ctx.send(embed=embed, view=TicketPanelView())


@bot.command()
async def aggiungi(ctx, member: discord.Member):
    if not is_staff(ctx.author):
        await ctx.send("❌ Solo lo staff può usare questo comando.")
        return

    await ctx.channel.set_permissions(
        member,
        view_channel=True,
        send_messages=True,
        read_message_history=True
    )
    await ctx.send(f"✅ {member.mention} aggiunto al ticket.")


@bot.command()
async def rimuovi(ctx, member: discord.Member):
    if not is_staff(ctx.author):
        await ctx.send("❌ Solo lo staff può usare questo comando.")
        return

    await ctx.channel.set_permissions(member, overwrite=None)
    await ctx.send(f"✅ {member.mention} rimosso dal ticket.")


@bot.event
async def on_ready():
    print(f"Bot online come {bot.user}")


import os
bot.run(os.getenv("TOKEN"))