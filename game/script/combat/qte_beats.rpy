################################################################################
## QTE BEATS
##
## You can use this to play animations through QTEs, visuals, effects and anything else
## from its results, pretty cool huh, don'tcha think?
################################################################################

init -10 python:
    import math
    from collections.abc import Mapping, Sequence

    def qte_build_sequence(beat_data):
        if not isinstance(beat_data, Mapping):
            raise ValueError("[QTE BEATS] Sequence data must be a dictionary, current: %r." % (beat_data))

        qte_data = beat_data.get("qte")

        if not isinstance(qte_data, Mapping):
            raise ValueError("[QTE BEATS] A sequence needs a 'qte' dictionary, got: %r." % (qte_data))

        definitions = qte_data.get("buttons", [])
        defaults = qte_data.get("button", {})

        if not isinstance(definitions, Sequence) or not definitions:
            raise ValueError("[QTE BEATS] 'buttons' must be a non-empty list, instead off: %r" % (definitions))

        if not isinstance(defaults, Mapping):
            raise ValueError("[QTE BEATS] 'button' defaults must be a dictionary, got: %r" % (defaults))

        threshold = float(qte_data.get("threshold", 1.0))

        if not math.isfinite(threshold) or not 0 < threshold <= 1:
            raise ValueError("[QTE BEATS] Threshold must be between 0 (exclusive) and 1.")

        shortcuts = {
            "prepare": "windup",
            "recover": "recoverup",
        }

        steps = []

        for index, definition in enumerate(definitions):
            if not isinstance(definition, Mapping):
                raise ValueError(f"[QTE BEATS] Button {index + 1} must be a dictionary.")

            # Copy the defaults so that anything related to the original is untouched
            button = defaults.copy()
            button.update(definition)

            anim_scale = button.pop("anim_scale", None)
            mirrored = button.pop("mirrored", None)

            # Mirrors the button xpos by default whenever mirrored is True
            # in any case just take it as an param and set it to false if you don't want the xpos mirrored
            button.setdefault("mirror_xpos", bool(mirrored))

            if anim_scale is not None:
                anim_scale = float(anim_scale)

                if not math.isfinite(anim_scale) or anim_scale <= 0:
                    raise ValueError("[QTE BEATS] anim_scale must be a finite number > 0, got: %r." % (anim_scale))

            visuals = {}

            for phase in ("recover", "prepare", "success", "failure"):
                base = beat_data.get(phase)

                if base is not None and not isinstance(base, Mapping):
                    raise ValueError(f"[QTE BEATS] '{phase}' must be a dictionary or None.")

                # Each action gets its own copy of the visual settings
                data = None if base is None else base.copy()

                explicit = phase in button
                button.pop(phase, None)

                if explicit:
                    for source in (defaults, definition):
                        if phase not in source:
                            continue

                        override = source[phase]

                        if override is None:
                            data = None

                        elif isinstance(override, Mapping):
                            data = {} if data is None else data
                            data.update(override)

                        else:
                            raise ValueError(f"[QTE BEATS] '{phase}' override must be a dictionary or None.")

                else:
                    shortcut = shortcuts.get(phase)

                    if shortcut is not None and (shortcut in button or shortcut in beat_data):
                        duration = float(button.get(shortcut, beat_data.get(shortcut)))

                        if not math.isfinite(duration) or duration < 0:
                            raise ValueError(f"[QTE BEATS] {shortcut} must be a finite number >= 0.")

                        if duration == 0:
                            data = None

                        elif data is None:
                            raise ValueError(f"[QTE BEATS] A positive {shortcut} needs a '{phase}' visual.")

                        else:
                            data["duration"] = duration

                if data is not None:
                    if anim_scale is not None:
                        data["scale"] = anim_scale
                    
                    if mirrored is not None:
                        data["mirrored"] = bool(mirrored)

                visuals[phase] = qte_build_visual(data)

            button.pop("windup", None)
            button.pop("recoverup", None)

            event = dict(qte_data)
            event.update(pattern="single", count=1, button=button, buttons=[])

            steps.append({"qte": event, "visuals": visuals})

        return steps, threshold

