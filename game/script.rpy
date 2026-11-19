# The game starts here.

label start:
    $ register_characters()
    jump qte_visuals_test

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
    $ check_event(target)
    
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
        jump expression jump_to

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
            followup = rts_db.get(followup, {}) if isinstance(followup, str) else followup

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
        jump expression route_target
    
    return

label glitch_scene(scene_bg, duration=1.0, scene_char=[], dialogue=[]):
    play sound sfx_glitch volume 1.0
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

image beige = Solid("#998e56")

label qte_visuals_test:
    scene beige with fade

    "Isso aqui é um teste, xablau!"
    "Iniciando sequência de animação"

    $ frames = qte_get_frames("images/testing/combat_dummy/dummy_up")
    $ print("Frames: ", frames)

    $ qte_visual = QTEVisual(frames, duration=0.3)

    show screen qte_visuals_preview(qte_visual)

    with Pause(0.7)

    $ frames = qte_get_frames("images/testing/combat_dummy/dummy_up_attack")
    $ print("Frames: ", frames)

    $ qte_visual = QTEVisual(frames, duration=0.1)

    hide screen qte_visuals_preview
    show screen qte_visuals_preview(qte_visual)

    with Pause(0.4)

    $ frames = qte_get_frames("images/testing/combat_dummy/dummy_base")
    $ qte_visual = QTEVisual(frames, duration=0.3)
    hide screen qte_visuals_preview
    show screen qte_visuals_preview(qte_visual)

    with Pause(1.0)

    $ frames = qte_get_frames("images/testing/combat_dummy/dummy_hor")
    $ qte_visual = QTEVisual(frames, duration=0.3)
    hide screen qte_visuals_preview
    show screen qte_visuals_preview(qte_visual)

    with Pause(0.5)

    $ frames = qte_get_frames("images/testing/combat_dummy/dummy_hor_attack")
    $ qte_visual = QTEVisual(frames, duration=0.1)
    hide screen qte_visuals_preview
    show screen qte_visuals_preview(qte_visual)

    with Pause(1.0)

    $ frames = qte_get_frames("images/testing/combat_dummy/dummy_base")
    $ qte_visual = QTEVisual(frames, duration=0.3)
    hide screen qte_visuals_preview
    show screen qte_visuals_preview(qte_visual)

    with Pause(0.4)

    hide screen qte_visuals_preview

    "fim da animação"

    jump qte_click_test

    return

label qte_click_test:

    "fica esperto mané"

    call qte({
        "type": "click",
        "image": "images/testing/ui/qte_test.png",
        "xpos": 640,
        "ypos": 360,
        "scale": 0.5,
        "timeout": 2.0,
        "given_input": "parry",
    })

    $ result = _return

    if result.success:
        "Oloco tá esperto mesmo."
    else:
        "Tomou gap kkkkkkkkk."

    $ print(
        "QTE result:",
        result.grade,
        result.reason,
        result.elapsed,
    )

    "ei"

    "hã?"

    "cuidado mano"

    "quem é você?"

    ":dedo meio:"

    "quê?"

    "vo dormi"

    jump qte_mult_buttons_test

    return

