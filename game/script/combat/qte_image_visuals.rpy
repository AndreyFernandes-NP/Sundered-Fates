init -10 python:

    class QTEImageClock:
        
        def __init__(self):
            self.time = 0.0

    class QTEImageTimed(renpy.Displayable):
        """Uses an elapsed timer from a shared image clock relative to this wrapper's origin."""

        def __init__(self, child, clock, origin=0.0, local=False):
            super().__init__()
            self.child = child
            self.clock = clock
            self.origin = origin
            self.local = local

        def visit(self):
            return [self.child]

        def get_placement(self):
            if self.local:
                return (0, 0, 0, 0, 0, 0, False)
            return self.child.get_placement()

        def render(self, width, height, st, at):
            elapsed = max(0.0, self.clock.time - self.origin)
            child = renpy.render(self.child, width, height, elapsed, elapsed)

            if self.local:
                # Give both transition states equal canvas sizes, including transparent Show/Hide states
                result = renpy.Render(width, height)
                result.blit(child, (0, 0))

                return result

            return child

    def qte_image_alpha_transition(displayable):
        """Enable alpha on transition displayables that expose it, including any nested transitions"""
        if isinstance(displayable, renpy.display.transition.Transition):
            if hasattr(displayable, "alpha"):
                displayable.alpha = True

            for child in getattr(displayable, "transitions", ()):
                qte_image_alpha_transition(child)

    class QTEImageView(renpy.Displayable):
        """Manage one image's target and any transition currently running between targets"""

        def __init__(self, clock):
            super().__init__()
            self.clock = clock
            self.target = None
            self.previous = None
            self.placement = Null()
            self.effect = None
            self.effect_at = 0.0
            self.effect_duration = 0.0

        @property
        def drawing(self):
            return self.target is not None or self.effect is not None

        def change(self, target, transition=None):
            """Set a new target and optionally transition from the current target"""
            # Start interruptions from the last target instead of nesting unfinished transitions
            previous = self.target
            effect = None

            if transition is not None and (previous is not None or target is not None):
                old = QTEImageTimed(previous or Null(), self.clock, local=True)
                new = QTEImageTimed(target or Null(), self.clock, local=True)

                try:
                    effect = transition(old_widget=old, new_widget=new)

                except Exception as exc:
                    raise ValueError("[QTE IMAGE] This transition cannot be applied to one image. Use a displayable transition, or ATL for movement") from exc

                effect = renpy.displayable(effect)
                duration = getattr(effect, "delay", None)

                qte_require(qte_number(duration) and duration >= 0, "Image transition needs a finite delay, instead got: %r" % duration)
                qte_image_alpha_transition(effect)

                if duration == 0:
                    effect = None

            self.previous = previous if effect is not None else None

            self.target = target
            self.placement = target or previous or self.placement

            self.effect = effect
            self.effect_at = self.clock.time
            self.effect_duration = 0.0 if effect is None else duration

            renpy.redraw(self, 0)

        def update(self):
            if self.effect is not None and self.clock.time - self.effect_at >= self.effect_duration:
                self.effect = None
                self.previous = None

                renpy.redraw(self, 0)
                return True

            return False

        def visit(self):
            return [d for d in (self.target, self.previous, self.effect) if d is not None]

        def per_interact(self):
            renpy.redraw(self, 0)

        def get_placement(self):
            return self.placement.get_placement()

        def render(self, width, height, st, at):
            if self.effect is None:
                if self.target is None:
                    return renpy.Render(0, 0)

                return renpy.render(self.target, width, height, self.clock.time, self.clock.time)

            # Size the transition canvas to the image states so Fade's Solid doesn't cover the entire screen
            sizes = [renpy.render(d, width, height, self.clock.time, self.clock.time).get_size() for d in (self.previous, self.target) if d is not None]

            w = max(1, int(math.ceil(max(size[0] for size in sizes))))
            h = max(1, int(math.ceil(max(size[1] for size in sizes))))

            elapsed = self.clock.time - self.effect_at
            canvas = Fixed(self.effect, xysize=(w, h))
            
            return renpy.render(canvas, w, h, elapsed, elapsed)
