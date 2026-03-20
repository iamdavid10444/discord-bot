import os
import discord
from discord.ext import commands
from discord.ui import View, Button

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

CATEGORY_NAME = "TICKETS"
STAFF_ROLE_ID = 1422587221600501780


def is_staff(member: discord.Member) -> bool:
    return (
        member.guild.owner_id == member.id
        or member.guild_permissions.administrator
        or any(role.id == STAFF_ROLE_ID for role in member.roles)
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
        self.claimed_by_id = None

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
            roles_text = ", ".join([f"{r.name} ({r.id})" for r in user.roles])
            await interaction.response.send_message(
                f"❌ Il bot non ti vede come staff.\n"
                f"Owner server: {guild.owner_id == user.id}\n"
                f"Admin: {user.guild_permissions.administrator}\n"
                f"Ruolo staff trovato: {any(role.id == STAFF_ROLE_ID for role in user.roles)}\n"
                f"STAFF_ROLE_ID attuale: {STAFF_ROLE_ID}\n"
                f"I tuoi ruoli: {roles_text}",
                ephemeral=True
            )
            return

        if self.claimed_by_id is not None:
            await interaction.response.send_message(
                "❌ Questo ticket è già stato reclamato.",
                ephemeral=True
            )
            return

        staff_role = guild.get_role(STAFF_ROLE_ID)
        if staff_role is None:
            await interaction.response.send_message(
                "❌ Non trovo il ruolo staff.",
                ephemeral=True
            )
            return

        ticket_owner = guild.get_member(self.ticket_owner_id)
        if ticket_owner is None:
            try:
                ticket_owner = await guild.fetch_member(self.ticket_owner_id)
            except discord.NotFound:
                await interaction.response.send_message(
                    "❌ Non trovo più l'utente che ha aperto il ticket.",
                    ephemeral=True
                )
                return
            except discord.Forbidden:
                await interaction.response.send_message(
                    "❌ Non ho i permessi per recuperare l'utente del ticket.",
                    ephemeral=True
                )
                return
            except Exception as e:
                await interaction.response.send_message(
                    f"❌ Errore nel recupero utente: {e}",
                    ephemeral=True
                )
                return

        self.claimed_by_id = user.id

        # tutto lo staff vede ma non scrive più
        await channel.set_permissions(
            staff_role,
            view_channel=True,
            send_messages=False,
            read_message_history=True
        )

        # chi reclama può scrivere
        await channel.set_permissions(
            user,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_messages=True
        )

        # owner ticket continua a scrivere
        await channel.set_permissions(
            ticket_owner,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True
        )

        self.clear_items()
        self.add_item(ClaimedButton(user.display_name))
        self.add_item(CloseTicketButton(self.ticket_owner_id, self.claimed_by_id))

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
        custom_id="close_ticket_button_initial"
    )
    async def close_ticket_initial(self, interaction: discord.Interaction, button: Button):
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


class ClaimedButton(Button):
    def __init__(self, claimer_name: str):
        super().__init__(
            label=f"📌 Reclamato da {claimer_name}",
            style=discord.ButtonStyle.blurple,
            disabled=True,
            custom_id="claimed_ticket_button"
        )


class CloseTicketButton(Button):
    def __init__(self, ticket_owner_id: int, claimed_by_id: int | None):
        super().__init__(
            label="🔒 Chiudi Ticket",
            style=discord.ButtonStyle.red,
            custom_id="close_ticket_button_after_claim"
        )
        self.ticket_owner_id = ticket_owner_id
        self.claimed_by_id = claimed_by_id

    async def callback(self, interaction: discord.Interaction):
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

        if (
            self.claimed_by_id is not None
            and user.id != self.claimed_by_id
            and guild.owner_id != user.id
            and not user.guild_permissions.administrator
        ):
            await interaction.response.send_message(
                "❌ Solo chi ha reclamato il ticket può chiuderlo.",
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
async def debugstaff(ctx):
    roles_text = ", ".join([f"{r.name} ({r.id})" for r in ctx.author.roles])
    await ctx.send(
        f"Owner server: {ctx.guild.owner_id == ctx.author.id}\n"
        f"Admin: {ctx.author.guild_permissions.administrator}\n"
        f"Ruolo staff trovato: {any(role.id == STAFF_ROLE_ID for role in ctx.author.roles)}\n"
        f"STAFF_ROLE_ID attuale: {STAFF_ROLE_ID}\n"
        f"I tuoi ruoli: {roles_text}"
    )


@bot.event
async def on_ready():
    bot.add_view(TicketPanelView())
    print(f"Bot online come {bot.user}")


bot.run(os.getenv("TOKEN"))