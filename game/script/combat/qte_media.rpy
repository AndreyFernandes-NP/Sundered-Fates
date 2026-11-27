default qte_media_session = None

init -5 python:
    QTE_MEDIA_EXTENSIONS = {".webm", ".mkv", ".avi", ".mp4", ".m4v", ".mov"}
    QTE_MEDIA_SOURCE_CACHE = {}
    QTE_MEDIA_FILE_CACHE = None
    QTE_MEDIA_MOVIES = {}
    QTE_MEDIA_CHANNEL_LIMIT = 16
    QTE_MEDIA_REGISTERED_CHANNELS = set()
    QTE_MEDIA_INTERACT_REGISTERED = False

    def qte_movie(source, *, loop=False, volume=1.0, side_mask=False, duration=None, scale=1.0, fit=False):
        """Return a JSON-compatible video configuration without starting a playback"""
        return dict(source=source, media=True, loop=loop, volume=volume, side_mask=side_mask, duration=duration, scale=scale, fit=fit)

    def qte_media_files():
        """Index video assets only when a video needs basename resolution"""
        global QTE_MEDIA_FILE_CACHE

        if QTE_MEDIA_FILE_CACHE is None:
            QTE_MEDIA_FILE_CACHE = tuple(
                sorted(
                    path for path in renpy.list_files()
                    if posixpath.splitext(path)[1].lower() in QTE_MEDIA_EXTENSIONS
                )
            )

        return QTE_MEDIA_FILE_CACHE

    def qte_media_source(name):
        """Resolve a video filename or unique basename to its project asset path"""
        name = qte_image_name(name)

        if name in QTE_MEDIA_SOURCE_CACHE:
            return QTE_MEDIA_SOURCE_CACHE[name]

        if renpy.loadable(name):
            extension = posixpath.splitext(name)[1].lower()
            qte_require(extension in QTE_MEDIA_EXTENSIONS, 
            "Unsupported video extension %r for %r, all supported extensions are: %s" % (extension or "<none>", name, ", ".join(sorted(QTE_MEDIA_EXTENSIONS))))

            path = name

        else:
            qte_require("/" not in name, "Video file '%r' was not found. Check the path, or use a basename to search project assets" % (name,))

            matches = [p for p in qte_media_files() if name in (posixpath.basename(p), posixpath.splitext(posixpath.basename(p))[0])]
            qte_require(bool(matches), "No video asset matches %r. Provide an exact project path or an asset basename, supported extensions: %s" % (name, ", ".join(sorted(QTE_MEDIA_EXTENSIONS))))

            if len(matches) > 1:
                message = ("[QTE VIDEO] Ambiguous video name '%r', using '%r' from candidates %r, if needed provide a full path to select one of those specific files" % (name, matches[0], matches))

                renpy.log(message)
                warnings.warn(message, RuntimeWarning)

            path = matches[0]

        QTE_MEDIA_SOURCE_CACHE[name] = path

        return path

    def qte_resolve_media(value, duration=None, required=False):
        """Resolve a video descriptor, or return None when another resolver may handle it"""
        if isinstance(value, str):
            value = {"source": value}

        if not isinstance(value, builtins.dict) or not isinstance(value.get("source"), str):
            qte_require(not required, "Expected a video filename or qte_movie descriptor, instead got %s: %r" % (type(value).__name__, value))
            return None

        source = qte_image_name(value["source"])

        if not renpy.loadable(source) and renpy.has_image(source, exact=True):
            registered = renpy.get_registered_image(source)

            if isinstance(registered, Movie):
                path = getattr(registered, "_original_play", None) or getattr(registered, "_play", None)

                qte_require(isinstance(path, str) and not path.startswith("<"), "Registered Movie %r does not expose a plain filename, give a video path or a qte_movie descriptor instead" % (source,))
                qte_require(not registered.mask and registered.play_callback is None, "Registered Movie %r uses a mask or play callback that QTE media cannot copy, use a plain Movie or qte_movie descriptor instead" % (source,))

                value = dict({"loop": registered.loop, "side_mask": registered.side_mask}, **value)
                value["source"] = source = path

            elif not required and not value.get("media", False):
                return None

        detected = value.get("media", False) or posixpath.splitext(source)[1].lower() in QTE_MEDIA_EXTENSIONS

        if not detected and not required:
            extension = posixpath.splitext(source)[1].lower()

            if not extension and "/" not in source:
                detected = any(source in (posixpath.basename(path), posixpath.splitext(posixpath.basename(path))[0]) for path in qte_media_files())

            if not detected:
                return None

        allowed = {"source", "media", "loop", "volume", "side_mask", "duration", "scale", "fit"}
        unknown = set(value) - allowed

        qte_require(not unknown, "Invalid video clip fields %r, allowed fields are %r. Descriptor received: %r" % (sorted(unknown), sorted(allowed), value))

        clip = qte_movie(source)
        clip.update(value)

        if duration is not None:
            clip["duration"] = duration

        for key in ("loop", "side_mask", "fit", "media"):
            qte_require(type(clip[key]) is bool, "Video %s must be a boolean, instead got: %r" % (key, clip[key]))

        qte_require(qte_number(clip["volume"]) and 0 <= clip["volume"] <= 1, "Video volume must be a value between 0 and 1, got %r" % (clip["volume"],))
        qte_require(qte_number(clip["scale"]) and clip["scale"] > 0, "Video scale must be a positive finite number, not %r" % (clip["scale"],))

        qte_require(clip["duration"] is None or (qte_number(clip["duration"]) and clip["duration"] > 0), "Video duration must be a positive finite number or None, not %r" % (clip["duration"],))
        qte_require(not (clip["loop"] and clip["duration"] is not None), "Video %r cannot loop and have a duration limit at the same time, omit duration or set loop=False." % (source,))

        clip.update(kind="media", source=qte_media_source(source))

        return clip

    def qte_can_wait_clip(clip):
        """Return whether playback has a reliable completion condition for wait"""
        # Native video finishes at EOF, so its duration need not be known at init
        return not clip["loop"] and (clip["kind"] == "media" or clip["duration"] is not None)

    def qte_make_playback(clip, session):
        return QTEMediaPlayback(clip, session.ensure_media()) if clip["kind"] == "media" else QTEPlayback(clip)

    def qte_close_playback(playback):
        if isinstance(playback, QTEMediaPlayback):
            playback.close()
        elif not playback.done:
            playback.cancelled = True

    def qte_media_clear_frames(channel):
        """Clear Ren'Py's cached frames before a pooled channel is reused, the caches are engine-owned and must not leak a previous channel owner's frame"""
        video = renpy.display.video
        video.texture.pop(channel, None)

        for masked in (False, True):
            movie = QTE_MEDIA_MOVIES[channel, masked]
            video.group_texture.pop(movie.group, None)

            renpy.redraw(movie, 0)

    def qte_media_register_channel(channel):
        """Register a movie channel and its displayables the first time it is acquired"""
        if channel in QTE_MEDIA_REGISTERED_CHANNELS:
            return

        renpy.music.register_channel(channel, "sfx", loop=False, movie=True, buffer_queue=False, stop_on_mute=False)
        QTE_MEDIA_REGISTERED_CHANNELS.add(channel)

        for masked in (False, True):
            QTE_MEDIA_MOVIES[channel, masked] = Movie(channel=channel, play=None, loop=False, side_mask=masked, keep_last_frame=True)

    class QTEMedia:
        """Pool movie channels and coordinate playback across a QTE session"""

        def __init__(self, session):
            self.session = session
            self.playbacks = []
            self.channels = {}
            self.paused = False

        def acquire(self, playback):
            for index in range(QTE_MEDIA_CHANNEL_LIMIT):
                channel = "qte_movie_%02d" % index

                if channel not in self.channels:
                    qte_media_register_channel(channel)
                    self.channels[channel] = playback

                    return channel

            raise RuntimeError("[QTE VIDEO] There's no movie channel available, all %d channels are busy, remove videos that are no longer needed or increase QTE_MEDIA_CHANNEL_LIMIT" % (QTE_MEDIA_CHANNEL_LIMIT,))

        def release(self, playback):
            """Stop playback and return its channel to the pool if still owned"""
            channel = playback.channel

            if channel is not None and self.channels.get(channel) is playback:
                renpy.music.stop(channel=channel, fadeout=0)
                qte_media_clear_frames(channel)

                self.channels.pop(channel)

            playback.channel = None

        def sync_pause(self):
            depth = getattr(self.session, "_qte_context_depth", renpy.context_nesting_level())
            self.paused = self.session.state != "active" or renpy.context_nesting_level() != depth

            for playback in list(self.playbacks):
                playback.sync_pause()

        def restore(self):
            """Recreate channel playback after loading a save"""
            for channel in tuple(QTE_MEDIA_REGISTERED_CHANNELS):
                renpy.music.stop(channel=channel, fadeout=0)
                qte_media_clear_frames(channel)

            self.channels = {}
            for playback in list(self.playbacks):
                playback.channel = None

                if not playback.cancelled:
                    playback.start(playback.elapsed)

            self.sync_pause()

        def clear(self):
            for playback in list(self.playbacks):
                playback.close()

    class QTEMediaPlayback(QTEPlayback):
        """Manage a video's decoder, track its progress, and reports when the playback finishes"""
        def __init__(self, clip, manager, paused=False, visible=True):
            self.clip, self.manager = clip, manager
            self.duration = clip["duration"]  # Optional playback limit
            self.elapsed = 0.0
            self.cancelled = False
            self.finished = False
            self.paused = paused
            self.visible = visible
            self.channel = None
            self.has_frame = False
            self.warming = True
            self.opened = False
            self.idle_time = 0.0
            self.last_frame_time = 0.0
            self.native_duration = None
            self.view = QTEMediaView(self)

            manager.playbacks.append(self)

            try:
                self.start()

            except Exception:
                self.close()
                raise

        @property
        def done(self):
            return self.finished

        def start(self, offset=0.0):
            """Acquire a channel and begin decoding from the requested offset"""
            if self.channel is None:
                self.channel = self.manager.acquire(self)

            renpy.music.stop(channel=self.channel, fadeout=0)
            qte_media_clear_frames(self.channel)

            self.has_frame, self.warming, self.opened = False, True, False
            self.idle_time = 0.0

            if self.native_duration is not None:
                offset = min(offset, max(0.0, self.native_duration - 0.1))

            source = self.clip["source"]
            if offset > 0:
                source = "<from %.6f loop 0>" % offset + source

            renpy.music.set_pause(not self.visible, channel=self.channel)

            # Decode one frame slightly even when restoring a paused object
            frozen = self.manager.paused or self.paused or self.finished or not self.visible

            renpy.music.set_volume(0.0 if frozen else self.clip["volume"], delay=0, channel=self.channel)
            renpy.music.play(source, channel=self.channel, loop=self.clip["loop"], fadeout=0)

            self.sync_pause()
            renpy.redraw(self.view, 0)

        def sync_pause(self):
            """Apply visibility, warm-up, session, and local pause state to the channel"""
            if self.channel is None:
                return

            if self.warming and self.has_frame:
                self.warming = False

            frozen = self.manager.paused or self.paused or self.finished
            paused = not self.visible or (frozen and not self.warming)

            renpy.music.set_pause(paused, channel=self.channel)
            silent = not self.visible or (self.warming and frozen)

            renpy.music.set_volume(0.0 if silent else self.clip["volume"], delay=0, channel=self.channel)

        def set_volume(self, volume):
            self.clip = dict(self.clip, volume=volume)
            self.sync_pause()

        def update(self, dt):
            if self.cancelled or self.channel is None or not self.visible or dt <= 0:
                return

            self.sync_pause()
            if not self.warming and (self.finished or self.paused or self.manager.paused):
                return

            position = renpy.music.get_pos(channel=self.channel)
            playing = renpy.music.get_playing(channel=self.channel)
            length = renpy.music.get_duration(channel=self.channel)

            if length > 0:
                self.native_duration = length

            self.opened = self.opened or self.has_frame or position is not None or length > 0
            if position is not None:
                self.elapsed = max(0.0, position)

            elif self.has_frame and playing is not None:
                self.elapsed += dt

                if self.clip["loop"] and self.native_duration:
                    self.elapsed %= self.native_duration

            if self.has_frame and playing is not None:
                self.idle_time = 0.0

                if self.duration is not None and self.elapsed >= self.duration:
                    self.finished = True
                    self.sync_pause()

            elif playing is None and self.opened and not self.clip["loop"]:
                qte_require(self.has_frame, "Video %r stopped without producing a frame, check if the file is valid and uses a supported codec" % (self.clip["source"],))
                self.finished = True

                # Resume from the last frame actually rendered, not the decoder's final position
                self.elapsed = self.last_frame_time

                self.sync_pause()
                renpy.redraw(self.view, 0)

            else:
                self.idle_time += dt
                qte_require(self.idle_time < 5.0, "Video %r has made no playback progress for %.1f seconds (opened=%r, has_frame=%r), check the codec, file access, and Ren'Py video support for it" % (self.clip["source"], self.idle_time, self.opened, self.has_frame))

        def close(self):
            if not self.done:
                self.cancelled = True

            self.manager.release(self)

            if self in self.manager.playbacks:
                self.manager.playbacks.remove(self)

            renpy.redraw(self.view, 0)

    class QTEMediaView(renpy.Displayable):
        """Render frames directly from a movie channel without generated image files"""
        def __init__(self, playback):
            super().__init__()
            self.playback = playback

        def child(self):
            """Return the movie displayable currently assigned to this playback channel"""
            playback = self.playback

            if playback.channel is None:
                return None
            
            return QTE_MEDIA_MOVIES[playback.channel, playback.clip["side_mask"]]

        def visit(self):
            """Gives the current movie displayable to Ren'Py"""
            child = self.child()
            return [child] if child is not None else []

        def per_interact(self):
            renpy.redraw(self, 0)

        def render(self, width, height, st, at):
            """Render the current video frame at native size or fitted to the screen"""
            playback, child = self.playback, self.child()

            if child is None:
                return renpy.Render(0, 0)

            native = renpy.render(child, width, height, st, at)
            w, h = native.get_size()

            if w > 0 and h > 0:
                playback.has_frame = True
                position = renpy.music.get_pos(channel=playback.channel)

                if position is not None:
                    playback.last_frame_time = max(0.0, position)

            options = {"zoom": playback.clip["scale"]}

            if playback.clip["fit"]:
                options.update(xysize=(config.screen_width, config.screen_height), fit="contain")

            return renpy.render(Transform(child, **options), width, height, st, at)

    def qte_media_bind(session):
        """Bind the session's media manager to Ren'Py's interaction lifecycle"""
        global qte_media_session
        
        qte_require(
            qte_media_session is None or qte_media_session is session,
            "Cannot bind QTE scene '%r' while scene %r is still bound/in-progress, finish or unbind the previous scene first"
            % (session.scene_id, None if qte_media_session is None else qte_media_session.scene_id),
        )

        qte_media_session = session
        qte_media_register_interact()

        if session.media is not None:
            session.media.sync_pause()

    def qte_media_unbind(session):
        """Close the session's media and clear the global binding if it owns it"""
        global qte_media_session, QTE_MEDIA_INTERACT_REGISTERED
        if session.media is not None:
            session.media.clear()

        if qte_media_session is session:
            qte_media_session = None

            if QTE_MEDIA_INTERACT_REGISTERED:
                config.interact_callbacks.remove(qte_media_interact)
                QTE_MEDIA_INTERACT_REGISTERED = False

    def qte_media_register_interact():
        """Register media synchronization only while a video session is active"""
        global QTE_MEDIA_INTERACT_REGISTERED

        if not QTE_MEDIA_INTERACT_REGISTERED:
            config.interact_callbacks.append(qte_media_interact)
            QTE_MEDIA_INTERACT_REGISTERED = True

    def qte_media_interact():
        """Synchronize playback whenever Ren'Py starts an interaction"""
        if qte_media_session is not None and qte_media_session.media is not None:
            qte_media_session.media.sync_pause()

    def qte_media_after_load():
        """Reset the scene clock and restore video channels after loading"""
        if qte_media_session is not None and qte_media_session.media is not None:
            qte_media_register_interact()
            qte_media_session._qte_tick_at = None
            qte_media_session.media.restore()

    config.after_load_callbacks.append(qte_media_after_load)
