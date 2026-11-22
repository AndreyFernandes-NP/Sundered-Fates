init -10 python:
    QTE_VIEWS = globals().get("QTE_VIEWS", {})

    QTE_STAGE_DEFAULTS = {
        "player": {
            "x": 0.5,
            "y": 0.5,
            "zorder": 100,
            "follow_mirror": False,
        }
    }

    class QTEStage:
        def __init__(self, session):
            self.session = session
            self.slots = {}

            self.revision = 0
            self.serial = 0

        def clip_for(self, actor_id, pose, duration=None, scale=None):
            actor = self.session.actor(actor_id)

            character_id = (actor.character_id or actor.actor_id)
            poses = QTE_VIEWS.get(character_id, {})
            source = poses.get(pose)

            if source is None:
                qte_require(
                    "/" in pose or posixpath.splitext(pose)[1] or renpy.has_image(pose, exact=True),
                    f"Unknown pose '{pose}' for character '{character_id}'. "
                    f"Registered characters: {sorted(QTE_VIEWS)}; available poses: {sorted(poses)}",
                )
                
                source = pose

            clip = qte_resolve_clip(source, duration)

            if scale is not None:
                qte_require(qte_number(scale) and scale > 0, "scale must be a positive number")
                clip["scale"] = scale

            return clip
    
        def display_for(self, step, old=None):
            """Resolve the defaults and overrides for any existing actor in a stage"""
            display = {
                "x": 0.5,
                "y": 0.3,
                "zorder": 0,
                "follow_mirror": True,
            }

            display.update(QTE_STAGE_DEFAULTS.get(step["actor"], {}))

            for key in ("x", "y", "zorder", "follow_mirror"):
                # If an actor that's already present keep its current visuals
                if old is not None:
                    display[key] = old.get(key, display[key])
                
                if key in step:
                    display[key] = step[key]
                
            for key in ("x", "y"):
                value = display[key]

                qte_require(qte_number(value) and 0 <= value <= 1, key + " must be between 0 and 1")

                display[key] = float(value)
            
            qte_require(type(display["zorder"]) is int, "zorder must be an integer")
            qte_require(type(display["follow_mirror"]) is bool, "follow_mirror must be either 'True' or 'False'")

            return display

        def draw_order(self):
            """Returns actors ordered from back to front"""

            return sorted(self.slots.items(), key=lambda item: item[1].get("zorder", 0))

        def validate(self, step):
            self.display_for(step, self.slots.get(step["actor"]))
            clip = self.clip_for(step["actor"], step["pose"], step.get("duration"), step.get("scale"))

            if step["op"] == "play":
                qte_require(type(step.get("wait", True)) is bool, "play.wait must be boolean")

                after = step.get("then")
                then_duration = step.get("then_duration")

                if then_duration is not None:
                    qte_require(after is not None, "then_duration requires a then pose")
                    qte_require(qte_number(then_duration) and then_duration > 0, "then_duration must be a positive number")

                if after is not None:
                    qte_require(isinstance(after, str) and bool(after.strip()), "Invalid next pose")
                    self.clip_for(step["actor"], after, then_duration)

                if step.get("wait", True) or after is not None:
                    qte_require(clip["duration"] is not None and not clip["loop"], "You can't use Wait during a loop, the clip must have a set duration")

            return clip

        def apply(self, step):
            clip = self.validate(step)

            actor_id = step["actor"]
            old = self.slots.get(actor_id)

            display = self.display_for(step, old)

            if (step["op"] == "show" and old is not None and old["pose"] == step["pose"] and old["playback"].clip == clip):
                changed = any(old.get(key) != value for key, value in display.items())

                if changed:
                    old.update(display)
                    self.revision += 1

                return old["playback"]

            playback = QTEPlayback(clip)

            if old is not None and not old["playback"].done:
                old["playback"].cancelled = True

            self.serial += 1

            slot = {
                "pose": step["pose"],
                "playback": playback,
                "serial": self.serial,
                "then": step.get("then"),
                "then_duration": step.get("then_duration"),
            }

            slot.update(display)

            self.slots[actor_id] = slot
            self.revision += 1

            return playback

        def update(self, dt):
            for actor_id, slot in list(self.slots.items()):
                playback = slot["playback"]

                was_done = playback.done
                playback.update(dt)

                if (not was_done and playback.done and slot["then"] is not None):
                    self.apply({
                        "op": "play",
                        "actor": actor_id,
                        "pose": slot["then"],
                        "wait": False,
                        "duration": slot["then_duration"],
                        "x": slot["x"],
                        "y": slot["y"],
                    })
