import discord
from discord.ext import commands
from discord.ui import Select, View

class ExampleDropdown(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Option 1", description="Description 1"),
            discord.SelectOption(label="Option 2", description="Description 2")
        ]
        super().__init__(
            placeholder="Choose an option...",
            options=options,
            custom_id="example_dropdown"  # Required for persistence
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"You chose {self.values[0]}", ephemeral=True
        )

class DropdownView(View):
    def __init__(self):
        super().__init__(timeout=None)  # Required for persistence
        self.add_item(ExampleDropdown())

class DropdownCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(DropdownView())  # Register persistent view on startup

async def setup(bot):
    await bot.add_cog(DropdownCog(bot))
