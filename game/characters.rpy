# The foundation for all characters in the game using the charRegister class so they can have their own stats and idk, maybe more later?
default ch_db = {}
default registered_characters = []

init python:
    class charRegister:
        def __init__(self, char_id, power:int=0, agi:int=0, vit:int=0):
            self.id = char_id
            self.power = power
            self.agi = agi
            self.vit = vit
        
        def __call__(self, *args, **kwargs):
            return self.char(*args, **kwargs)

    characters = [
        {"id": "tm", "power": 5, "agi": 4, "vit": 3},
        {"id": "ib", "power": 2, "agi": 7, "vit": 4},
    ]

    for data in characters:
        ch_db[data["id"]] = charRegister(
            char_id=data["id"],
            power=data["power"],
            agi=data["agi"],
            vit=data["vit"]
        )