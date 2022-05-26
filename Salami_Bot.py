import discord
from discord.ext import tasks, commands
import datetime as dt
import json
import numpy as np # yeah, im a physicist,

# opens a json with the token for obfuscation
with open('config.json') as f:
    data = json.load(f)
    token = data["TOKEN"]

# full intents, because personal server, required for discord.py 2.0
intents = discord.Intents.all()
client = discord.Client(intents=intents)

# dict to keep track of who asks for a reminder, author.id : ReminderCog
user_reminder_cogs_dict = {}

# bean color : emoji id
bean_dict = {
"b" : "978771714576121867",
"c" : "978771675506159668",
"g" : "978771666589073448",
"o" : "978771652924035082",
"p" : "978771687644483655",
"r" : "978771722838900786",
"v" : "978771704643985439",
"y" : "978771696351838208"
}

# offset by 1 to match levels, shows best bean combo first
garden_beans = [
["", "", "", "", ""],
["c", "y", "p", "g", "o"],
["cg", "yr", "py", "gc", "oc"],
["rrr", "yrg", "prr", "coo", "orr"],
["oyyr", "yrco", "coop", "gpyy", "ryoy"],
["crrrr", "yrooo", "vrbvv", "prgbr", "gpbpp"],
["crvvvv", "ybcvbb", "vrrrvv", "oppobp", "rporop"],
["pggggyg", "ygroggg", "cvcbcbb", "bvbvcbb", "rcopvcc"],
["cbyycbyy", "ybvcvrov", "vyyvyovy", "bppbroyy", "rbvvbbpb"]
]

# gag damages for each line in order
gag_damage = [
[12, 20, 35, 50, 85, 180, 200], # trap
[4, 7, 11, 16, 21, 50, 90], # sound
[6, 10, 17, 27, 40, 100, 120], # throw
[4, 8, 12, 21, 30, 80, 105], # squirt
[10, 18, 30, 45, 70, 170, 180] # drop
]

# dict for avg pots to max for each class. runs l to r as life, mana, att, def, spd, dex, vit, wis
pots_to_max_dict = {
    "rogue" : [19, 12, 21, 25, 32, 32, 16, 21],
    "archer" : [19, 12, 35, 25, 19, 19, 19, 21],
    "wizard" : [19, 19, 35, 25, 21, 32, 19, 29],
    "priest" : [19, 19, 19, 25, 15, 24, 21, 32],
    "warrior" : [19, 12, 32, 25, 24, 21, 37, 21],
    "knight" : [19, 12, 7, 40, 24, 21, 37, 21],
    "paladin" : [19, 12, 10, 30, 24, 16, 21, 37],
    "assassin" : [19, 12, 29, 25, 32, 32, 16, 22],
    "necromancer" : [19, 19, 35, 25, 21, 17, 11, 35],
    "huntress" : [19, 12, 35, 25, 19, 19, 19, 21],
    "mystic" : [19, 19, 22, 25, 29, 26, 16, 32],
    "trickster" : [19, 12, 27, 25, 35, 32, 19, 29],
    "sorcerer" : [19, 19, 22, 25, 20, 19, 37, 17],
    "ninja" : [19, 12, 27, 25, 31, 30, 21, 30],
    "samurai" : [19, 12, 35, 30, 26, 21, 20, 20],
    "bard" : [19, 19, 17, 25, 26, 27, 14, 32],
    "summoner" : [19, 19, 12, 25, 29, 32, 21, 32],
    "kensei" : [19, 12, 24, 25, 31, 24, 29, 16]
}

# on init prints name and discord.py version
@client.event
async def on_ready():
    print("We have logged in as {0.user} using {1}".format(client, discord.__version__))

