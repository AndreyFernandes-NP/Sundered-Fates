init -5 python:
    from decimal import Decimal, ROUND_CEILING

    def qte_pattern_count(step):
        buttons = step.get("buttons", [])

        qte_require(isinstance(buttons, builtins.list), "buttons must be a list, instead it is: %r" % type(buttons))

        fallback = (1 if step.get("pattern", "single") == "single" else 4)
        count = step.get("count", len(buttons) or fallback)

        qte_require(type(count) is int and count > 0, "count must be a positive integer")
        qte_require(len(buttons) <= count, "Buttons amount is greater than its count, like wtf? How did you do it?")

        return count

    def qte_required_hits(count, threshold):
        value = Decimal(str(threshold)) * count

        return int(value.to_integral_value(rounding=ROUND_CEILING))

    def qte_choose_boolean(value, option_name, randomize=False, choice_history=None):
        choice = qte_choice_info(value)

        if choice is not None:
            options = choice["options"]

            qte_require(all(type(option) is bool for option in options), option_name + " qte_choice options must all be booleans")

            index = qte_choice_index(choice, choice_history if choice_history is not None else {}, randomize)
            
            return options[index]

        if isinstance(value, (builtins.list, tuple)):
            qte_require(bool(value) and all(type(option) is bool for option in value), option_name + " must be a boolean or a non-empty list of booleans")

            return value[renpy.random.randrange(len(value))] if randomize else value[0]

        qte_require(type(value) is bool, option_name + " must be a boolean or a non-empty list of booleans")
        return value

    def qte_build_controls(step, randomize=False, choice_history=None):
        count = qte_pattern_count(step)
        points = qte_layout_points(step, count, randomize)
        overrides = step.get("buttons", [])
        pattern_name = step.get("pattern", "single")
        mirrored_option = step.get("mirrored", False)
        mirror_xpos_option = step.get("mirror_xpos")

        if (
            isinstance(mirrored_option, (builtins.list, tuple))
            or qte_choice_info(mirrored_option) is not None
            or isinstance(mirror_xpos_option, (builtins.list, tuple))
            or qte_choice_info(mirror_xpos_option) is not None
        ):
            qte_require(pattern_name in ("single", "chain", "timed"), "mirrored and mirror_xpos option lists or qte_choice are only supported by single, chain and timed patterns")

        if mirror_xpos_option is not None:
            qte_choose_boolean(mirror_xpos_option, "mirror_xpos", choice_history=choice_history)

        allowed = {
            "id", "kind", "source", "target",
            "duration", "params", "skin", "visual",
            "x", "y", "on_press", "on_miss",
        }

        controls = []

        for index in range(count):
            extra = (overrides[index] if index < len(overrides) else {})
            qte_require(isinstance(extra, builtins.dict) and set(extra) <= allowed, "Invalid fields in button dict; only on_press and on_miss hooks are supported there")
            mirrored = qte_choose_boolean(mirrored_option, "mirrored", randomize, choice_history)

            mirror_xpos = (mirrored if mirror_xpos_option is None else qte_choose_boolean(mirror_xpos_option, "mirror_xpos", randomize, choice_history))

            kind = extra.get("kind", step["kind"])
            params = (step.get("params", {}) if kind == step["kind"] else {})

            visual = dict(step.get("visual") or {})
            local_visual = extra.get("visual", {})

            qte_require(isinstance(local_visual, builtins.dict), "Button visual must be an object, instead of: %r" % (local_visual,))

            visual.update(local_visual)

            control = {
                "id": (step["id"] if count == 1 else "%s:%d" % (step["id"], index + 1)),
                "kind": kind,
                "source": step.get("source"),
                "target": step.get("target"),
                "duration": step.get("duration", 2.0),
                "params": dict(params),
                "skin": step.get("skin", "default"),
                "x": points[index][0],
                "y": points[index][1],
                "mirrored": mirrored,
                "mirror_xpos": mirror_xpos,
            }

            control.update(extra)
            control["on_press"] = qte_press_steps(extra.get("on_press", step.get("on_press")))
            control["on_miss"] = qte_miss_steps(extra.get("on_miss", step.get("on_miss")))

            if control["mirror_xpos"]:
                control["x"] = 1.0 - control["x"]

            control["visual"] = visual

            controls.append(control)
        
        return controls
    
    class QTEPattern:
        def __init__(self, definition):
            self.definition = definition
        
        @staticmethod
        def validate(definition, controls):
            pass

        def start(self, run):
            pass

        def update(self, run):
            pass
    
    class QTESinglePattern(QTEPattern):
        @staticmethod
        def validate(definition, controls):
            qte_require(len(controls) == 1, "single requires only one type of button")

        def start(self, run):
            run.spawn_next()
    
    class QTEBurstPattern(QTEPattern):
        @staticmethod
        def validate(definition, controls):
            duration = definition.get("duration", 2.0)

            qte_require(all(c["duration"] == duration for c in controls), "bursts controls must share the same duration value throughout the entire definition")
        
        def start(self, run):
            while run.has_pending:
                run.spawn_next()
        
    class QTEChainPattern(QTEPattern):
        def update(self, run):
            if not run.active:
                run.spawn_next()

    class QTETimedPattern(QTEPattern):
        def __init__(self, definition):
            super().__init__(definition)

            self.interval = definition.get("interval", 0.4)
            self.next_at = 0.0
        
        def update(self, run):
            if run.has_pending and run.elapsed >= self.next_at:
                run.spawn_next()

                self.next_at = run.elapsed + self.interval
    
    QTE_PATTERN_TYPES = {
        "single": QTESinglePattern,
        "burst": QTEBurstPattern,
        "chain": QTEChainPattern,
        "timed": QTETimedPattern,
    }

    def qte_validate_pattern(step, session):
        name = step.get("pattern", "single")

        qte_require(isinstance(name, str) and name in QTE_PATTERN_TYPES, "Unknown type of QTE pattern, received: " + name + ", use one of these: %r" % QTE_PATTERN_TYPES)

        threshold = step.get("threshold", 1.0)
        interval = step.get("interval", 0.4)

        qte_require(qte_number(threshold) and 0 < threshold <= 1, "threshold must be in between 0 and 1")
        qte_require(qte_number(interval) and interval > 0, "intervals must always be positive, received: %r" % (interval,))
        qte_require(type(step.get("hint_line", False)) is bool, "hint_line must be a boolean, 'true' or 'false'")

        ratio = step.get("hint_line_ratio", 0.5)
        pixels = step.get("hint_line_max_px", 180)

        qte_require(qte_number(ratio) and 0 < ratio <= 1, "Invalid hint line ratio, be sure it's between 0 and 1 and not 0, got: %r" % (ratio,))
        qte_require(qte_number(pixels) and pixels > 0, "Invalid hint line length, should always be a positive value, received: %r" % (pixels,))

        controls = qte_build_controls(step)

        for control in controls:
            qte_validate_control(control, session)

        qte_require(len({c["id"] for c in controls}) == len(controls), "Duplicated IDs present, check any of your calls for the same id, got: %r" % controls)

        QTE_PATTERN_TYPES[name].validate(step, controls)

    class QTEPatternRun:
        """
        Owns controls and results from any pattern call,
        it's what makes everything mostly work and coordinate together
        """

        screen_name = "qte_pattern_control"

        def __init__(self, definition, event_data=None, button_history=None, choice_history=None):
            self.definition = definition
            self.pattern_name = definition.get("pattern", "single")
            self.event_data = ({} if event_data is None else event_data)
            self.button_history = ([] if button_history is None else button_history)
            self.choice_history = ({} if choice_history is None else choice_history)

            self.elapsed = 0.0
            self.result = None

            self.active = []
            self.controls = []
            self.next_index = 0

            self._view_revision = 0
            self._input = None
            self.events = []

            definitions = qte_build_controls(definition, randomize=True, choice_history=self.choice_history)

            for uid, data in enumerate(definitions):
                control = QTE_INPUT_TYPES[data["kind"]](data)

                control.uid = uid
                self.controls.append(control)

            self.results = [None] * len(self.controls)

            self.required_hits = qte_required_hits(len(self.controls), definition.get("threshold", 1.0))

            self.pattern = QTE_PATTERN_TYPES[self.pattern_name](definition)
            self.pattern.start(self)

        @property
        def has_pending(self):
            return self.next_index < len(self.controls)

        @property
        def view_revision(self):
            return (self._view_revision, tuple((control.uid, control.view_revision) for control in self.active))

        @property
        def mirrored(self):
            return (False if not self.active else self.active[-1].definition["mirrored"])

        def spawn_next(self):
            if not self.has_pending:
                return None

            control = self.controls[self.next_index]
            self.next_index += 1

            self.active.append(control)
            self.button_history.append({
                "uid": control.uid,
                "id": control.definition["id"],
                "order": len(self.button_history) + 1,
                "x": control.definition["x"],
                "y": control.definition["y"],
                "mirrored": control.definition["mirrored"],
                "mirror_xpos": control.definition["mirror_xpos"],
                "appeared_at": self.elapsed,
                "success": None,
                "grade": None,
                "reason": None,
                "elapsed": None,
                "result": None,
            })
            self._view_revision += 1

            return control

        def drain_events(self):
            events = self.events
            self.events = []

            return events

        def input(self, packet):
            # Compatibility for callers that only sends an input name.
            if isinstance(packet, str):
                qte_require(len(self.active) == 1, "Input needs a control UID, please set one like 'parry' or 'random_attack' idk")

                packet = {
                    "uid": self.active[0].uid,
                    "name": packet,
                    "data": {},
                }

            qte_require(isinstance(packet, builtins.dict), "Invalid input packet, received: %r" % (packet,))

            self._input = packet

        def update(self, dt):
            if self.result is not None:
                return

            qte_require(qte_number(dt) and dt >= 0, "Invalid pattern delta time, should be a positive number")

            self.elapsed += dt
            packet, self._input = self._input, None

            # Only controls that's already active receives this update's elapsed time.
            for control in list(self.active):
                if (control.result is None and packet is not None and packet.get("uid") == control.uid):
                    accepted = control.input(packet["name"], **packet.get("data", {}))

                    if accepted and control.definition.get("on_press"):
                        self.events.append({
                            "name": "press",
                            "definition": control.definition,
                            "result": None,
                            "uid": control.uid,
                        })

                if control.result is None:
                    control.update(dt)

                if control.result is not None:
                    history_entry = self.button_history[control.uid]
                    history_entry.update(control.result)
                    history_entry["result"] = dict(control.result)

                    if not control.result["success"] and control.definition.get("on_miss"):
                        self.events.append({
                            "name": "miss",
                            "definition": control.definition,
                            "result": control.result,
                            "uid": control.uid,
                        })

                    self.results[control.uid] = dict(control.result, uid=control.uid)

                    self.active.remove(control)
                    self._view_revision += 1

            self.pattern.update(self)

            if not self.active and not self.has_pending:
                self.finish()

        def finish(self):
            total = len(self.controls)
            hits = sum(result["success"] for result in self.results)

            success = hits >= self.required_hits

            grade = ("good" if hits == total else "bad" if hits else "miss")

            reason = ("threshold_met" if success else "threshold_not_met")

            if self.pattern_name == "single":
                grade = self.results[0]["grade"]
                reason = self.results[0]["reason"]

            self.result = {
                "action": self.definition["id"],
                "source": self.definition.get("source"),
                "target": self.definition.get("target"),

                "pattern": self.pattern_name,
                "success": success,
                "grade": grade,
                "reason": reason,
                "elapsed": self.elapsed,

                "hits": hits,
                "misses": total - hits,
                "total": total,
                "required_hits": self.required_hits,

                "results": [
                    dict(result)
                    for result in self.results
                ],
                "button_history": [dict(entry) for entry in self.button_history],
                "data": dict(self.event_data),
            }

        def hint_link(self):
            if (self.definition.get("hint_line", False) and self.pattern_name in ("chain", "timed") and self.active and self.has_pending):

                return (self.active[-1].definition, self.controls[self.next_index].definition)

            return None
