import discord
from discord.ext import tasks, commands
import datetime as dt
import json

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
        await message.channel.send("Use !time help for info about reminders.")
        await message.channel.send("Use !tunt help for info about toontown commands.")
        return

    # time specific help message
    if message.content.startswith("!time help"):
        await message.channel.send("Use !time notify X to remind you X seconds before the hour.")
        await message.channel.send("Use !time notify cancel to cancel the reminder.")
        return

    # toontown specific help message
    if message.content.startswith("!tunt help"):
        await message.channel.send("Use !tunt garden X to display the beans needed for level X gardening, with the easiest combination shown first.")
        return

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