# on message, parses
@client.event
async def on_message(message):

    # does nothing if bots says it
    if message.author == client.user:
        return

    # general help message
    if message.content.startswith("!help"):
        await message.channel.send("Use `!time help` for info about reminders.")
        await message.channel.send("Use `!tunt help` for info about toontown commands.")
        return

    # time specific help message
    if message.content.startswith("!time help"):
        await message.channel.send("Use `!time notify X` to remind you X seconds before the hour.")
        await message.channel.send("Use `!time notify cancel` to cancel the reminder.")
        return

    # toontown specific help message
    if message.content.startswith("!tunt help"):
        await message.channel.send("Use `!tunt garden X` to display the beans needed for level X gardening, with the easiest combination shown first.")
        return

    if message.content.startswith("!rotmg help")
        await message.channel.send("Use `!rotmg roll <class> <life> <mana> <att> <def> <spd> <dex> <vit> <wis>` to see how good your roll is. Input remaining pots to max.")

    # stu id easter egg messages
    if message.content.startswith("!morb"):
        await message.channel.send("It's morbin' time!")
        return

    if message.content.startswith("!nene"):
        await message.channel.send("https://www.youtube.com/watch?v=FdMxDzPIcsw")
        return
    
    # time notify handler
    if message.content.startswith("!time notify"):
        try:
            # try to convert what comes after "!time notify" to an int
            secs = int(message.content[13:])
            # denies invalid input
            if (secs <= 0):
                await message.channel.send("Please input a number of seconds larger than 0.")
                return
        except ValueError:
            # sees if not int means it says cancel
            if (message.content[13:] == "cancel"):
                # sets default dict get response to False if it doesnt have then ask if reminder cog exists
                if user_reminder_cogs_dict.get(message.author.id, False):
                    # unloads the cog if there is one
                    user_reminder_cogs_dict[message.author.id].cog_unload()
                    await message.channel.send("Reminder successfully cancelled.")
                else:
                    await message.channel.send("No reminder currently set.")
            else:
                # if not cancel nor int then nothing valuable put after
                await message.channel.send("Please input a warning time.")
            return
        # if cog exists for the user, set it to the new time, else make a new cog
        if user_reminder_cogs_dict.get(message.author.id, False):
            user_reminder_cogs_dict[message.author.id].set_time(secs)
        else:
            user_reminder_cogs_dict[message.author.id] = ReminderCog(message.author, secs, message.channel, client.user)
        await message.channel.send("I'll ping you {0} seconds before the hour as a reminder.".format(secs % 3600))
        return

    # toontown gardening handler
    if message.content.startswith("!tunt garden"):
        try:
            # try to convert what comes after "!tunt garden" to an int
            level = int(message.content[13:])
            # denies invalid input
            if (level <= 0) or (level >= 9):
                await message.channel.send("Please input a valid gardening level.")
                return
        except ValueError:
            # denies no int input
            await message.channel.send("Please input a gardening level.")
            return
        # makes string for all of them
        for flower in garden_beans[level]:
            bean_text = ""
            # makes each bean into an emoji and adds it to string
            for bean in flower:
                bean_text += "<:{0}bean:{1}>".format(bean, bean_dict[bean])
            await message.channel.send(bean_text)
        return

    #rotmg stat roll handler
    if message.content.startswith("!rotmg roll"):
        try:
            # parse message into data
            params = message.content[12:]
            arr = params.split()
            char_class = arr[0].lower()
            char_stats = arr[1:]
            char_stats = np.asarray(char_stats).astype(int)
            # denies incorrect input
            if(not (char_class in pots_to_max_dict.keys())):
                await message.channel.send("Please input a valid class.")
                return
            if(char_stats.size != 8):
                await message.channel.send("Please enter exactly 8 stats.")
                return
            char_diff = -char_stats+np.asarray(pots_to_max_dict[char_class])
        except ValueError:
            # no input / not integers
            await message.channel.send("You are on crack. Get a grip.")
            return
        char_diff = np.array(map(str, char_diff))
        for x in range(8):
            if(char_diff[x][0] != '-'):
                char_diff[x] = '+' + char_diff[x]
        await message.channel.send("Life: " + char_diff[0] + "Mana: " + char_diff[1] + "Attack: " + char_diff[2] + "Defense: " + char_diff[3] + "Speed: " + char_diff[4] + "Dexterity: " + char_diff[5] + "Vitality: " + char_diff[6] + "Wisdom: " + char_diff[7])
        return

# Cog class for reminder loop
# pings user X seconds before each hour
class ReminderCog(commands.Cog):

    # User user, int secs_before, Channel channel, Bot bot
    def __init__(self, user, secs_before, channel, bot):
        self.user = user
        self.channel = channel
        self.bot = bot
        # converts seconds into minutes and seconds
        self.mins = int((secs_before % 3600) / 60)
        self.secs = secs_before % 60
        # timelist will be a list of dt.time with all 24 hours and the mins/secs before
        timelist = []
        for hr in range(24):
            timelist.append(dt.time(hour=hr, minute=(59-self.mins), second=((60-self.secs) % 60)))
        self.timelist = timelist
        # makes that timelist the list of times the reminder loop happens and starts it
        self.reminder.change_interval(time=self.timelist)
        self.reminder.start()
        
        print(self.user, self.mins, self.secs)

    # unloads the cog (:
    def cog_unload(self):
        self.reminder.cancel()

    # does the same thing init does with time
    def set_time(self, secs_before):
        self.mins = int((secs_before % 3600) / 60)
        self.secs = secs_before % 60
        timelist = []
        for hr in range(24):
            timelist.append(dt.time(hour=hr, minute=(59-self.mins), second=((60-self.secs) % 60)))
        self.timelist = timelist
        self.reminder.change_interval(time=self.timelist)

        print(self.user, self.mins, self.secs)

    # the actual loop, interval is set before
    @tasks.loop()
    async def reminder(self):
        await self.channel.send("<@{0}> It's time to bing bong, you ding dong!".format(self.user.id))

client.run(token)
