################################################################################
## CHARACTERS FILE
##
## No spoilers here! Hehe- gotcha, thought it would have little fun
## facts about any major character? Nah, this file is only for defines,
## and their setup + how they're registered in the game. Technical stuff.
## But welp, if you take character names as spoiler, then beware!
################################################################################

## ch_db is a dictionary holding all registered character objects.
## and registered_characters... I genuinely forgot its use rn, but gonna let it stay anyway.
default ch_db = {}
default registered_characters = []

## We initialize a list of character data, then loop through to create charRegister instances.
init python:
    class charRegister:
        def __init__(self, char_id:str, power:int=0, agi:int=0, vit:int=0):
            self.id = char_id
            self.power = power
            self.agi = agi
            self.vit = vit

    ## Each character gets stats like Power (strength?), Agility (speed?), Vitality (health?),
    ## don't know for sure what they mean rn as I still need to finish the combat system.
    characters = [
        {"id": "nerfed_cb", "power": 1, "agi": 1, "vit": 1},
        {"id": "cb", "power": 6, "agi": 9, "vit": 69},
        {"id": "sel", "power": 1, "agi": 1, "vit": 1}
    ]

    for data in characters:
        ch_db[data["id"]] = charRegister(
            char_id=data["id"],
            power=data["power"],
            agi=data["agi"],
            vit=data["vit"]
        )
    
    # if "cb" in ch_db: pass # if example for function

### ALL CHARACTERS CURRENTLY IN THE GAME
## - Prologue
default mc = "" # Move this to another place later
define m = Character("[mc]", color = '#ff9e00')
define unk = Character(_("Unknown"), color="#777777")
define stranger = Character("???", color="#666666")
define cb = Character(_("Cumbeard"), color="#ffffff")
define sel = Character("Seleris", color="#5b3475")


## - Starting Village


## - Dream Realms