label combat_beat(beat_data):
    $ renpy.dynamic(beat_visuals=None, beat_result=None, beat_reaction=None, beat_predictions=None, _autosave=False)

    python:
        if not isinstance(beat_data, Mapping) or not isinstance(beat_data.get("qte"), Mapping):
            raise ValueError(f"[QTE BEATS] A combat beat needs at least a 'qte' as a dictionary, got {beat_data}")

        mirrored = beat_data.pop("mirrored", None)
        beat_visuals = {}

        for phase in ("recover", "prepare", "success", "failure"):
            base = beat_data.get(phase)

            if base is not None and not isinstance(base, Mapping):
                raise ValueError(f"[QTE BEATS] '{phase}' must be a dictionary or None.")

            data = None if base is None else base.copy()

            if data is not None and mirrored is not None:
                data["mirrored"] = bool(mirrored)

            beat_visuals[phase] = qte_build_visual(data)

        beat_predictions = [
            visual for visual in beat_visuals.values()
            if visual is not None
        ]
    
    $ renpy.stop_skipping()
    $ renpy.start_predict(*beat_predictions)
    $ renpy.pause(predict=True)

    call qte_beat_phase(beat_visuals["prepare"])
    call qte_session(beat_data["qte"])

    $ beat_result = _return
    $ beat_reaction = "success" if beat_result.success else "failure"

    call qte_beat_phase(beat_visuals[beat_reaction])
    call qte_beat_phase(beat_visuals["recover"])

    $ renpy.stop_predict(*beat_predictions)

    return beat_result

label combat_sequence(beat_data):
    python:
        renpy.dynamic(
            seq_steps=None, seq_threshold=None,
            seq_predictions=None, seq_results=None,
            seq_index=0, seq_step=None,
            seq_result=None, seq_reaction=None,
            seq_started=None, seq_summary=None,
            seq_hits=0, _autosave=False,
        )

    $ seq_steps, seq_threshold = qte_build_sequence(beat_data)
    $ seq_results = []

    python:
        seq_predictions = [visual for step in seq_steps for visual in step["visuals"].values() if visual is not None]

    $ renpy.stop_skipping()
    $ renpy.start_predict(*seq_predictions)
    $ renpy.pause(predict=True)

    $ seq_started = qte_now()

    while seq_index < len(seq_steps):
        $ seq_step = seq_steps[seq_index]

        # Both phases belong to the action that is about to start, so we need to execute them in order
        call qte_beat_phase(seq_step["visuals"]["recover"])
        call qte_beat_phase(seq_step["visuals"]["prepare"])

        call qte_session(seq_step["qte"])

        # Save this result before another call overwrites _return
        $ seq_result = _return
        $ seq_results.append(seq_result)

        $ seq_reaction = "success" if seq_result.success else "failure"

        call qte_beat_phase(seq_step["visuals"][seq_reaction])

        $ seq_index += 1

    $ renpy.stop_predict(*seq_predictions)

    python:
        seq_hits = sum(
            result.success for result in seq_results
        )

        seq_summary = QTEResult(
            grade=("good" if seq_hits == len(seq_results) else "bad" if seq_hits else "miss"),
            success=seq_hits >= math.ceil(len(seq_results) * seq_threshold),

            hits=seq_hits,
            misses=len(seq_results) - seq_hits,
            total=len(seq_results),
            results=list(seq_results),
            reason="completed",
            elapsed=qte_now() - seq_started,
        )

    return seq_summary

label qte_beat_phase(visual):
    if visual is None:
        return

    hide screen qte_combat_visual onlayer combat_visuals
    show screen qte_combat_visual(visual) onlayer combat_visuals

    call screen qte_beat_wait(visual.duration)

    return