label qte_mult_buttons_test:
    call qte({"xpos": 960, "ypos": 540 ,})
    call qte({})
    call qte({})

    call qte_session({
        "pattern": "burst",
        "count": 5,
        "timeout": 2.0,
        "threshold": 0.6,

        "button": {
            "type": "click",
            "image": "images/testing/ui/qte_test.png",
            "scale": 0.5,
        },

        "buttons": [
            {"xpos": 960, "ypos": 270},
            {"xpos": 720, "ypos": 540},
            {"xpos": 1200, "ypos": 540},
            {"xpos": 840, "ypos": 810},
            {"xpos": 1080, "ypos": 810},
        ],
    })

    $ result = _return

    if result.success:
        "que isso tankou até a estrelinha"
    else:
        "tomou gap de israel mt rui"

    "acertou [result.hits] de [result.total]"

    "mas será que o caba é bom mesmo?"

    "fica esperto"

    call qte_session({
        "pattern": "chain",
        "count": 12,
        "timeout": 0.8,
        "threshold": 0.7,
        
        "hint_line": True,

        "button": {
            "type": "click",
            "image": "images/testing/ui/qte_test.png",
            "scale": 0.5,
        },

        "buttons": [
            {"xpos": 960, "ypos": 270},
            {"xpos": 720, "ypos": 540},
            {"xpos": 1200, "ypos": 540},
            {"xpos": 840, "ypos": 810},
            {"xpos": 1080, "ypos": 810},
            {"xpos": 960, "ypos": 540},
        ],
    })

    $ result = _return

    if result.success:
        "rapaz, comprou o jogo só pra voce foi?"
    else:
        "slc melhore"
    
    "acertou [result.hits] de [result.total]"

    if result.hits > 10:
        "sai daqui jogador de osu!"
    
    call qte_session({
        "pattern": "timed",
        "count": 12,
        "timeout": 1.0,
        "spawn_interval": 0.3,
        "threshold": 0.7,

        "hint_line": True,

        "button": {
            "type": "click",
            "image": "images/testing/ui/qte_test.png",
            "scale": 0.5,
        },

        "buttons": [
            {"xpos": 960, "ypos": 270},
            {"xpos": 720, "ypos": 540},
            {"xpos": 1200, "ypos": 540},
            {"xpos": 840, "ypos": 810},
            {"xpos": 1080, "ypos": 810},
            {"xpos": 960, "ypos": 540},
        ],
    })

    $ result = _return

    if result.success:
        "o caba é bom demais mesmo, insano"
    else:
        "porque tu ainda tá jogando mano, desiste logo"
    
    "acertou [result.hits] de [result.total]"

    "agora, preparado pro desafio supremo?"

    "é paizao, tudo isso só foi um aquecimento"

    "FICA ESPERTO"

    $ wins = 0
    
    call qte_session({
        "pattern": "burst",
        "count": 16,
        "timeout": 3.0,
        "threshold": 0.8,

        "button": {
            "type": "click",
            "image": "images/testing/ui/qte_test.png",
            "scale": 0.5,
        },

        "buttons": [
            {"xpos": 960, "ypos": 270},
            {"xpos": 840, "ypos": 270},
            {"xpos": 720, "ypos": 270},
            {"xpos": 1080, "ypos": 270},
            {"xpos": 1200, "ypos": 270},
            {"xpos": 960, "ypos": 810},
            {"xpos": 840, "ypos": 810},
            {"xpos": 720, "ypos": 810},
            {"xpos": 1080, "ypos": 810},
            {"xpos": 1200, "ypos": 810},
            {"xpos": 720, "ypos": 405},
            {"xpos": 720, "ypos": 540},
            {"xpos": 720, "ypos": 675},
            {"xpos": 1200, "ypos": 405},
            {"xpos": 1200, "ypos": 540},
            {"xpos": 1200, "ypos": 675},
        ],
    })

    $ result = _return

    if result.success:
        $ wins += 1
    
    call qte_session({
        "pattern": "chain",
        "count": 24,
        "timeout": 0.5,
        "threshold": 0.8,

        "hint_line": True,

        "button": {
            "type": "click",
            "image": "images/testing/ui/qte_test.png",
            "scale": 0.5,
        },

        "buttons": [],
    })

    $ result = _return

    if result.success:
        $ wins += 1

    call qte_session({
        "pattern": "timed",
        "count": 32,
        "timeout": 1.0,
        "spawn_interval": 0.3,
        "threshold": 0.7,

        "hint_line": True,

        "button": {
            "type": "click",
            "image": "images/testing/ui/qte_test.png",
            "scale": 0.5,
        },

        "buttons": [],
    })

    $ result = _return

    if result.success:
        $ wins += 1
    
    if wins >= 2:
        "Rapaz, nao eh que tu passou no teste mesmo, parabains"
        "Agora sai logo daqui e volta pro seu osu"
    else:
        "Falhastes, mas nao se sinta indigno pequeno gafanhoto"
        "significa que voce nao joga osu! e tem vida social, se duvidar namorada"
        "entao prossiga ao próximo desafio"

    jump qte_combat_dummy_test

    return

