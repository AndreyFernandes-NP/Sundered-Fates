image beige = Solid("#998e56")

init 1 python:
    QTE_VIEWS["testing_dummy"] = {
        "idle": qte_clip("images/testing/combat_dummy/dummy_base", fit=True),
        "prepare": qte_clip("images/testing/combat_dummy/dummy_up", duration=0.4, fit=True),
        "attack": qte_clip("images/testing/combat_dummy/dummy_up_attack", duration=0.4, fit=True),
        "parry": qte_clip("images/testing/combat_dummy/dummy_parry", duration=0.4, fit=True),
    }

    QTE_VIEWS["player"] = {
        "idle": qte_clip("images/testing/player/player_test_base", fit=True),
        "prepare": qte_clip("images/testing/player/player_test_prepare", fit=True),
        "attack": qte_clip("images/testing/player/player_test_attack", fit=True),
        "parry": qte_clip("images/testing/player/player_test_parry", duration=0.3, fit=True),
    }

    sfx_test = [
        "audio/sounds/testing/sword_test_1",
        "audio/sounds/testing/sword_test_2",
        "audio/sounds/testing/sword_test_3",
    ]

    vfx_test = [
        "hpunch",
        "vpunch",
    ]

    demo = qte_script(
            qte_show("enemy", "idle", x=0.5, y=0.5),
            qte_show("player", "idle", y=0.65, scale=0.75),
            qte_say(what="Single"),

            qte_single(
                "test_single",
                duration=1.0,
                skin="small_d",
                on_start=(qte_play("enemy", "prepare")),
                on_success=(qte_play("player", "parry", wait=False, then="idle", sfx=qte_sfx(sfx_test, volume=0.3), effect=qte_effect(vfx_test)), qte_play("enemy", "attack", then="idle")),
            ),

            qte_say(what="Burst"),

            qte_burst(
                "test_burst",
                count=12,
                duration=4.0,
                threshold=0.8,
                skin="small_d",
                on_start=(qte_play("enemy", "prepare")),
                on_press=(qte_play("enemy", "attack", duration=0.2, then="prepare", then_duration=0.3), qte_play("player", "parry", duration=0.2, then="idle")),
                on_success=(qte_play("player", "parry", wait=False, then="idle"), qte_play("enemy", "attack", then="idle")),
            ),

            qte_say(what="Chain"),

            qte_chain(
                "test_chain",
                count=12,
                duration=0.7,
                skin="small_d",
                on_start=(qte_play("enemy", "prepare")),
                on_press=(qte_play("enemy", "attack", duration=0.2, then="prepare", then_duration=0.3, sfx=qte_sfx(sfx_test, volume=0.3), effect=qte_effect(vfx_test)), qte_play("player", "parry", duration=0.2, then="idle")),
                on_miss=qte_play("enemy", "attack", duration=0.1, then="prepare", then_duration=0.2),
                on_end=qte_play("enemy", "attack", then="idle", wait=True),
                mirrored=qte_choice([True, False], mode="alternate", first="random"),
                mirror=["player", "enemy"],
                layout="random",
                hint_line=True,
            ),

            qte_say(what="Timed"),

            qte_timed(
                "test_timed",
                count=12,
                interval=0.3,
                duration=1.0,
                threshold=0.8,
                on_start=(qte_play("enemy", "prepare")),
                on_press=(qte_play("enemy", "attack", duration=0.2, then="prepare", then_duration=0.3, sfx=qte_sfx(qte_choice(sfx_test, mode="avoid_last", last=1), volume=[0.3, 0.4, 0.3]), effect=qte_effect(vfx_test)), qte_play("player", "parry", duration=0.2, then="idle")),
                on_miss=qte_play("enemy", "attack", duration=0.1, then="prepare", then_duration=0.2),
                on_end=qte_play("enemy", "attack", then="idle", wait=True),
                layout="random",
                skin="small_d",
                hint_line=True,
            ),

            qte_say(what="Fim"),
            qte_end("test_finished"),
        )
        
label qte_testing:
    scene beige with fade

    call qte_scene(
        "patterns_test",
        player_stats={},
        cast=("enemy", "testing_dummy", "enemy"),
        script=demo,
    )

    $ summary = _return
    $ end_result = summary["qtes"][-1]["reason"]

    "Resultado da cena: [end_result]."

    return