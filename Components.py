import discord
import commands
import InteractionUtils
import UtilityFunctions
import asyncio
import time

class ConfirmButton(discord.ui.Button['ConfirmView']):
    def __init__(self, cat):
        self.cat = cat
        buttonType = discord.ButtonStyle.success if cat=='Yes' else discord.ButtonStyle.danger
        super().__init__(style=buttonType, label=cat, row=1)
    
    async def callback(self, interaction: discord.Interaction):
        self.disabled = True
        for ind, child in enumerate(self.view.children):
            child.disabled = True
            if child.cat != self.cat: 
                self.view.children.pop(ind)
        self.view.stop()

        await interaction.response.edit_message(view=self.view)

        message = InteractionUtils.create_proxy_msg(interaction, ['wp'])
        await commands.TablingCommands.after_start_war_command(message, self.view.bot, [self.cat], self.view.prefix, self.view.lounge)


class ConfirmView(discord.ui.View):
    def __init__(self, bot, prefix, lounge):
        super().__init__()
        self.bot = bot
        self.prefix = prefix
        self.lounge = lounge
        self.add_item(ConfirmButton('Yes'))
        self.add_item(ConfirmButton('No'))
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        allowed = InteractionUtils.commandIsAllowed(self.lounge, interaction.user, self.bot, 'confirm_interaction')
        if not allowed: 
            await interaction.response.send_message("You cannot use these buttons.", ephemeral=True)
        return allowed


###########################################################################################


class PictureButton(discord.ui.Button['PictureView']):
    def __init__(self, bot, timeout):
        super().__init__(style=discord.ButtonStyle.primary, label='Update', row=0)
        self.bot = bot
        # self.button_number = self.bot.pic_button_count + 1
        # self.disabled = self.bot.getWPCooldownSeconds() > 0

        # self.timeout = timeout
        # self.__timeout_task = None
        # self.__timeout_expiry = None

        # self.cooldown = max(self.bot.getWPCooldownSeconds(), 0.5)
        # self.__cooldown_task = None
        # self.__cooldown_expiry = None
        # self.bot.pic_button_count+=1
        # self.start_timeout_timer()
        # self.start_cooldown_timer()
        # self.button_number = self.bot.pic_button_count + 1

        self.disabled = self.bot.getWPCooldownSeconds() > 0

        self.timeout = timeout
        self.__timeout_task = None
        self.__timeout_expiry = None

        self.cooldown = self.bot.getWPCooldownSeconds()
        self.__cooldown_task = None
        self.__cooldown_expiry = None
        self.start_timeout_timer()
        self.start_cooldown_timer()
        
    async def __timeout_task_impl(self) -> None:
        while True:
            if self.__timeout_expiry is None:
                return self._dispatch_timeout()

            # Check if we've elapsed our currently set timeout
            now = time.monotonic()
            if now >= self.__timeout_expiry:
                return self._dispatch_timeout()

            # Wait N seconds to see if timeout data has been refreshed
            await asyncio.sleep(self.__timeout_expiry - now)
    
    def start_timeout_timer(self):
        loop = asyncio.get_running_loop()
        if self.__timeout_task is not None:
            self.__timeout_task.cancel()

        self.__timeout_expiry = time.monotonic() + self.timeout
        self.__timeout_task = loop.create_task(self.__timeout_task_impl())
        
    def _dispatch_timeout(self):
        self.__cooldown_task.cancel()
        asyncio.create_task(self.view.on_timeout(), name=f'pic-button-timeout-{time.monotonic()}')
    
    async def __cooldown_task_impl(self):
        while True:
            if self.__cooldown_expiry is None:
                return
            
            await asyncio.sleep(self.__cooldown_expiry - time.monotonic())

            await self.check_clickable()
            self.cooldown = 0.5
            self.__cooldown_expiry = time.monotonic() + self.cooldown
    
    def start_cooldown_timer(self):
        loop = asyncio.get_running_loop()
        if self.__cooldown_task is not None:
            self.__cooldown_task.cancel()

        self.__cooldown_expiry = time.monotonic() + self.cooldown
        self.__cooldown_task = loop.create_task(self.__cooldown_task_impl())

    async def check_clickable(self):
        if not self.view or not self.view.message: return
        if self.bot.pic_button_count - self.button_number > 2:
            self.view.clear_items()
            self.view.stop()
            await self.view.message.edit(view=self.view)
            self.__cooldown_task.cancel()
            self.__timeout_task.cancel()

        if self.disabled and self.bot.getWPCooldownSeconds() < 1:
            self.disabled = False
        elif not self.disabled and self.bot.getWPCooldownSeconds() > 0:
            self.disabled = True

        await self.view.message.edit(view=self.view)

    async def callback(self, interaction: discord.Interaction):
        msg = InteractionUtils.create_proxy_msg(interaction, ['wp'])

        self.view.message = None
        await interaction.response.edit_message(view=None)
        await commands.TablingCommands.war_picture_command(msg, self.view.bot, ['wp'], self.view.prefix, self.view.lounge,
                                                           requester=interaction.user.display_name)

