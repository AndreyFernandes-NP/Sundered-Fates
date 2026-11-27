init -10 python:

    QTE_MEDIA_OPTIONS = {"loop", "volume", "duration", "side_mask", "scale", "fit"}
    QTE_VIDEO_OPTIONS = QTE_IMAGE_OPTIONS | QTE_MEDIA_OPTIONS

    def qte_video(name, **options):
        reserved = {"op", "name"} & set(options)
        qte_require(not reserved, "qte_video reserves the 'op' and 'name' fields, remove these options: %r" % (sorted(reserved),))

        return dict(options, op="video", name=name)

    def qte_video_actions(value):
        if value is None:
            value = "Show"

        if isinstance(value, (str, builtins.dict)):
            value = [value]
            
        qte_require(isinstance(value, (builtins.list, tuple)), "Video action must be an action or a list of actions, instead got: %r" % (value,))

        result = []

        for action in value:
            if isinstance(action, str):
                name = action.strip().lower()

                if name in ("pause", "resume", "restart"):
                    result.append((name, {}))
                    
                else:
                    qte_require(name in ("show", "hide", "remove", "transparent", "opaque"), 
                    "Unknown video action '%r', expected show, hide, remove, pause, resume, restart, transparent, or opaque" % (action,))

                    result.extend(qte_image_actions(action))
            else:
                result.extend(qte_image_actions(action))

        return result

    class QTEVideoItem(QTEImageItem):
        """Combine an image-style view with a managed video playback"""

        def __init__(self, name, serial, playback):
            super().__init__(name, serial, playback.view, False)
            self.playback = playback
            self.was_drawing = False

        def sync_pause(self):
            """Keep the decoder's visibility and pause state aligned with its view"""
            if not self.was_drawing and self.view.drawing and self.playback.done and not self.playback.warming:
                self.playback.start(self.playback.elapsed)

            self.was_drawing = self.view.drawing
            self.playback.visible = self.view.drawing
            self.playback.paused = self.config["paused"] or not self.view.drawing
            self.playback.sync_pause()

        def update(self, dt):
            self.sync_pause()
            self.playback.update(dt)
            result = super().update(dt)
            self.sync_pause()
            return result

        def dispose(self):
            self.playback.close()

    class QTEVideos(QTEImages):
        """Manage scene videos using the image module's presentation and layering"""

        def __init__(self, session):
            super().__init__(session.qte)
            self.session = session

        def validate(self, step):
            qte_require(isinstance(step, builtins.dict), "Video instruction must be an object, instead got: %r" % (step,))

            received = set(step)
            missing = {"op", "name"} - received
            unknown = received - QTE_VIDEO_OPTIONS

            qte_require(not missing and not unknown and step.get("op") == "video", 
            "Invalid video instruction, expected op='video' with required fields 'op' and 'name'\n got op=%r, fields=%r, missing=%r, unknown=%r" % (step.get("op"), sorted(received), sorted(missing), sorted(unknown)))

            names, choice = qte_image_names(step["name"])
            actions = qte_video_actions(step.get("action"))

            visual = {k: v for k, v in step.items() if k not in QTE_MEDIA_OPTIONS}
            visual.update(op="image", action=[])

            QTEImages.validate(self, visual)

            if any(action in ("show", "restart") for action, _ in actions) or any(key in step for key in QTE_MEDIA_OPTIONS):
                for name in names:
                    probe = self._config(None, step)
                    self.clip_for(name, probe)

            return names, choice, actions

        def _config(self, old, step):
            """Merge retained video settings with values from a specific instruction, like we do with the image module"""
            config = super()._config(old, step)

            if old is None:
                config.update(loop=True, volume=1.0, duration=None, side_mask=False, scale=1.0, fit=False, paused=False)

            for key in QTE_MEDIA_OPTIONS:
                if key in step:
                    config[key] = step[key]

            if config["duration"] is not None and "loop" not in step:
                config["loop"] = False

            return config

        def clip_for(self, name, config):
            """Resolve a video's source and media options into a playback clip"""
            return qte_resolve_media(dict(source=name, **{key: config[key] for key in QTE_MEDIA_OPTIONS}), required=True)

        def apply(self, step):
            names, choice, actions = self.validate(step)

            if choice is None:
                name = names[0]
            else:
                index = qte_choice_index(choice, self.qte_manager.choice_history)
                name = names[index]

            old = self.items.get(name)

            config = None if old is None else self._config(old.config, step)

            recreated = False
            restart = False

            for action, properties in actions:
                if action == "show":
                    if config is None:
                        config, recreated = self._config(None, step), True

                    config["visible"] = True

                elif action == "hide":
                    if config is not None:
                        config["visible"] = False

                elif action == "remove":
                    config = None

                elif action in ("pause", "resume"):
                    if config is not None:
                        config["paused"] = action == "pause"

                elif action == "restart":
                    qte_require(config is not None, "Cannot restart video %r because it has not been shown in this scene yet" % (name,))
                    restart = True

                else:
                    qte_require(config is not None, "Cannot change properties for video %r because it has not been shown in this scene yet" % (name,))
                    config["properties"] = qte_image_merge_properties(config["properties"], properties)

            transition = qte_image_transition(step.get("trans")) if preferences.transitions else None
            if config is None:
                if old is not None:
                    old.view.change(None, transition)

                    del self.items[name]

                    if old.view.drawing:
                        self.outgoing.append(old)

                    else:
                        old.dispose()

                    self.revision += 1

                return None

            structural = old is not None and any(config[k] != old.config[k] for k in ("loop", "duration", "side_mask"))
            replace = old is None or recreated or restart or structural
            changed = replace or config != old.config or "atl" in step
            replay = transition is not None and config["visible"]

            if not changed and not replay:
                return None

            clip = self.clip_for(name, config)

            if replace:
                frees_channel = old is not None and old.playback.channel is not None and (transition is None or not old.view.drawing)

                media = self.session.media
                channel_limit = QTE_MEDIA_CHANNEL_LIMIT
                channel_reason = ("the previous playback must remain active for its exit transition" if old is not None and old.playback.channel is not None else "no existing playback channel can be released")

                qte_require(frees_channel or (media is None or len(media.channels) < channel_limit), "Cannot start video '%r', all %d video channels are occupied, and %s" % (name, channel_limit, channel_reason))

                # Keep the old decoder only while its exit transition is visible, otherwise release it before restarting.
                if old is not None:
                    if transition is not None and old.view.drawing:
                        old.view.change(None, transition)
                        self.outgoing.append(old)

                    else:
                        old.dispose()

                self.serial += 1

                playback = QTEMediaPlayback(clip, self.session.ensure_media(), paused=config["paused"], visible=config["visible"])
                item = QTEVideoItem(name, self.serial, playback)

            else:
                item = old
                item.playback.clip = dict(item.playback.clip, scale=clip["scale"], fit=clip["fit"])
                item.playback.set_volume(config["volume"])
                renpy.redraw(item.playback.view, 0)

            item.configure(config, transition, restart_atl="atl" in step)
            item.sync_pause()

            self.items[name] = item
            self.revision += 1

            return None

        def update(self, dt):
            for item in list(self.items.values()) + list(self.outgoing):
                was_drawing = item.view.drawing
                item.update(dt)

                if was_drawing != item.view.drawing:
                    self.revision += 1

            for item in list(self.outgoing):
                if not item.view.drawing:
                    item.dispose()
                    self.outgoing.remove(item)

        def clear(self):
            for item in list(self.items.values()) + list(self.outgoing):
                item.dispose()

            super().clear()

    def qte_scene_objects(session, foreground=False):
        images = session.images.draw_order(foreground)
        videos = [] if session.videos is None else session.videos.draw_order(foreground)

        # Keep equal-zorder items stable, with videos drawn over images
        return sorted(images + videos, key=lambda item: (item.config["zorder"], isinstance(item, QTEVideoItem), item.serial))
