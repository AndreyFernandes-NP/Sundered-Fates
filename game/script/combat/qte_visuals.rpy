################################################################################
## QTE VISUALS
##
## Takes an ordered image list and plays it as a single animation
## the duration belongs to the whole (like HOLE) animation, so adding more frames
## makes the movement more detailed/fluid without making it take longer.
################################################################################

init -10 python:
    import math
    from collections.abc import Mapping

    renpy.add_layer("combat_visuals", below="screens")

    class QTEVisual(renpy.Displayable):

        def __init__(self, frames, duration=1.0, scale=1.0, mirrored=False, **kwargs):
            super().__init__(**kwargs)

            self.duration = duration
            self.scale = scale
            self.mirrored = bool(mirrored)

            if not math.isfinite(self.duration) or self.duration <= 0:
                raise ValueError("[QTE VISUALS] Duration must be a positive number, got %r." % (self.duration))
            
            if not math.isfinite(self.scale) or self.scale <= 0:
                raise ValueError("[QTE VISUALS] Scale must be a positive number, got %r." % (self.scale))
            
            if not frames or not isinstance(frames, (list, tuple)):
                raise ValueError("[QTE VISUALS] Frames must be a non-empty list or tuple, got %r." % (frames))
            
            self.frames = []

            for frame_path in frames:
                # We use Transform here to ensure that the image is scaled to fit the screen, while maintaining its aspect ratio
                image = Transform(frame_path, xysize=(config.screen_width, config.screen_height), fit="contain", zoom=self.scale, xzoom=-1.0 if self.mirrored else 1.0)
                self.frames.append(image)
            
            self.frame_duration = self.duration / len(self.frames)
        
        def visit(self):
            # A way to let Ren'Py know that this displayable can show
            return self.frames
    
        def render(self, width, height, st, at):
            # st is how long this displayable has been shown for, in seconds
            # once we reach the end of it, keep showing the last frame by default

            frame_index = min(int(st / self.frame_duration), len(self.frames) - 1)
            frame = self.frames[frame_index]

            frame_render = renpy.render(frame, width, height, st, at)
            result = renpy.Render(width, height)

            frame_width, frame_height = frame_render.get_size()

            x = int((width - frame_width) / 2)
            y = int((height - frame_height) / 2)

            result.blit(frame_render, (x, y))

            # Schedule the next frame to be drawn, if there is one
            if frame_index < len(self.frames) - 1:
                next_frame_at = (frame_index + 1) * self.frame_duration

                renpy.redraw(self, max(0.001, next_frame_at - st))

            return result
    
    def qte_build_visual(data):
        """
        Basically what we already do above but automatically,
        creates new visuals based on a frame path with its animations
        """

        if data is None:
            return None

        if not isinstance(data, Mapping):
            raise ValueError(f"[QTE VISUALS] Visual data must be a dictionary, got {data}")
        
        path = data.get("path")

        if not isinstance(path, str) or not path:
            raise ValueError(f"[QTE VISUALS] A visual needs a non-empty string path, got '{path}'")
        
        frames = qte_get_frames(path)

        if not frames:
            raise ValueError(f"[QTE VISUALS] No frames found for '{path}'")
        
        return QTEVisual(frames, duration=data.get("duration", 0.3), scale=data.get("scale", 1.0), mirrored=data.get("mirrored", False))

screen qte_visuals_preview(visual):
    add visual

    textbutton "Close":
        align (0.98, 0.95)
        action Hide("qte_visuals_preview")

screen qte_combat_visual(visual):
    zorder 0

    add visual

screen qte_beat_wait(duration):
    modal True
    zorder 201

    timer duration action Return(True)

    key "dismiss" action NullAction()
    key "game_menu" action NullAction()
    key "rollback" action NullAction()
    key "skip" action NullAction()
    key "toggle_skip" action NullAction()
