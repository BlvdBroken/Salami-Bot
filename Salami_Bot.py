import discord
from discord.ext import tasks, commands
import datetime as dt
import json
import numpy as np # yeah, im a physicist,
from discord import app_commands
from typing import Optional
import math
import sqlite3

#initialises sqlite db, with db file named salami.db
db=sqlite3.connect("salami.db")
cursor=db.cursor()

#helper for sql commands
def execute(command):
    global db   
    global cursor
    print(command)
    cursor.execute(command)
    db.commit()
    return


# opens a json with the token for obfuscation
with open('config.json') as f:
    data = json.load(f)
    token = data["TOKEN"]

# full intents, because personal server, required for discord.py 2.0
intents = discord.Intents.all()
client = discord.Client(intents=intents)

# this client's command tree (or list of inbuilt commands)
general_tree = discord.app_commands.CommandTree(client)
# group for toontown commands (allows for multiple tunt slash commands)
tuntGroup = app_commands.Group(name="tunt", description="Toontown commands")
# add group(s) to the command tree
general_tree.add_command(tuntGroup)

# dict to keep track of who asks for a reminder, author.id : ReminderCog
user_reminder_cogs_dict = {}

# dict for bean color : emoji id
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

    # use only if adding/changing a slash command
    if message.content.startswith("!update"):
        await general_tree.sync()
        await message.channel.send("Commands successfully updated.")
        return

    # general help message
    if message.content.startswith("!help"):
        await message.channel.send("Use `!time help` for info about reminders.")
        await message.channel.send("Use `!tunt help` for info about toontown commands.")
        await message.channel.send("Use `!rotmg help` for info about rotmg commands.")
        await message.channel.send("Use `!morb help` to learn more about the art of morbing.")
        return

    # time specific help message
    if message.content.startswith("!time help"):
        await message.channel.send("Use `!time notify X` to remind you X seconds before the hour.")
        await message.channel.send("Use `!time notify cancel` to cancel the reminder.")
        return  

    # toontown specific help message
    if message.content.startswith("!tunt help"):
        await message.channel.send("Use `!tunt garden X` to display the beans needed for level X gardening, with the easiest combination shown first.")
        await message.channel.send("Use `/tunt kill` to see if a group of gags kills a cog.\nThe format for a gag is xxN where xx is the first two letters of a gag track and N is the level the gag is.\nFor an organic gag, add an \'o\' to the end of the gag.\nGag tracks include trap(tr), sound(so), throw(th), squirt(sq), and drop(dr).")
        return

    # rotmg specific help message
    if message.content.startswith("!rotmg help"):
        await message.channel.send("Use `!rotmg roll <class> <life> <mana> <att> <def> <spd> <dex> <vit> <wis>` to see how good your roll is. Input remaining pots to max.")
        return


    # stu id easter egg messages
    #morb specific help message
    if message.content.startswith("!morb help"):
        await message.channel.send("Use `!morb` to morb.")
        await message.channel.send("Use `!morb stats` to get some stats on your morbing")
        return
    #gets the number of times a user has morbed, and dispplays
    elif message.content.startswith("!morb stats"):
        execute('SELECT morbCount FROM morbStats WHERE userID="'+message.author.id+'";')
        morbCount=cursor.fetchall()[0][0]
        await message.channel.send("you have morbed "+str(morbCount)+" times. Keep on morbing!")
        return
    #morbs and increases users morb counter by 1
    elif message.content.startswith("!morb"):
        await message.channel.send("It's morbin' time!")
        execute('UPDATE morbStats SET morbCount=morbCount+1 WHERE userID="'+message.author.id+'";')
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

    # rotmg stat roll handler
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
        except (ValueError, IndexError):
            # no input / not integers
            await message.channel.send("The numbers, Mason, what do they mean?")
            return
        char_diff = char_diff.astype(str)
        for x in range(8):
            if(char_diff[x][0] != '-'):
                char_diff[x] = '+' + char_diff[x]
        await message.channel.send("Life: " + char_diff[0] + "\nMana: " + char_diff[1] + "\nAttack: " + char_diff[2] + "\nDefense: " + char_diff[3] + "\nSpeed: " + char_diff[4] + "\nDexterity: " + char_diff[5] + "\nVitality: " + char_diff[6] + "\nWisdom: " + char_diff[7])
        return

