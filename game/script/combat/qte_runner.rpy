label qte_execute(session, script, step=None, result=None, prepared=None, playback=None):
    python:
        session._require_state("active")

        if session.run is not None:
            raise RuntimeError("[QTE RUN] A script is already running, can't initiate other")

        prepared = qte_prepare(script, session)
        session.run = QTERun(prepared)
        
        session._qte_context_depth = renpy.context_nesting_level()

    show screen qte_scene_view(session)

    while True:
        $ step = session.run.next_step()

        if step["op"] in ("show", "play"):
            $ playback = session.stage.apply(step)

            if step["op"] == "play" and step.get("wait", True):
                $ renpy.stop_skipping()
                $ session.begin_wait(playback)

                call screen qte_wait_screen(session)

                $ session.end_wait()

        elif step["op"] == "wait":
            $ renpy.stop_skipping()
            $ session.begin_wait(QTEDelay(step["duration"]))

            call screen qte_wait_screen(session)

            $ session.end_wait()

        elif step["op"] == "say":
            if step.get("what"):
                $ renpy.say(step.get("who"), step["what"])

        elif step["op"] == "qte":
            $ session.prepare_qte(step)

        elif step["op"] == "_activate_qte":
            $ renpy.stop_skipping()
            $ session.start_qte(step["definition"])

            call screen qte_interaction_screen(session)

            $ result = session.collect_qte()

        elif step["op"] == "end":
            hide screen qte_scene_view onlayer qte_scene

            $ session.end_run()

            return step["outcome"]