class PictureView(discord.ui.View):
    def __init__(self, bot, prefix, is_lounge_server, timeout=600):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.prefix = prefix
        self.lounge = is_lounge_server
        self.message = None

        self.add_item(PictureButton(self.bot, timeout))

        self.bot.add_pic_view(self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        allowed = InteractionUtils.commandIsAllowed(self.lounge, interaction.user, self.bot, 'wp_interaction')
        if not allowed:
            await interaction.response.send_message("You cannot use these buttons.", ephemeral=True)
            return False
        
        # cooldown = self.bot.getWPCooldownSeconds()
        # cooldown_active = cooldown > 0
        # if cooldown_active:
        #     await interaction.response.send_message(f"This button is on cooldown. Please wait {cooldown} more seconds.", ephemeral=True)
        #     return False

        return True
    
    async def on_timeout(self) -> None:
        self.clear_items()
        self.stop()
        await self.message.edit(view=self)
        self = None
            
    async def send(self, messageable, content=None, file=None, embed=None):
        if hasattr(messageable, 'channel'):
            messageable = messageable.channel

        self.message = await messageable.send(content=content, file=file, embed=embed, view=self)


###########################################################################################


class RejectButton(discord.ui.Button['SuggestionView']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.danger, label="Discard")
    
    async def callback(self, interaction: discord.Interaction):
        self.view.bot.resolved_errors.add(self.view.index)

        self.view.clear_items() #get rid of all buttons except Picture Button
        await interaction.response.edit_message(view=self.view)

class SuggestionButton(discord.ui.Button['SuggestionView']):
    def __init__(self, error, label, value=None, confirm=False):
        self.error = error #dict of error information
        self.confirm = confirm
        self.value = value
        if not confirm: 
            label = f"R{self.error['race']}: "+label
        super().__init__(style=discord.ButtonStyle.secondary, label=label, disabled=confirm)
    
    async def callback(self, interaction: discord.Interaction):
        server_prefix = self.view.prefix

        args = get_command_args(self.error, self.value if not self.confirm else self.view.selected_values, self.view.bot)
        message = InteractionUtils.create_proxy_msg(interaction, args)

        command_mapping = {
            "blank_player": commands.TablingCommands.disconnections_command,
            "gp_missing": commands.TablingCommands.change_room_size_command,
            "gp_missing_1": commands.TablingCommands.early_dc_command,
            "tie": commands.TablingCommands.quick_edit_command,
            "large_time": commands.TablingCommands.quick_edit_command,
            "missing_player": commands.TablingCommands.disconnections_command
        }
        
        command_mes = await command_mapping[self.error['type']](message, self.view.bot, args, server_prefix, self.view.lounge, dont_send=True)
        author_str = interaction.user.display_name
        self.view.stop()
        self.view.clear_items()
        await interaction.response.edit_message(content=f"{author_str} - "+command_mes, view=self.view)

class SuggestionSelectMenu(discord.ui.Select['SuggestionView']):
    def __init__(self, values, name):
        options = [discord.SelectOption(label=str(value)) for value in values]
        super().__init__(placeholder=name, options=options)
    
    async def callback(self, interaction: discord.Interaction):
        self.view.selected_values(interaction.data['values'][0])
        self.placeholder = self.view.selected_values 

        self.view.enable_confirm()
        try:
            await interaction.response.edit_message(view=self.view)
        except: 
            pass

LABEL_BUILDERS = {
    'missing_player': '{} DCed *{}* race',
    'blank_player': "{} DCed *{}* race",
    'tie': '{} placed *{}*',
    'large_time': '{} {} *{}*', #placed / did not place
    'gp_missing': 'Change Room Size',
    'gp_missing_1': 'Missing player early DCed *{}* race'
}

class SuggestionView(discord.ui.View):
    def __init__(self, error, bot, prefix, lounge, id=None):
        super().__init__(timeout=120)
        self.bot = bot
        self.prefix = prefix
        self.error = error
        self.lounge = lounge
        self.index = id if id else self.error['id']
        self.selected_values = None
        self.message = None
        self.bot.add_sug_view(self)
        # self.bot.cur_sug_num +=1
        # self.current_num = self.bot.cur_sug_num

        self.__delete_task = None
        self.__delete_expiry = None
        self.delete_interval = 0.5

        self.create_row()


    async def on_timeout(self) -> None:
        self.clear_items()
        self.stop()
        await self.message.edit(view=self)
        await self.message.delete()
        self = None
        
    async def __delete_task_impl(self) -> None:
        '''
        Delete old suggestion views when new ones are sent.
        '''
        while True:
            if self.__delete_expiry is None:
                return self._dispatch_del_timeout()
            
            if self.current_num < self.bot.cur_sug_num:
                return self._dispatch_del_timeout()

            # Check if we've elapsed our currently set timeout
            now = time.monotonic()
            self.__delete_expiry = now + self.delete_interval

            # Wait N seconds to see if timeout data has been refreshed
            await asyncio.sleep(self.__delete_expiry - now)
        
    def _dispatch_del_timeout(self):
        self.__delete_task.cancel()
        asyncio.create_task(self.on_timeout(), name=f'sug-view-timeout-{time.monotonic()}')
    
    def start_delete_timer(self):
        loop = asyncio.get_running_loop()
        if self.__delete_task is not None:
            self.__delete_task.cancel()

        self.__delete_expiry = time.monotonic() + self.delete_interval
        self.__delete_task = loop.create_task(self.__delete_task_impl())
    
    async def send(self, messageable, content=None, file=None, embed=None):
        if hasattr(messageable, 'channel'):
            messageable = messageable.channel
        
        # self.start_delete_timer()

        self.message = await messageable.send(content=content, file=file, embed=embed, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        allowed = InteractionUtils.commandIsAllowed(self.lounge, interaction.user, self.bot, InteractionUtils.convert_key_to_command(self.error['type']))
        if not allowed: 
            await interaction.response.send_message("You cannot use these buttons.", ephemeral=True)
        return allowed

    def create_row(self):
        error = self.error
        err_type = error['type']
        label_builder = LABEL_BUILDERS[err_type]

        if 'gp_missing' in err_type:
            if '_1' in err_type:
                label_builder = LABEL_BUILDERS[err_type]
                for insert in ['during', 'before']:
                    label = label_builder.format(insert)
                    self.add_item(SuggestionButton(error, label, value=insert))
            else:
                label = label_builder
                self.add_item(SuggestionSelectMenu(error['corrected_room_sizes'], name=f"R{error['race']}: Select correct room size"))
                self.add_item(SuggestionButton(error, label, confirm=True))
        

        elif err_type in { 'missing_player', 'blank_player' }:
            for insert in ['during', 'before']:
                label = label_builder.format(error['player_name'], insert)
                self.add_item(SuggestionButton(error, label, value=insert))
        
        elif err_type == 'large_time':
            for insert in ["placed"]:
                label = label_builder.format(error['player_name'], insert, UtilityFunctions.place_to_str(error['placement']))
                self.add_item(SuggestionButton(error, label, value=error['placement']))
        
        elif err_type == 'tie':
            for insert in error['placements']:
                label = label_builder.format(error['player_name'], insert)
                self.add_item(SuggestionButton(error, label, value=insert))
        
        self.add_item(RejectButton())
    
    def enable_confirm(self):
        for child in self.children:
            child.disabled=False


def get_command_args(error, info, bot):
    err_type = error['type']

    if err_type == 'gp_missing_1':
        GP = int((error['race']-1)/4) + 1
        time = "on" if info == 'during' else "before"
        args = ['earlydc', str(GP), time]
    
    elif err_type == 'gp_missing':
        race = error['race']
        room_size = str(info)
        args = ['changeroomsize', str(race), room_size]
    
    elif err_type in { 'missing_player', 'blank_player' }:
        playerNum = bot.player_to_dc_num(error['race'], error['player_fc'])

        time = "on" if info == 'during' else "before"
        args = ['dc', str(playerNum), time]
    
    elif err_type == 'large_time':
        playerNum = bot.player_to_num(error['player_fc'])
        placement = str(info)
        race = error['race']
        args = ['changeplace', str(playerNum), str(race), placement]
    
    elif err_type == 'tie':
        playerNum = bot.player_to_num(error['player_fc'])
        race = error['race']
        placement = str(info)
        args = ['changeplace', str(playerNum), str(race), placement]
    
    return args
