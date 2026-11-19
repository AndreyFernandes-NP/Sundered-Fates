################################################################################
## QTE UI
##
## Just simply displays the active buttons and forwards their inputs to the manager
################################################################################

transform qte_approach(duration=1.0, base_scale=1.0):

    subpixel True
    alpha 0.0
    zoom (base_scale * 3)

    # this fucking thing took me an hour to complete it
    parallel:
        linear (duration * ((base_scale * 3) - (base_scale*0.75)) / ((base_scale * 3) - 0.01)) zoom (base_scale*0.75)
    
    parallel:
        linear min(0.2 + (duration / 10), 0.5) alpha 1.0

        time (duration * ((base_scale * 3) - (base_scale * 0.75)) / ((base_scale * 3) - 0.01))
        alpha 0.0

screen qte_single_screen(manager):
    modal True
    zorder 200

    on "show" action Function(manager.start)

    timer 0.01 repeat True action Function(manager.tick, _update_screens=False)

    key "game_menu" action NullAction()
    key "rollback" action NullAction()
    key "skip" action NullAction()
    key "toggle_skip" action NullAction()

    # This is our hint line that points towards the next button IF it's true
    if (manager.hint_line and manager.pattern in ("chain", "timed") and manager.active_buttons and manager.pending_buttons):
        use qte_hint_line(manager.active_buttons[-1], manager.pending_buttons[0], manager.hint_line_ratio, manager.hint_line_max_px)

    # Each button is its own screen bindable to this screen
    for btn index btn.uid in manager.active_buttons:
        use qte_button_screen(manager, btn)

screen qte_button_screen(manager, btn):
    $ button_size = max(1, int(256 * btn.scale * 3))

    fixed:
        pos (btn.xpos, btn.ypos)
        anchor (0.5, 0.5)

        xysize (button_size, button_size)

        add "images/testing/ui/zoom_circle.png" at qte_approach(btn.timeout, btn.scale):
            align (0.5, 0.5)

        python:
            if btn.timeout > 2:
                fade_duration = btn.timeout / 10
            else:
                fade_duration = 0.2
            
            fade_duration = min(fade_duration, 0.5)

        imagebutton:
            idle btn.image
            hover btn.image

            align (0.5, 0.5)
            focus_mask None
            keysym None

            at transform:
                zoom btn.scale
                alpha 0.0
                linear fade_duration alpha 1.0

            action Function(manager.click, btn.uid)

screen qte_hint_line(source, target, ratio=0.4, max_px=150):
    # Osu! like line between each button

    # This is the distance between curr and next button
    $ dx = target.xpos - source.xpos
    $ dy = target.ypos - source.ypos
    $ distance = math.hypot(dx, dy)

    if distance > 0:
        $ length = min(distance * ratio, max_px)
        $ angle = math.degrees(math.atan2(dy, dx))

        $ mid_x = source.xpos + (dx / distance) * (length / 2)
        $ mid_y = source.ypos + (dy / distance) * (length / 2)

        # Glow
        add "images/testing/ui/hint_line_glow.png":
            pos (absolute(mid_x), absolute(mid_y))
            anchor (0.5, 0.5)
            xysize (max(1, int(length)), 16)
            at Transform(
                rotate=angle,
                rotate_pad=False,
                alpha=0.4
            )
        
        # Line
        add "images/testing/ui/hint_line.png":
            pos (absolute(mid_x), absolute(mid_y))
            anchor (0.5, 0.5)
            xysize (max(1, int(length)), 4)
            at Transform(
                rotate=angle,
                rotate_pad=False,
                alpha=0.9
            )

# okay I pull up hop on after the party