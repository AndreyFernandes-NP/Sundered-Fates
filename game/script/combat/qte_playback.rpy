init -10 python:
    class QTEDelay:
        """A type of a custom wait function based on our own clock method"""

        def __init__(self, duration):
            qte_require(qte_number(duration) and duration > 0, "Invalid wait duration")
        
            self.duration = duration
            self.elapsed = 0.0
            self.cancelled = False
        
        @property
        def done(self):
            return self.elapsed >= self.duration
        
        def update(self, dt):
            self.elapsed = min(self.duration, self.elapsed + dt)

    class QTEPlayback:
        """All of the states that can be changed of any specific playback"""

        def __init__(self, clip):
            self.clip = clip
            self.duration = clip["duration"]
            self.elapsed = 0.0
            self.cancelled = False

            self.view = QTEClipView(self)
        
        @property
        def done(self):
            return (not self.clip["loop"] and self.duration is not None and self.elapsed >= self.duration)
        
        @property
        def frame_index(self):
            if self.duration is None:
                return 0

            count = len(self.clip["frames"])

            return min(int(self.elapsed / self.duration * count), count - 1)

        def update(self, dt):
            if self.cancelled or self.done or dt <= 0:
                return

            native = self.clip["kind"] == "native"

            if not native and self.duration is None:
                return

            previous = (None if native else self.frame_index)
            self.elapsed += dt

            if self.duration is not None:
                if self.clip["loop"]:
                    self.elapsed %= self.duration
                
                else:
                    self.elapsed = min(self.duration, self.elapsed)
            
            if native or previous != self.frame_index:
                renpy.redraw(self.view, 0)
    
    class QTEClipView(renpy.Displayable):
        """Renders a playback using its time"""

        def __init__(self, playback, **properties):
            super().__init__(**properties)

            self.playback = playback
            clip = playback.clip

            sources = ((clip["source"],) if clip["kind"] == "native" else clip["frames"])
            options = {"zoom": clip["scale"]}

            if clip["fit"]:
                options.update(xysize=(config.screen_width, config.screen_height), fit="contain")
            
            self.children = [
                Transform(renpy.displayable(source), **options) for source in sources
            ]

        def visit(self):
            return self.children

        def per_interact(self):
            renpy.redraw(self, 0)
        
        def render(self, width, height, st, at):
            playback = self.playback

            index = (0 if playback.clip["kind"] == "native" else playback.frame_index)
            clock = playback.elapsed

            child = renpy.render(self.children[index], width, height, clock, clock)
            w, h = child.get_size()

            result = renpy.Render(w, h)
            result.blit(child, (0, 0))

            return result
