# The foundation for all characters in the game using the charRegister class so they can have their own stats and idk, maybe more later?

init python:
    class charRegister:
        def __init__(self, char:Character(), powr:int=0, agi:int=0, vit:int=0):
            self.char = char
            self.powr = powr
            self.agi = agi
            self.vit = vit
        
        def __call__(self, *args, **kwargs):
            return self.char(*args, **kwargs)

# TODO: decide if the class should be only for a character's stats and info, or if it should also include the character itself. Having the character in the class could be messy as to how to call it in dialogue and stuff, like it's just way better to call tm instead of tm.char.

# So far this is just a template, later use a for/while with a function to create characters from a list/dictionary of name and stats.
# That way we can even append characters middle game if we want to, and it would be easier to manage them all in one place.
# The idea is that it would call the checker function, see in a list of characters that where created with the charRegister,
# and then add the character if it's not already in the list.
define tm = charRegister(Character("TM", color="#FF0000"))

# Character list going to be added below