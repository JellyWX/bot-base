from server_data import ServerData
import discord
import sys
import os
import msgpack
import zlib

class BotClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super(BotClient, self).__init__(*args, **kwargs)
        self.get_server = lambda x: [d for d in self.data if d.id == x.id][0]

        self.data = []

        self.commands = {
            'ping' : self.ping,
            'help' : self.help,
            'info': self.info,
            'prefix' : self.change_prefix
        }

        try:
            with open('data.mp', 'rb') as f:
                for d in msgpack.unpackb(zlib.decompress(f.read()), encoding='utf8'):
                    self.data.append(ServerData(**d))
        except FileNotFoundError:
            pass

        try:
            open('strings', 'r').close()
        except FileNotFoundError:
            print('Strings file not present. Exiting...')
            sys.exit()


    async def on_ready(self):
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------------')
        await client.change_presence(activity=discord.Game(name='r!help'))


    async def on_guild_join(self, guild):
        self.data.append(ServerData(**{
            'id' : guild.id,
            'prefix' : '!'
            }
        ))


    async def on_guild_remove(self, guild):
        self.data = [d for d in self.data if d.id != guild.id]


    async def on_message(self, message):

        if isinstance(message.channel, discord.DMChannel) or message.author.bot or message.content == None:
            return

        if len([d for d in self.data if d.id == message.guild.id]) == 0:
            self.data.append(ServerData(**{
                'id' : message.guild.id,
                'prefix' : '!'
                }
            ))

        else:
            server = self.get_server(message.guild)

            queue_deletes = []
            for user in server.referral_links.keys():
                if message.guild.get_member(user) is None:
                    queue_deletes.append(user)

            for user in queue_deletes:
                del server.referral_users[user]
                del server.referral_links[user]
                del server.logged_referrals[user]

            queue_deletes = []
            for user, data in server.referral_users.items():
                for joiner in data:
                    if message.guild.get_member(joiner) is None:
                        queue_deletes.append((user, joiner))

            for user, person in queue_deletes:
                server.referral_users[user].remove(person)

        invites = await message.guild.invites()

        for invite in invites:
            if invite.inviter == self.user and invite.id not in server.referral_links.values():
                await invite.delete()

        with open('strings', 'r') as f:
            self.strings = f.read().split('[split]')

        if await self.get_cmd(message):
            with open('data.mp', 'wb') as f:
                f.write(zlib.compress(msgpack.packb([d.__dict__ for d in self.data])))


    async def get_cmd(self, message):

        server = self.get_server(message.guild)
        prefix = server.prefix

        if message.content[0:len(prefix)] == prefix:
            command = (message.content + ' ')[len(prefix):message.content.find(' ')]
            if command in self.commands:
                stripped = (message.content + ' ')[message.content.find(' '):].strip()
                await self.commands[command](message, stripped)
                return True

        elif self.user.id in map(lambda x: x.id, message.mentions) and len(message.content.split(' ')) > 1:
            if message.content.split(' ')[1] in self.commands.keys():
                stripped = (message.content + ' ').split(' ', 2)[-1].strip()
                await self.commands[message.content.split(' ')[1]](message, stripped)
                return True

        return False


    async def change_prefix(self, message, stripped):
        server = self.get_server(message.guild)

        if stripped:
            stripped += ' '
            server.prefix = stripped[:stripped.find(' ')]
            await message.channel.send('Prefix changed to {}'.format(server.prefix))

        else:
            await message.channel.send('Please use this command as `{}prefix <prefix>`'.format(server.prefix))


    async def ping(self, message, stripped):
        t = message.created_at.timestamp()
        e = await message.channel.send('pong')
        delta = e.created_at.timestamp() - t

        await e.edit(content='Pong! {}ms round trip'.format(round(delta * 1000)))


    async def help(self, message, stripped):
        embed = discord.Embed(description=self.strings[1])
        await message.channel.send(embed=embed)


    async def info(self, message, stripped):
        embed = discord.Embed(description=self.strings[0])
        await message.channel.send(embed=embed)


try: ## token grabbing code
    with open('token','r') as token_f:
        token = token_f.read().strip('\n')

except:
    print('no token provided')
    sys.exit(-1)

client = BotClient()
client.run(token)