# class to keep track of a cog and damage done to it for /tunt kill
class tuntCog():

    # int level, int lured, int vTwo, Channel channel
    def __init__(self, level, lured, vTwo, channel):
        self.channel = channel
        self.level = level
        self.health = ((level + 1) * (level + 2)) if (level < 12) else ((level + 1) * (level + 2) + 14)
        self.lured = lured
        self.vTwo = vTwo
        # dictionary of tuples with an array of tuples
        # (int, int, (int, String)[])
        # name key : (total damage, times hit, (gag damage, gag name)[])
        # im so sorry
        self.damage = {
        "tr" : (0, 0, [(0,"null"), (12,"Banana Peel"), (20,"Rake"), (35,"Marbles"), (50,"Quicksand"), (85,"Trapdoor"), (180,"TNT"), (200,"Railroad")]), # trap
        "so" : (0, 0, [(0,"null"), (4,"Bike Horn"), (7,"Whistle"), (11,"Bugle"), (16,"Aoogah"), (21,"Elephant Trunk"), (50,"Foghorn"), (90,"Opera Singer")]), # sound
        "th" : (0, 0, [(0,"null"), (6,"Cupcake"), (10,"Fruit Pie Slice"), (17,"Cream Pie Slice"), (27,"Whole Fruit Pie"), (40,"Whole Cream Pie"), (100,"Birthday Cake"), (120,"Wedding Cake")]), # throw
        "sq" : (0, 0, [(0,"null"), (4,"Squirting Flower"), (8,"Glass of Water"), (12,"Squirt Gun"), (21,"Seltzer Bottle"), (30,"Fire Hose"), (80,"Storm Cloud"), (105,"Geyser")]), # squirt
        "dr" : (0, 0, [(0,"null"), (10,"Flower Pot"), (18,"Sandbag"), (30,"Anvil"), (45,"Big Weight"), (70,"Safe"), (170,"Grand Piano"), (180,"Toontanic")]) # drop
        }
        # string returned in calc for response
        self.attackString = "Using "
        # set to true when invalid command passed
        # initial value is dependant on whether lured and vTwo are either 0 or 1
        self.broken = not (((self.lured == 0) or (self.lured == 1)) and ((self.vTwo == 0) or (self.vTwo == 1)))

    # called for each gag passed in the slash command
    # interprets string input and adds its name/damage to class variables
    def attack(self, gag):
        # checks if gag input is valid dict key
        if not (self.damage.get(gag[:2], False)):
            self.broken = True
            return
        # checks if gag input is integer level
        try:
            gagLevel = int(gag[2])
            # checks if gag input is valid level
            if ((gagLevel > 7) or (gagLevel < 1)):
                self.broken = True
                return
        except ValueError:
            self.broken = True
            return
        # example of String gag would be sq5o where gag[:2] is key name for self.damage and o is optional organic
        gagString = self.damage[gag[:2]][2][int(gag[2])][1]
        singleDamage = self.damage[gag[:2]][2][int(gag[2])][0]
        # checks if the length is long enough for organic and check if it is organic
        if (len(gag) == 4):
            if (gag[3] == 'o'):
                # if it is organic change gag string and add the bonus damage
                gagString = "organic " + gagString
                singleDamage = math.floor(singleDamage * 1.1)
        # if the cog is v2.0 subtract the armor (min damage is zero (probably))
        if (self.vTwo == 1):
            singleDamage = max(singleDamage - math.floor(self.level * 1.5), 0)
        # scuffed way of editing the dict
        # adds on the damage, adds one to the number of times track used, and just re-places the array tuple frankenstein's monster
        self.damage[gag[:2]] = (self.damage[gag[:2]][0] + singleDamage, self.damage[gag[:2]][1] + 1, self.damage[gag[:2]][2])
        # adds gag name to the string class variable
        self.attackString += "{0} + ".format(gagString)

    # called after all the gags are added
    # calculates the total damage on a cog and formats and returns a response string
    def calc(self):
        if (self.broken):
            return "Please input valid command."
        # first part of the response becomes the gags used, lure/v2 status, level, and cog health
        self.attackString = "{0} on a {1}level {2}{3} cog with {4} health.\n".format(self.attackString[:-3], "lured " if (self.lured == 1) else "", self.level, "v2.0" if (self.vTwo == 1) else "", self.health)
        # init damages, seperate for lured handling
        lureBonus = 0
        trapDamage = 0
        soundDamage = 0
        throwDamage = 0
        squirtDamage = 0
        dropDamage = 0
        # trap damage handler
        trapDamage += self.damage.get("tr")[0]
        # cancels trap if multiple
        if (self.damage.get("tr")[1] > 1):
            trapDamage = 0
        # unlures trapped cogs
        if (trapDamage > 0):
            self.lured = 0
        # sound damage handler
        soundDamage += self.damage.get("so")[0]
        # handles combo damage
        if (self.damage.get("so")[1] > 1):
            soundDamage = math.ceil(soundDamage * 1.2)
        # unlures sounded cogs
        if (soundDamage > 0):
            self.lured = 0
        # throw damage handler
        throwDamage += self.damage.get("th")[0]
        # calcs lure bonus damage and unlures thrown cogs
        if (throwDamage > 0) and (self.lured == 1):
            lureBonus = math.ceil(throwDamage * 0.5)
            self.lured = 0
        # handles combo damage
        if (self.damage.get("th")[1] > 1):
            throwDamage = math.ceil(throwDamage * 1.2)
        # squirt damage handler
        squirtDamage += self.damage.get("sq")[0]
        # calcs lure bonus damage and unlures squirted cogs
        if (squirtDamage > 0) and (self.lured == 1):
            lureBonus = math.ceil(squirtDamage * 0.5)
            self.lured = 0
        # handles combo damage
        if (self.damage.get("sq")[1] > 1):
            squirtDamage = math.ceil(squirtDamage * 1.2)
        # drop damage handler
        dropDamage += self.damage.get("dr")[0]
        # handles combo damage
        if (self.damage.get("dr")[1] > 1):
            dropDamage = math.ceil(dropDamage * 1.2)
        # drop doesn't damage lured cogs you dummy
        if (self.lured == 1):
            self.attackString += "Should've used Sound to unlure the cogs.\n"
            dropDamage = 0
        # adds up track damages and lure bonus
        totalDamage = trapDamage + soundDamage + throwDamage + squirtDamage + dropDamage + lureBonus
        # adds how much cog was/wasn't killed by to the response string
        if (self.health - totalDamage == 0):
            self.attackString += "This kills exactly. God gamer alert."
        elif (self.health - totalDamage < 0):
            self.attackString += "This kills. You overkill by {0} damage.".format((totalDamage - self.health))
        else:
            self.attackString += "This does not kill. The cog is left with {0} health.".format((self.health - totalDamage))
        return self.attackString
        