label qte_combat_dummy_test:
    "vê se não rebola de ladinho na primeira luta"

    "tente acertar seu inimigo até cair"

    window hide

    call combat_beat({
        "prepare": {
            "path": "images/testing/combat_dummy/dummy_up",
            "duration": 0.35,
            "scale": 1.0,
        },

        "qte": {
            "pattern": "single",
            "timeout": 0.7,

            "button": {
                "type": "click",
                "image": "images/testing/ui/qte_test.png",
                "scale": 0.5,

                "xpos": 640,
                "ypos": 360,

                "given_input": "parry",
            },
        },

        "success": {
            "path": "images/testing/combat_dummy/dummy_parry",
            "duration": 0.3,
        },

        "failure": {
            "path": "images/testing/combat_dummy/dummy_up_attack",
            "duration": 0.25,
        },

        "recover": {
            "path": "images/testing/combat_dummy/dummy_base",
            "duration": 0.3,
        },
    })

    $ result = _return
    $ wins = 0

    window auto

    if result.success:
        $ wins += 1
    
    call combat_beat({
        "prepare": {
            "path": "images/testing/combat_dummy/dummy_up",
            "duration": 0.7,
            "scale": 1.0,
        },

        "qte": {
            "pattern": "single",
            "timeout": 0.5,

            "button": {
                "type": "click",
                "image": "images/testing/ui/qte_test.png",
                "scale": 0.5,

                "xpos": 640,
                "ypos": 360,

                "given_input": "parry",
            },
        },

        "success": {
            "path": "images/testing/combat_dummy/dummy_parry",
            "duration": 0.3,
        },

        "failure": {
            "path": "images/testing/combat_dummy/dummy_up_attack",
            "duration": 0.25,
        },

        "recover": {
            "path": "images/testing/combat_dummy/dummy_base",
            "duration": 0.3,
        },
    })

    $ result = _return

    if result.success:
        $ wins += 1
    
    call combat_beat({
        "prepare": {
            "path": "images/testing/combat_dummy/dummy_up",
            "duration": 0.35,
            "scale": 1.0,
        },

        "qte": {
            "pattern": "single",
            "timeout": 0.7,

            "button": {
                "type": "click",
                "image": "images/testing/ui/qte_test.png",
                "scale": 0.5,

                "xpos": 640,
                "ypos": 360,

                "given_input": "parry",
            },
        },

        "success": {
            "path": "images/testing/combat_dummy/dummy_parry",
            "duration": 0.3,
        },

        "failure": {
            "path": "images/testing/combat_dummy/dummy_up_attack",
            "duration": 0.25,
        },

        "recover": {
            "path": "images/testing/combat_dummy/dummy_base",
            "duration": 0.3,
        },
    })

    $ result = _return

    if result.success:
        $ wins += 1
    
    call combat_beat({
        "mirrored": True,

        "prepare": {
            "path": "images/testing/combat_dummy/dummy_up",
            "duration": 0.35,
            "scale": 1.0,
        },

        "qte": {
            "pattern": "single",
            "timeout": 0.7,

            "button": {
                "type": "click",
                "image": "images/testing/ui/qte_test.png",
                "scale": 0.5,

                "mirror_xpos": True,
                "xpos": 640,
                "ypos": 360,

                "given_input": "parry",
            },
        },

        "success": {
            "path": "images/testing/combat_dummy/dummy_parry",
            "duration": 0.3,
        },

        "failure": {
            "path": "images/testing/combat_dummy/dummy_up_attack",
            "duration": 0.25,
        },

        "recover": {
            "path": "images/testing/combat_dummy/dummy_base",
            "duration": 0.3,
        },
    })

    $ result = _return

    if result.success:
        $ wins += 1
    
    call combat_beat({
        "prepare": {
            "path": "images/testing/combat_dummy/dummy_up",
            "duration": 0.7,
            "scale": 1.0,
        },

        "qte": {
            "pattern": "single",
            "timeout": 1.0,

            "button": {
                "type": "click",
                "image": "images/testing/ui/qte_test.png",
                "scale": 0.5,

                "mirror_xpos": True,
                "xpos": 640,
                "ypos": 360,

                "given_input": "parry",
            },
        },

        "success": {
            "path": "images/testing/combat_dummy/dummy_parry",
            "duration": 0.3,
        },

        "failure": {
            "path": "images/testing/combat_dummy/dummy_up_attack",
            "duration": 0.25,
        },

        "recover": {
            "path": "images/testing/combat_dummy/dummy_base",
            "duration": 0.3,
        },
    })

    $ result = _return

    if result.success:
        $ wins += 1
    
    if wins > 3:
        "Rapaz mas cê tá afiado, nada mal mesmo ein"
        "Continua assim que logo logo tu acaba com ele"
    else:
        "Mermão eu já num te disse pra quitar?"
        "Se tu nao conseguiu isso quem dirá o que vai vir"

    "Agora se prepara que a coisa vai esquentar"
    "La vem ele!"

    call combat_sequence({
        "recover": {
            "path": "images/testing/combat_dummy/dummy_base",
            "duration": 0.3,
        },

        "prepare": {
            "path": "images/testing/combat_dummy/dummy_up",
            "duration": 0.3,
        },

        "success": {
            "path": "images/testing/combat_dummy/dummy_parry",
            "duration": 0.2,
        },

        "failure": {
            "path": "images/testing/combat_dummy/dummy_up_attack",
            "duration": 0.2,
        },

        "qte": {
            "timeout": 1.0,
            "threshold": 0.7,

            "button": {
                "type": "click",
                "image": "images/testing/ui/qte_test.png",
                "scale": 0.5,
                "given_input": "parry",
            },

            "buttons": [
                {"recoverup": 0},
                {},
                {"xpos": 960, "ypos": 270, "windup": 0},
                {"xpos": 840, "ypos": 270, "recoverup": 0.4, "windup": 0.8, "timeout": 0.7},
                {"xpos": 720, "ypos": 270, "recoverup": 0.15, "windup": 0,
                    "prepare": {
                        "path": "images/testing/combat_dummy/dummy_hor",
                        "duration": 0.5,
                    },
                    "failure": {
                        "path": "images/testing/combat_dummy/dummy_hor_attack",
                    },
                },
                {"xpos": 720, "ypos": 270, "recoverup": 0.4, "windup": 0.8, "mirrored": True, "timeout": 0.8},
                {"xpos": 600, "ypos": 270, "recoverup": 0.2, "windup": 0.3, "mirrored": True, "timeout": 0.8},
                {"xpos": 720, "ypos": 270, "recoverup": 0.2, "windup": 0.3, "mirrored": True, "timeout": 0.7},
                {"xpos": 600, "ypos": 270, "windup": 0.2, "timeout": 0.6},
                {"xpos": 600, "ypos": 270, "windup": 0.2, "mirrored": True, "timeout": 0.6},
                {"xpos": 720, "ypos": 440, "windup": 0.2, "timeout": 0.6},
                {"xpos": 720, "ypos": 440, "windup": 0.2, "mirrored": True, "timeout": 0.6},
                {"xpos": 600, "ypos": 270, "windup": 0.1, "timeout": 0.5},
                {"xpos": 600, "ypos": 270, "windup": 0.1, "mirrored": True, "timeout": 0.5},
            ],
        },
    })

    $ result = _return

    if result.success:
        "Calma ai musashi miyamoto"
        "Mas pelo menos tu é bom com combates de espada (ou osu! na verdade)"
    else:
        "Sai logo mano essa novel não é pra tu fi"
        "mentira pode ficar, só que tu vai sofrer mais"
    
    "Foi um ótimo aquecimento não foi?"
    "AGORA, TENTE DERROTÁ-LO USANDO SEU MÁXIMO!!"
    "Você precisa acertá-lo dez vezes pra vencer"
    "Se você errar apenas três vezes, perde"
    "BOA SORTE!"

    return