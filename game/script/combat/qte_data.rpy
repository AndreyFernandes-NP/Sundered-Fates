init -20 python:
    import builtins
    import math
    import json
    import copy

    QTE_CHOICE_SERIAL = 0

    def qte_script(*steps):
        return {
            "version": 1,
            "steps": list(steps),
        }
    
    def qte_show(actor, pose, x=None, y=None, zorder=None, follow_mirror=None, scale=None, sfx=None, effect=None):
        step = {
            "op": "show",
            "actor": actor,
            "pose": pose,
        }

        for key, value in (("x", x), ("y", y), ("zorder", zorder), ("follow_mirror", follow_mirror), ("scale", scale), ("sfx", sfx), ("effect", effect)):
            if value is not None:
                step[key] = value

        return step
    
    def qte_play(actor, pose, wait=True, then=None, duration=None, x=None, y=None, zorder=None, follow_mirror=None, scale=None, then_duration=None, sfx=None, effect=None):
        step = {
            "op": "play",
            "actor": actor,
            "pose": pose,
            "wait": wait,
            "then": then,
        }

        for key, value in (("duration", duration), ("x", x), ("y", y), ("zorder", zorder), ("follow_mirror", follow_mirror), ("scale", scale), 
        ("then_duration", then_duration), ("sfx", sfx), ("effect", effect)):
            if value is not None:
                step[key] = value

        return step

    def qte_wait(duration):
        return {"op": "wait", "duration": duration}
    
    def qte_say(who=None, what=None):
        step = {"op": "say"}

        if who is not None:
            step["who"] = who

        if what is not None:
            step["what"] = what

        return step

    def qte_sfx(source, channel="sound", volume=1.0, fadein=0.0, fadeout=0.0):
        return {
            "op": "sfx",
            "source": source,
            "channel": channel,
            "volume": volume,
            "fadein": fadein,
            "fadeout": fadeout,
        }
    
    def qte_effect(name, layers=("master", "qte_scene"), always=False):
        return {
            "op": "effect",
            "name": name,
            "layers": layers,
            "always": always,
        }

    def qte_history(index=-1, field=None, default=None):
        return {
            "$qte_ref": "history",
            "index": index,
            "field": field,
            "default": default,
        }

    def qte_ev_data(key, default=None):
        return {
            "$qte_ref": "event_data",
            "key": key,
            "default": default,
        }

    def qte_set_ev_data(key, value):
        return {
            "op": "data_set",
            "key": key,
            "value": value,
        }

    def qte_choice(options, mode="random", first="random", last=1, key=None):
        global QTE_CHOICE_SERIAL

        allowed_modes = {"random", "alternate", "avoid_last"}

        qte_require(isinstance(options, (builtins.list, tuple)) and bool(options), "qte_choice options must be a non-empty list")
        qte_require(isinstance(mode, str) and mode in allowed_modes, "Unknown qte_choice mode: %r, select one of %r" % (mode, allowed_modes,))
        qte_require(type(last) is int and last > 0, "qte_choice last must be a positive integer")
        qte_require(first in ("random", "first"), "qte_choice first must be 'random' or 'first'")

        if mode == "avoid_last":
            qte_require(len(options) > last, "avoid_last needs more options than its last window")

        if mode == "alternate":
            qte_require(len(options) > 1, "alternate needs at least two options")

        if key is None:
            QTE_CHOICE_SERIAL += 1
            key = "choice:%d" % QTE_CHOICE_SERIAL

        qte_require(isinstance(key, str) and bool(key.strip()), "qte_choice key must be a non-empty string")

        return {
            "$qte_choice": True,
            "key": key,
            "options": list(options),
            "mode": mode,
            "last": last,
            "first": first,
        }

    def qte_choice_info(value):
        allowed_modes = {"random", "alternate", "avoid_last"}

        if not isinstance(value, builtins.dict) or "$qte_choice" not in value:
            return None

        qte_require(set(value) == {"$qte_choice", "key", "options", "mode", "last", "first"} and value["$qte_choice"] is True,
            "Invalid qte_choice descriptor")

        options = value["options"]
        mode = value["mode"]

        qte_require(isinstance(options, builtins.list) and bool(options), "qte_choice options must be a non-empty list")
        qte_require(isinstance(value["key"], str) and bool(value["key"].strip()), "qte_choice key must be a non-empty string")
        qte_require(isinstance(mode, str) and mode in allowed_modes, "Unknown qte_choice mode: %r, select one of %r" % (mode, allowed_modes,))
        qte_require(type(value["last"]) is int and value["last"] > 0, "qte_choice last must be a positive integer")
        qte_require(value["first"] in ("random", "first"), "qte_choice first must be 'random' or 'first'")

        if mode == "avoid_last":
            qte_require(len(options) > value["last"], "avoid_last needs more options than its last window")

        if mode == "alternate":
            qte_require(len(options) > 1, "alternate needs at least two options")

        return value

    def qte_choice_index(descriptor, history, choose=True):
        descriptor = qte_choice_info(descriptor)

        if not choose:
            return 0

        key = descriptor["key"]
        options = descriptor["options"]
        mode = descriptor["mode"]
        previous = history.get(key, [])

        if not previous:
            selected = renpy.random.randrange(len(options)) if descriptor["first"] == "random" else 0

        elif mode == "alternate":
            selected = (previous[-1] + 1) % len(options)

        elif mode == "avoid_last":
            excluded = set(previous[-descriptor["last"]:])
            candidates = [index for index in range(len(options)) if index not in excluded]
            selected = candidates[renpy.random.randrange(len(candidates))]

        else:
            selected = renpy.random.randrange(len(options))

        if mode == "avoid_last":
            history[key] = (previous + [selected])[-descriptor["last"]:]

        else:
            history[key] = [selected]

        return selected

    def qte_end(outcome):
        return {"op": "end", "outcome": outcome}

    def qte_step_list(steps):
        return [steps] if isinstance(steps, builtins.dict) else list(steps)
    
    def qte_branch(success=(), failure=()):
        return {
            "op": "branch",
            "success": qte_step_list(success),
            "failure": qte_step_list(failure),
        }
    
    def qte_action(kind, action_id, source=None, target=None, duration=2.0, who=None, what=None, x=0.5, y=0.6,
                    on_press=None, on_miss=None, on_start=(), on_success=(), on_failure=(), on_end=(),
                    params=None, skin="default", visual=None, pattern="single", count=None, 
                    buttons=None, threshold=1.0, interval=0.4, layout="grid", spread=(0.6, 0.4), 
                    hint_line=False, hint_line_ratio=0.5, hint_line_max_px=180, mirrored=False, mirror_xpos=None, mirror=None):
        step = {
            "op": "qte",
            "kind": kind,
            "id": action_id,
            "params": dict(params or {}),
            "skin": skin,
            "visual": dict(visual or {}),
            "source": source,
            "target": target,
            "duration": duration,
            "who": who,
            "what": what,
            "x": x,
            "y": y,
            "on_press": qte_press_steps(on_press),
            "on_miss": qte_miss_steps(on_miss),
            "on_start": qte_step_list(on_start),
            "on_success": qte_step_list(on_success),
            "on_failure": qte_step_list(on_failure),
            "on_end": qte_step_list(on_end),
            "pattern": pattern,
            "buttons": list(buttons or ()),
            "threshold": threshold,
            "interval": interval,
            "layout": layout,
            "spread": list(spread),
            "hint_line": hint_line,
            "hint_line_ratio": hint_line_ratio,
            "hint_line_max_px": hint_line_max_px,
            "mirrored": mirrored,
            "mirror_xpos": mirror_xpos,
            "mirror": mirror,
        }

        if count is not None:
            step["count"] = count

        return step

    def qte_button(x=None, y=None, **options):
        button = dict(options)

        if x is not None:
            button["x"] = x

        if y is not None:
            button["y"] = y

        return button

    def qte_click(action_id, **options):
        return qte_action("click", action_id, **options)

    def qte_single(action_id, kind="click", **options):
        return qte_action(kind, action_id, pattern="single", **options)

    def qte_burst(action_id, kind="click", **options):
        return qte_action(kind, action_id, pattern="burst", **options)

    def qte_chain(action_id, kind="click", **options):
        return qte_action(kind, action_id, pattern="chain", **options)

    def qte_timed(action_id, kind="click", **options):
        return qte_action(kind, action_id, pattern="timed", **options)

    def qte_require(condition, message):
        if not condition:
            raise ValueError("[QTE DATA] " + message)
        
    def qte_number(value):
        return (type(value) in (int, float) and math.isfinite(value))

    def qte_prepare(script, session):
        if isinstance(script, str):
            with renpy.open_file(script, encoding="utf-8") as file:
                script = json.load(file)
        
        ## Both paths must produce a valid JSON-compatible definitions
        script = json.loads(json.dumps(script, allow_nan=False))

        qte_require(isinstance(script, builtins.dict), "Script must be a valid JSON object")
        qte_require(set(script) == {"version", "steps"}, "Expected 'version' and 'steps' in script")
        qte_require(type(script["version"]) is int and script["version"] == 1, "Unsupported combat scene script version")

        qte_validate_steps(script["steps"], session)

        return script

    def qte_resolve_event_refs(value, session=None, validation=False):
        if isinstance(value, builtins.dict):
            if "$qte_ref" in value:
                reference = value["$qte_ref"]
                default = value.get("default")

                if reference == "button_history":
                    qte_require(
                        set(value) == {"$qte_ref", "index", "field", "default"}
                        and type(value["index"]) is int
                        and (value["field"] is None or isinstance(value["field"], str)),
                        "Invalid qte_history reference",
                    )

                    if validation:
                        return qte_resolve_event_refs(default, session, True)

                    history = session.qte.button_history
                    index = value["index"]

                    if -len(history) <= index < len(history):
                        entry = history[index]
                        field = value["field"]

                        if field is None:
                            return copy.deepcopy(entry)

                        return copy.deepcopy(entry.get(field, default))

                    return copy.deepcopy(default)

                if reference == "event_data":
                    qte_require(set(value) == {"$qte_ref", "key", "default"} and isinstance(value["key"], str) and bool(value["key"].strip()), "Invalid qte_ev_data reference")

                    if validation:
                        return qte_resolve_event_refs(default, session, True)

                    return copy.deepcopy(session.qte.event_data.get(value["key"], default))

                raise ValueError("[QTE DATA] Unknown event data reference: %r" % (reference,))

            return {key: qte_resolve_event_refs(item, session, validation) for key, item in value.items()}

        if isinstance(value, (builtins.list, tuple)):
            return [qte_resolve_event_refs(item, session, validation) for item in value]

        return value

    def qte_reaction_steps(value, hook_name):
        if value is None:
            return []

        if isinstance(value, builtins.dict):
            value = [value]

        qte_require(isinstance(value, (builtins.list, tuple)), hook_name + " must be a show/play/sfx/effect instruction, a list, or None, received: %r" % (value,))

        steps = []

        for entry in value:
            qte_require(isinstance(entry, builtins.dict) and entry.get("op") in ("show", "play", "sfx", "effect", "data_set"),
                        hook_name + " only accepts show, play, sfx, effect and event data updates, not %r" % (entry,))

            step = dict(entry)

            if step["op"] == "play":
                qte_require(type(step.get("wait", True)) is bool, "play.wait must be a boolean")

                # Visual reactions should never block the current QTE
                step["wait"] = False

            steps.append(step)

        return steps

    def qte_press_steps(value):
        return qte_reaction_steps(value, "on_press")

    def qte_miss_steps(value):
        return qte_reaction_steps(value, "on_miss")

    def qte_validate_steps(steps, session):
        qte_require(isinstance(steps, builtins.list), "Steps must be a valid list")

        schemas = {
            "show": (
                {"op", "actor", "pose"},
                {"x", "y", "zorder", "follow_mirror", "scale", "sfx", "effect"},
            ),

            "play": (
                {"op", "actor", "pose"},
                {"wait", "then", "duration", "then_duration", "x", "y", "zorder", "follow_mirror", "scale", "sfx", "effect"},
            ),

            "sfx": (
                {"op", "source"},
                {"channel", "volume", "fadein", "fadeout"},
            ),

            "effect": (
                {"op", "name"},
                {"layers", "always"},
            ),

            "data_set": (
                {"op", "key", "value"},
                set(),
            ),

            "wait": (
                {"op", "duration"},
                set()
            ),

            "say": (
                {"op"},
                {"who", "what"},
            ),

            "end": (
                {"op", "outcome"},
                set(),
            ),

            "branch": (
                {"op", "success", "failure"},
                set(),
            ),

            "qte": (
                {"op", "kind", "id"},
                {
                    "source", "target", "duration", "who", "what",
                    "x", "y", "params", "skin", "visual",
                    "pattern", "count", "buttons", "threshold",
                    "interval", "layout", "spread", "hint_line",
                    "hint_line_ratio", "hint_line_max_px",
                    "mirrored", "mirror_xpos", "mirror", "on_press", "on_miss",
                    "on_start", "on_success", "on_failure", "on_end",
                },
            ),
        }

        for raw_step in steps:
            step = qte_resolve_event_refs(raw_step, session, validation=True)
            qte_require(isinstance(step, builtins.dict), "Every step must be an object, got: %r" % (step,))

            op = step.get("op")

            qte_require(isinstance(op, str) and op in schemas, "Unknown step: " + repr(op))

            required, optional = schemas[op]

            qte_require(required <= set(step) <= required | optional, "Missing or unknown fields in " + repr(step.get("id")) + "\n Available fields: %r" % (schemas[op],))

            for key in ("x", "y"):
                if key in step:
                    value = step[key]
                    
                    qte_require(qte_number(value) and 0 <= value <= 1, key + " must be a relative coordinate from 0 to 1")
            
            match op:
            
                case "show" | "play":
                    qte_require(isinstance(step["actor"], str) and isinstance(step["pose"], str), "Actor and pose must be strings")
                
                    session.stage.validate(step)
                    session.audio.validate(step.get("sfx"))
                    session.effects.validate(step.get("effect"))
            
                case "sfx":
                    session.audio.validate(step)
                
                case "effect":
                    session.effects.validate(step)

                case "data_set":
                    qte_require(isinstance(step["key"], str) and bool(step["key"].strip()), "Event data key must be a non-empty string")
            
                case "wait":
                    qte_require(qte_number(step["duration"]) and step["duration"] > 0, "Wait duration must be a positive number")
            
                case "say":
                    for key in ("who", "what"):
                        if key in step:
                            value = step[key]
                            qte_require(isinstance(value, str) and bool(value.strip()), f"Expected non-empty text for '{key}'")

                case "end":
                    value = step["outcome"]
                    qte_require(isinstance(value, str) and bool(value.strip()), "Outcome shouldn't be an empty value")
            
                case "branch":
                    qte_validate_steps(step["success"], session)
                    qte_validate_steps(step["failure"], session)
            
                case "qte":
                    qte_validate_control(step, session)
                    qte_validate_pattern(step, session)

                    for key in ("who", "what"):
                        value = step.get(key)

                        qte_require(value is None or isinstance(value, str), f"'{key}' must be a string or None")

                    for hook in ("on_start", "on_success", "on_failure", "on_end"):
                        qte_validate_steps(step.get(hook, []), session)
    
    def qte_validate_control(control, session):
        qte_require(isinstance(control["id"], str) and bool(control["id"].strip()), "Invalid control ID, got: %r" % (control["id"],))

        kind = control["kind"]

        qte_require(isinstance(kind, str) and kind in QTE_INPUT_TYPES,  f"Unknown interaction type {kind}, use one of: {repr(QTE_INPUT_TYPES)}")

        params = control.get("params", {})

        qte_require(isinstance(params, builtins.dict), "params must be an object, not %r" % type(params))

        QTE_INPUT_TYPES[kind].validate(params)

        qte_skin(control.get("skin", "default"), control.get("visual"))

        duration = control.get("duration", 2.0)

        qte_require(qte_number(duration) and duration > 0, "Duration must be positive")

        for key, fallback in (("x", 0.5), ("y", 0.6)):
            value = control.get(key, fallback)

            qte_require(qte_number(value) and 0 <= value <= 1, key + " must be from 0 to 1")

        def validate_boolean_option(value, option_name):
            choice = qte_choice_info(value)

            if choice is not None:
                options = choice["options"]
            elif isinstance(value, (builtins.list, tuple)):
                options = value
            else:
                qte_require(type(value) is bool, option_name + " must be a boolean, a boolean list, or qte_choice")
                return

            qte_require(
                bool(options) and all(type(option) is bool for option in options),
                option_name + " options must be a non-empty list of booleans",
            )

        mirrored = control.get("mirrored", False)
        mirror_xpos = control.get("mirror_xpos")

        validate_boolean_option(mirrored, "mirrored")

        if mirror_xpos is not None:
            validate_boolean_option(mirror_xpos, "mirror_xpos")

        mirror = control.get("mirror")

        if mirror is not None:
            mirror_actors = [mirror] if isinstance(mirror, str) else mirror
            qte_require(isinstance(mirror_actors, (builtins.list, tuple)), "mirror must be an actor ID or a list of actor IDs")

            for actor_id in mirror_actors:
                qte_require(isinstance(actor_id, str) and bool(actor_id.strip()), "mirror actor IDs must be non-empty strings")
                session.actor(actor_id)

        for key in ("source", "target"):
            if control.get(key) is not None:
                qte_require(isinstance(control[key], str), "Actor ID must be a string, got: %r" % type(control[key]))

                session.actor(control[key])
        
        qte_validate_steps(qte_press_steps(control.get("on_press")), session)
        qte_validate_steps(qte_miss_steps(control.get("on_miss")), session)
