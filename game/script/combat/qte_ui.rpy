init python:
    import time

    renpy.add_layer("qte_scene", below="screens", menu_clear=True)

    def qte_ui_signature(session):
        interaction = session.qte.current

        return (session.state, interaction, None if interaction is None else interaction.view_revision, session.stage.revision)

    def qte_ui_clock_reset(session):
        session._qte_tick_at = None
        session._qte_ui_signature = None

    def qte_ui_begin(session):
        qte_ui_clock_reset(session)

        session._qte_ui_signature = qte_ui_signature(session)

    def qte_ui_refresh(session):
        signature = qte_ui_signature(session)

        if signature != session._qte_ui_signature:
            session._qte_ui_signature = signature

            renpy.restart_interaction()

    def qte_ui_tick(session, input_name=None):
        if(renpy.context_nesting_level() != getattr(session, "_qte_context_depth", 0)):
            session._qte_tick_at = None
            return None

        result = None

        if session.state == "active":
            now = time.monotonic()

            dt = (0.0 if session._qte_tick_at is None else max(0.0, now - session._qte_tick_at))
            session._qte_tick_at = now

            result = session.update(dt, input_name)

        else:
            session._qte_tick_at = None

        if result is None:
            qte_ui_refresh(session)

        return result

    def qte_ui_input(session, group, control, input_name, **data):
        if (session.state != "active" or session.qte.current is not group or control not in group.active or control.result is not None):
            return None

        return qte_ui_tick(session, {"uid": control.uid, "name": input_name, "data": data})

    def qte_ui_toggle_pause(session):
        if session.state == "paused":
            session.resume()

        else:
            result = qte_ui_tick(session)

            if result is not None:
                return result

            session.pause()

        qte_ui_refresh(session)

        return None

    def qte_ui_after_load():
        if qte_active_session is not None:
            qte_ui_clock_reset(qte_active_session)

    config.after_load_callbacks.append(qte_ui_after_load)

screen qte_scene_view(session):
    layer "qte_scene"
    zorder -1

    on "show" action Function(qte_ui_begin, session, _update_screens=False)
    timer 0.01 repeat True action Function(qte_ui_tick, session, _update_screens=False)

    $ current = session.qte.current
    $ mirrored = current is not None and current.definition.get("mirrored", False)

    for actor_id, slot index (actor_id, slot["serial"]) in session.stage.draw_order():
        $ actor_mirrored = mirrored and slot["follow_mirror"]

        add slot["playback"].view:
            pos (slot["x"], slot["y"])
            anchor (0.5, 0.5)

            at Transform(xzoom=-1 if actor_mirrored else 1)

screen qte_wait_screen(session):
    modal True
    zorder 200

    on "show" action Function(qte_ui_begin, session, _update_screens=False)

    key "dismiss" action NullAction()
    key "game_menu" action NullAction()
    key "rollback" action NullAction()
    key "skip" action NullAction()
    key "toggle_skip" action NullAction()

screen qte_interaction_screen(session):
    modal True
    zorder 200

    on "show" action Function(qte_ui_begin, session, _update_screens=False)

    key "game_menu" action NullAction()
    key "rollback" action NullAction()
    key "skip" action NullAction()
    key "toggle_skip" action NullAction()

    $ interaction = session.qte.current

    if interaction is not None:
        use expression interaction.screen_name pass (session, interaction)

screen qte_hint_line(source, target, ratio=0.5, max_px=180):
    $ sx = source["x"] * config.screen_width
    $ sy = source["y"] * config.screen_height

    $ dx = (target["x"] - source["x"]) * config.screen_width
    $ dy = (target["y"] - source["y"]) * config.screen_height

    $ distance = math.hypot(dx, dy)

    if distance > 0:
        $ length = min(distance * ratio, max_px)
        $ angle = math.degrees(math.atan2(dy, dx))

        $ mid_x = sx + dx / distance * length / 2
        $ mid_y = sy + dy / distance * length / 2

        add "images/testing/ui/hint_line_glow.png":
            pos (absolute(mid_x), absolute(mid_y))
            anchor (0.5, 0.5)
            xysize (max(1, int(length)), 16)

            at Transform(rotate=angle, rotate_pad=False, alpha=0.4)

        add "images/testing/ui/hint_line.png":
            pos (absolute(mid_x), absolute(mid_y))
            anchor (0.5, 0.5)
            xysize (max(1, int(length)), 4)

            at Transform(rotate=angle, rotate_pad=False, alpha=0.9)

screen qte_click_control(session, group, interaction):
    $ definition = interaction.definition
    $ visual = interaction.visual

    fixed:
        pos (
            float(definition.get("x", 0.5)),
            float(definition.get("y", 0.6)),
        )

        anchor (0.5, 0.5)
        xysize (visual.box_size, visual.box_size)

        if visual.skin["approach"] is not None:
            add visual.skin["approach"]:
                align (0.5, 0.5)
                at Transform(function=visual.animate_approach, subpixel=True, xzoom=-1 if definition.get("mirrored", False) else 1)

        imagebutton:
            idle visual.skin["idle"]
            hover visual.skin["hover"]
            insensitive visual.skin["idle"]

            align (0.5, 0.5)
            padding (0, 0)
            focus_mask None
            keysym None
            sensitive session.state == "active"

            at Transform(function=visual.animate_button, subpixel=True, xzoom=-1 if definition.get("mirrored", False) else 1)

            action Function(qte_ui_input, session, group, interaction, "click", _update_screens=False)

screen qte_pattern_control(session, group):
    $ link = group.hint_link()

    if link is not None:
        use qte_hint_line(link[0], link[1], group.definition.get("hint_line_ratio", 0.5), group.definition.get("hint_line_max_px", 180))

    for control index control.uid in group.active:
        use expression control.screen_name pass (session, group, control)
