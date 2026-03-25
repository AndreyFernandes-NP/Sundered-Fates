# The foundation for all characters in the game using the charRegister class so they can have their own stats and idk, maybe more later?
default ch_db = {}
default registered_characters = []

init python:
    class charRegister:
        def __init__(self, char_id:str, power:int=0, agi:int=0, vit:int=0):
            self.id = char_id
            self.power = power
            self.agi = agi
            self.vit = vit

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

## - Dreams