# subcommand of /tunt
@tuntGroup.command()
@app_commands.describe(
    level='The level of the cog you\'re killing',
    lured='1 if lured, 0 if unlured',
    vtwo='1 if v2.0, 0 if not',
    firstgag='First gag being used, see `!tunt help` for details.',
    secondgag='(Optional) Second gag being used, see `!tunt help` for details.',
    thirdgag='(Optional) Third gag being used, see `!tunt help` for details.',
    fourthgag='(Optional) Fourth gag being used, see `!tunt help` for details.'
)
# second through fourth gags are optional in the command
# reason why vtwo and not vTwo is capitals not allowed in interaction slash command arguments
async def kill(interaction: discord.Interaction, level: int, lured: int, vtwo: int, firstgag : str, secondgag : Optional[str], thirdgag : Optional[str], fourthgag : Optional[str],):
    """Checks if the given gags can kill a cog."""
    # creates new cogToKill class
    cogToKill = tuntCog(level, lured, vtwo, interaction.channel)
    # first is not optional, always runs attack
    cogToKill.attack(firstgag)
    # next three are optional, so checks if none before "attacking"
    if secondgag is not None:
        cogToKill.attack(secondgag)
    if thirdgag is not None:
        cogToKill.attack(thirdgag)
    if fourthgag is not None:
        cogToKill.attack(fourthgag)
    # responds with what calc returns after the attacks
    # ephemeral=False means other people can see your command
    await interaction.response.send_message(cogToKill.calc(), ephemeral=False)


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

#this is just me trying to figure out how git works