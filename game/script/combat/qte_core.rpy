init -10 python:
    import math
    import time

    def qte_now():
        """
        Returns a continual monotonic clock

        Used to be renpy's internal time, but had to
        be adjusted so some optimization could work.
        """

        return time.monotonic()

    class QTEManager:

        def __init__(self, event_data):
            self.pattern = event_data.get("pattern", "single")

            if self.pattern not in ("single", "burst", "chain", "timed"):
                raise ValueError(f"[QTE CORE] Unknown pattern '{self.pattern}' in event data.")
            
            self.timeout = float(event_data.get("timeout", 1.0 if self.pattern == "single" else 2.0))
            self.spawn_interval = float(event_data.get("spawn_interval", 0.4))
            self.threshold = float(event_data.get("threshold", 1.0))

            for name, value in (("timeout", self.timeout), ("spawn_interval", self.spawn_interval)):
                if not math.isfinite(value) or value <= 0:
                    raise ValueError(f"[QTE CORE] {name} must be a positive number, got {value}.")
            
            if not math.isfinite(self.threshold) or not 0 < self.threshold <= 1:
                raise ValueError("[QTE CORE] Threshold must be between 0 (exclusive) and 1 (inclusive).")
            
            self.hint_line = bool(event_data.get("hint_line", False))
            self.hint_line_ratio = float(event_data.get("hint_line_ratio", 0.5))
            self.hint_line_max_px = float(event_data.get("hint_line_max_px", 180))

            if not 0 < self.hint_line_ratio <= 1:
                raise ValueError("[QTE CORE] hint_line_ratio must be between 0 and 1.")

            if not math.isfinite(self.hint_line_max_px) or self.hint_line_max_px <= 0:
                raise ValueError("[QTE CORE] hint_line_max_px must be positive.")
            
            self.buttons = self._build_buttons(event_data)
            self.required_hits = math.ceil(len(self.buttons) * self.threshold)

            self.pending_buttons = list(self.buttons)
            self.active_buttons = []
            self.results = []

            self.started = False
            self.finished = False

            self.started_at = None
            self.finished_at = None
            self.next_spawn_at = None

            self.result = None

        def _build_buttons(self, event_data):
            defaults = dict(event_data.get("button", {}))
            definitions = list(event_data.get("buttons", []))

            count = event_data.get("count", len(definitions) or 1)

            if (not isinstance(count, int) or isinstance(count, bool) or count < 1):
                raise ValueError(f"[QTE CORE] count must be a positive integer, got {count}.")
            
            if len(definitions) > count:
                raise ValueError(f"[QTE CORE] More button definitions ({len(definitions)}) than count ({count}).")

            if self.pattern == "single" and count != 1:
                raise ValueError(f"[QTE CORE] Single pattern must have count=1, got {count}.")
            
            box = event_data.get("random_box", (96, 96, config.screen_width - 96, config.screen_height - 96))

            if (len(box) != 4 or not all(isinstance(x, (int, float)) for x in box)):
                raise ValueError(f"[QTE CORE] random_box must be a tuple of 4 numbers, got {box}.")
            
            x1, y1, x2, y2 = box

            if x1 > x2 or y1 > y2:
                raise ValueError(f"[QTE CORE] random_box must have x1 <= x2 and y1 <= y2, got {box}.")
            
            built = []

            for index in range(count):
                data = dict(defaults)
            
                if index < len(definitions):
                    data.update(definitions[index])
                
                button_type = data.pop("type", "click")
                button_class = QTE_BUTTON_TYPES.get(button_type)

                if button_class is None:
                    raise ValueError(f"[QTE CORE] Unknown button type '{button_type}' in event data.")
                
                data.setdefault("image", "qte test button")
                data.setdefault("timeout", self.timeout)

                # So that every 'burst' button shares the same timeout
                if self.pattern == "burst":
                    data["timeout"] = self.timeout
                
                if data.get("xpos") is None:
                    data["xpos"] = renpy.random.randint(x1, x2)
                
                if data.get("ypos") is None:
                    data["ypos"] = renpy.random.randint(y1, y2)
                
                if data.pop("mirror_xpos", False):
                    data["xpos"] = config.screen_width - data["xpos"]
                
                button = button_class(**data)
                button.uid = len(built)  # Assign a unique ID based on the order of creation

                built.append(button)

            return built

        def start(self):
            if self.started:
                return

            now = qte_now()

            self.started = True
            self.started_at = now

            match self.pattern:
                
                case "burst":
                    while self.pending_buttons:
                        self.spawn_next(now)
                
                case _:
                    self.spawn_next(now)
            
            self.next_spawn_at = now + self.spawn_interval

        def spawn_next(self, now=None):
            if self.finished or not self.pending_buttons:
                return

            now = qte_now() if now is None else now

            btn = self.pending_buttons.pop(0)
            btn.start(now)

            self.active_buttons.append(btn)

        def update(self):
            """
            Called by the screen timer.
            Always returns QTEResult if finished,
            otherwise, returns None.
            """
            if self.finished:
                return self.result
                
            if not self.started:
                self.start()

            now = qte_now()

            for btn in list(self.active_buttons):
                if btn.expired(now):
                    result = self.miss(btn.uid)

                    if result is not None:
                        return result
            
            match self.pattern:
                
                case "timed":
                    if self.pending_buttons:
                        if now >= self.next_spawn_at:
                            self.spawn_next(now)
                            self.next_spawn_at = now + self.spawn_interval
                         
            self.check_finished()

            return self.result

        def tick(self):
            """
            Updates the QTE state without always refreshing the entire screen binded to it.
            """

            # Save all currently visible buttons
            previous = tuple(btn.uid for btn in self.active_buttons)

            result = self.update()

            # If it's already finished then it'll end the interaction
            if result is not None:
                return result

            current = tuple(btn.uid for btn in self.active_buttons)

            if previous != current:
                renpy.restart_interaction()
            
            return None
    
        def handle_input(self, uid, input_name, **data):
            # Update the QTE state based on the input received before forwarding another input to the button itself.
            result = self.update()

            if result is not None:
                return result
            
            btn = self.get_active_button(uid)

            if btn is None:
                return None

            now = qte_now()

            # If the button has expired, we treat it as a miss and return the result.
            if btn.expired(now):
                return self.miss(uid)

            result = btn.handle_input(input_name, now=now, **data)

            if result is None:
                return None

            return self.record_result(btn, result)

        def click(self, uid):
            return self.handle_input(uid, "click")

        def record_result(self, btn, result):
            # A button that has been hit or missed is no longer active, don't need to count it twice
            if btn not in self.active_buttons:
                return None

            self.active_buttons.remove(btn)
            self.results.append(result)

            if self.pattern == "chain":
                self.spawn_next()
            
            self.check_finished()

            return self.result

        def miss(self, uid):
            if self.finished:
                return self.result

            btn = self.get_active_button(uid)

            if btn is None:
                return None

            result = QTEResult(
                grade="miss",
                given_input=btn.given_input,
                hits=0,
                misses=1,
                total=1,
                reason="timeout",
                elapsed=btn.timeout,
            )

            return self.record_result(btn, result)

        def get_active_button(self, uid):
            for btn in self.active_buttons:
                if btn.uid == uid:
                    return btn

            return None

        def check_finished(self):
            if not self.pending_buttons and not self.active_buttons:
                self.finish()

        def finish(self):
            if self.finished:
                return

            self.finished = True
            self.finished_at = qte_now()
            self.result = self.final_result()

        def final_result(self):
            if self.result is not None:
                return self.result
            
            if self.pattern == "single":
                return self.results[0]

            total = len(self.buttons)
            hits = sum(r.success for r in self.results)
            success = hits >= self.required_hits

            if hits == total:
                grade = "good"

            elif hits > 0:
                grade = "bad"

            else:
                grade = "miss"

            return QTEResult(
                grade=grade,
                success=success,
                hits=hits,
                misses=total - hits,
                total=total,
                results=list(self.results),
                reason=(
                    "threshold_met" if success else "threshold_not_met"
                ),
                elapsed=self.finished_at - self.started_at,
            )

    class QTEResult:
        GRADE_SCORE = {"miss": 0, "bad": 1, "good": 2, "critical": 3}

        def __init__(self, grade="miss", given_input=None, hits=0, misses=0, total=1, results=None, reason=None, elapsed=None, success=None):
            self.grade = grade
            self.score = self.GRADE_SCORE.get(grade, 0)

            if success is None:
                self.success = grade in ("bad", "good", "critical")
            else:
                self.success = bool(success)

            self.given_input = given_input

            self.hits = hits
            self.misses = misses
            self.total = total
            self.results = results or []

            self.reason = reason
            self.elapsed = elapsed

        def __repr__(self):
            return (
                f"QTEResult(grade={self.grade}, "
                f"success={self.success}, "
                f"hits={self.hits}, "
                f"misses={self.misses}, "
                f"total={self.total})"
            )

    class QTEButton:
        def __init__(self, image, xpos=640, ypos=360, scale=1.0, timeout=1.0, given_input=None, meta=None):
            self.uid = None

            self.image = image
            self.xpos = xpos
            self.ypos = ypos
            self.scale = scale

            self.timeout = timeout

            if not math.isfinite(self.timeout) or self.timeout <= 0:
                raise ValueError("[QTE CORE] Timeout must be a positive number, got %r." % (self.timeout))
            
            if not math.isfinite(self.scale) or self.scale <= 0:
                raise ValueError("[QTE CORE] Scale must be a positive number, got %r." % (self.scale))

            self.given_input = given_input
            self.meta = dict(meta or {})

            self.spawned_at = None

        def start(self, now=None):
            self.spawned_at = qte_now() if now is None else now

        def elapsed(self, now=None):
            if self.spawned_at is None:
                return 0.0

            now = qte_now() if now is None else now
            return now - self.spawned_at

        def expired(self, now=None):
            return self.elapsed(now) >= self.timeout

        def time_left(self, now=None):
            return max(0.0, self.timeout - self.elapsed(now))

        def handle_input(self, input_name, now=None, **data):
            # This method can be overridden in subclasses to handle specific input events,
            # None by default, as the QTEManager handles input based on button UIDs.
            return None
    
    class QTEClickButton(QTEButton):
        def handle_input(self, input_name, now=None, **data):
            if input_name != "click":
                return None
            
            # Just any type of click can be considered a hit for this button,
            # it's pretty simple as it's just a single click button, you can also use this as
            # a base class for more complex buttons that require specific input or mechanics.
            return QTEResult(
                grade="good",
                given_input=self.given_input,
                hits=1,
                misses=0,
                total=1,
                reason="completed",
                elapsed=self.elapsed(now),
            )

            return False
    
    ## Button types available to the manager,
    ## Event data uses these names to choose which class should be created.
    QTE_BUTTON_TYPES = {
        "click": QTEClickButton,
    }

label qte(button_data):
    $ btn_data = button_data.copy()

    $ defaults = {
        "type": "click",
        "image": "images/testing/ui/qte_test.png",
        "scale": 0.5,
        "timeout": 2.0,
        "given_input": "parry",
    }

    python:
        for key, value in defaults.items():
            btn_data.setdefault(key, value)

    call qte_session({
        "pattern": "single",
        "buttons": [btn_data],
    })

    return _return

label qte_session(event_data, qte_manager=None, qte_images=None):
    $ renpy.stop_skipping()
    $ renpy.dynamic(_autosave=False)

    $ qte_manager = QTEManager(event_data)

    # Prepare each different image used by this session
    $ qte_images = list(dict.fromkeys(
        btn.image for btn in qte_manager.buttons
    ))

    $ renpy.start_predict(*qte_images)
    $ renpy.pause(predict=True)

    call screen qte_single_screen(qte_manager)

    $ renpy.stop_predict(*qte_images)

    return _return