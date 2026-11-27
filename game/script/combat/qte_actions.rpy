init -15 python:
    import time

    class QTEInteraction:
        """
        Works like a mutable state for any type of execution,
        inherits this if you want to create another class of interactions
        """

        screen_name = None

        @staticmethod
        def validate(params):
            qte_require(isinstance(params, builtins.dict) and not params, "This interaction does not accept extra parameters")

        def __init__(self, definition):
            self.definition = definition
            self.duration = definition.get("duration", 2.0)
            self.elapsed = 0.0
            self.result = None
            self.uid = None
            self.view_revision = 0
            self.visual_active = False
            self.visual_tick_at = None

        @property
        def visual_elapsed(self):
            if not self.visual_active or self.visual_tick_at is None or self.result is not None:
                return self.elapsed

            elapsed = self.elapsed + max(0.0, time.monotonic() - self.visual_tick_at)

            return min(self.duration, elapsed)

        def set_visual_active(self, active):
            if self.visual_active == active:
                return

            self.visual_active = active
            self.visual_tick_at = time.monotonic() if active else None

        def update(self, dt):
            if self.result is None:
                self.elapsed = min(self.duration, self.elapsed + dt)
                self.visual_tick_at = time.monotonic() if self.visual_active else None

                if self.elapsed >= self.duration:
                    self.finish(False, "timeout")
        
        def input(self, name, **data):
            return False

        def finish(self, success, reason):
            if self.result is None:
                self.result = {
                    "action": self.definition["id"],
                    "source": self.definition.get("source"),
                    "target": self.definition.get("target"),
                    "success": success,
                    "grade": "good" if success else "miss",
                    "reason": reason,
                    "elapsed": self.elapsed,
                }
        
        def invalidate_view(self):         
            self.view_revision +=1
    
    class QTEClick(QTEInteraction):
        screen_name = "qte_click_control"

        def __init__(self, definition):
            super().__init__(definition)

            self.visual = QTEButtonVisual(self)

        def input(self, name, **data):
            if self.result is not None or name != "click":
                return False

            self.finish(True, "completed")
            return True
        
    QTE_INPUT_TYPES = {
        "click": QTEClick,
    }
