init python:
    

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

label iscene(target):
    $ scene_register(target)
    $ last_visited_label = target
    call expression target from _call_expression
    
    return

# Simple version of the imenu aka its first version lol
label simenu(target, deafen=False, jump_to=""):
    python:
        scene_register(target)
        last_visited_label = target
        if deafen:
            renpy.music.set_volume(0.3, 1.0, "music") 
            renpy.music.set_volume(0.3, 1.0, "ambient")
    call expression target from _call_expression_3
    python:
        if deafen: 
            renpy.music.set_volume(1.0, 1.0, "music") 
            renpy.music.set_volume(1.0, 1.0, "ambient")

    if jump_to:
        jump expression jump_to from _jump_expression_1

    # use this as $ destination = simenu("choice_label")
    return _return

label imenu(target, followup=None, fallback=None, deafen=False):
    python:
        scene_register(target)
        last_visited_label = target

        if deafen:
            renpy.music.set_volume(0.3, 1.0, "music")
            renpy.music.set_volume(0.3, 1.0, "ambient")

    call expression target from _call_expression_1

    python:
        choice_result = _return

        if deafen:
            renpy.music.set_volume(1.0, 1.0, "music")
            renpy.music.set_volume(1.0, 1.0, "ambient")

        if isinstance(choice_result, dict):
            route_data = choice_result
            
        else:
            followup = route_db.get(followup, {}) if isinstance(followup, str)

            if isinstance(followup, dict):
                route_data = followup.get(choice_result, fallback)
            else:
                route_data = fallback

        if route_data is None:
            route_data = {"action": "return"}

        if isinstance(route_data, str):
            route_data = {"action": "call", "target": route_data}

        action = route_data.get("action", "return")
        route_target = route_data.get("target", "")

        extra_set = route_data.get("set", {})
        for key, value in extra_set.items():
            setattr(store, key, value)
        
    if action == "call" and route_target:
        call expression route_target from _call_expression_2
        return

    elif action == "jump" and route_target:
        jump expression route_target from _jump_expression
    
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
