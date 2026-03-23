# The script of the game goes in this file.

# Declare characters used by this game. The color argument colorizes the
# name of the character.

define e = Character("Eileen")


# The game starts here.

label start:

    # Show a background. This uses a placeholder by default, but you can
    # add a file (named either "bg room.png" or "bg room.jpg") to the
    # images directory to show it.

    scene bg room

    # This shows a character sprite. A placeholder is used, but you can
    # replace it by adding a file named "eileen happy.png" to the images
    # directory.

    show eileen happy

    # These display lines of dialogue.

    e "You've created a new Ren'Py game."

    e "Once you add a story, pictures, and music, you can release it to the world!"

    # This ends the game.

    return

# Maybe create one for menus too? Depends if I really need it.
label iscene(target):
    $ scene_register(target)
    call expression target from _call_expression
    
    return

label glitch_scene(scene_bg, duration=1.0, scene_char=[], dialogue=[]):
    play sound sfx_glitch volume 1.5
    show expression animated_glitch("bg " + scene_bg, chroma=True, timeout_base=0.05, timeout_vanilla=(0.05)) as glitch_bg

    if scene_char:
        python:
            for character in scene_char:
                renpy.show("glitch_char", what=animated_glitch(character, chroma=True, timeout_base=0.05, timeout_vanilla=(0.05)))

    with Pause(duration)

    hide glitch_bg
    hide glitch_char

    python:
        if dialogue:
            for who, what in dialogue:
                renpy.say(who, what)

    return
