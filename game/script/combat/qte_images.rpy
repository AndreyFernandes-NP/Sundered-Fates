init -20 python:

    def qte_image(name, **options):
        qte_require(not ({"op", "name"} & set(options)), "Reserved qte_image option")

        return dict(options, op="image", name=name)

    def qte_set_property(**properties):
        return {"op": "set_property", "properties": properties}

init -10 python:
    import warnings

    QTE_IMAGE_SOURCE_CACHE = {}
    QTE_IMAGE_FILE_INDEX = None
    QTE_IMAGE_OPTIONS = {"op", "name", "at", "atl", "trans", "xpos", "ypos", "zorder", "action"}
    QTE_IMAGE_SHORTCUTS = {"transparent": {"alpha": 0.0}, "opaque": {"alpha": 1.0}}
    QTE_IMAGE_AT = {None, "Center", "truecenter", "center", "left", "right", "top", "topleft", "topright"}

    def qte_image_name(value):
        qte_require(isinstance(value, str) and bool(value.strip()), "Ofc image name must not be empty, tf you're thinking?")

        return value.strip().replace("\\", "/")

    def qte_image_names(value):
        choice = qte_choice_info(value)

        if choice is None:
            return [qte_image_name(value)], None

        options = choice["options"]
        qte_require(
            all(isinstance(option, str) and bool(option.strip()) for option in options),
            "qte_image qte_choice options must all be non-empty image names",
        )

        return [qte_image_name(option) for option in options], choice

    def qte_image_source(name):
        """You can retrieve each source based on specific file paths, exact renpy image names or an unique basename"""
        global QTE_IMAGE_FILE_INDEX

        name = qte_image_name(name)
        if name in QTE_IMAGE_SOURCE_CACHE:
            return QTE_IMAGE_SOURCE_CACHE[name]

        if "/" in name or renpy.loadable(name):
            qte_require(renpy.loadable(name), "Image file not found: " + name)

            result = (name, False)

        elif renpy.has_image(name, exact=True):
            result = (name, True)

        else:
            if QTE_IMAGE_FILE_INDEX is None:
                index = {}
                extensions = QTE_IMAGE_EXTENSIONS | {".avif", ".bmp", ".gif"}

                for path in sorted(SF_ASSETS):
                    base = posixpath.basename(path)
                    stem, ext = posixpath.splitext(base)

                    if ext.lower() in extensions:
                        for key in (base, stem):
                            index.setdefault(key, []).append(path)

                QTE_IMAGE_FILE_INDEX = index

            matches = QTE_IMAGE_FILE_INDEX.get(name, [])
            qte_require(bool(matches), "Image not found: " + name)

            if len(matches) > 1:
                message = "[QTE IMAGE] Ambiguous name %r. Using %r, candidates: %r. In any case just use the full image path" % (name, matches[0], matches)

                renpy.log(message)
                warnings.warn(message, RuntimeWarning)

            result = (matches[0], False)

        QTE_IMAGE_SOURCE_CACHE[name] = result

        return result

    def qte_image_transform(name):
        if name is None:
            return None

        qte_require(isinstance(name, str) and name.isidentifier(), "Expected a named Ren'Py transform, '%r' is invalid" % name)
        value = getattr(renpy.store, name, None)

        if value is None and name == "Center":
            value = getattr(renpy.store, "truecenter", None)

        qte_require(isinstance(value, Transform), "Unknown transform: " + name)

        return value

    def qte_image_transition(name):
        if name is None:
            return None

        qte_require(isinstance(name, str) and name.isidentifier(), "Expected a valid named transition, '%r is invalid" % name)

        value = getattr(renpy.store, name, None)
        qte_require(callable(value), "Unknown transition: " + name)

        return value

    def qte_image_properties(value):
        qte_require(isinstance(value, builtins.dict), "set_property requires an object at least")

        ## Keep this API restricted to native transform properties, anything below can make things a tad messier or complicated
        ## BUT- fuck it we only live once, just try and experiment anything below by taking them off from the list, if it crashes? just try again until it works
        reserved = {"child", "function", "style", "focus", "default", "reset"}
        qte_require(all(isinstance(k, str) and not k.startswith("_") and k not in reserved for k in value), "Invalid transform property name")
        try:
            Transform(**value)
        except Exception as exc:
            raise ValueError("[QTE IMAGE] Invalid transform properties: " + repr(value)) from exc
        for key in ("xpos", "ypos"):
            if key in value:
                qte_require(value[key] is None or qte_number(value[key]), key + " must be a number or None")
        return dict(value)

    def qte_image_actions(value):
        if value is None:
            return [("show", {})]
        if isinstance(value, (str, builtins.dict)):
            value = [value]
        qte_require(isinstance(value, (builtins.list, tuple)), "Image action must be an action or a list")
        actions = []
        for action in value:
            if isinstance(action, str):
                name = action.strip().lower()
                if name in QTE_IMAGE_SHORTCUTS:
                    actions.append(("set_property", dict(QTE_IMAGE_SHORTCUTS[name])))
                else:
                    qte_require(name in ("show", "hide", "remove"), "Unknown image action: " + action)
                    actions.append((name, {}))
            else:
                qte_require(isinstance(action, builtins.dict) and set(action) == {"op", "properties"}, "Invalid image action object")
                qte_require(action["op"] == "set_property", "Expected set_property")
                actions.append(("set_property", qte_image_properties(action["properties"])))
        return actions

    def qte_image_merge_properties(current, changes):
        # Reinsert overwritten keys so the newest related property wins:
        # e.g. align first, then a later explicit xpos.
        result = dict(current)
        for key, value in changes.items():
            result.pop(key, None)
            result[key] = value
        return result

    class QTEImageItem:
        """One identity, its retained ATL objects, and its local transition."""
        def __init__(self, name, serial, source, native):
            self.name = name
            self.serial = serial
            self.native = native
            self.clock = QTEImageClock()
            self.source = QTEImageTimed(renpy.displayable(source), self.clock)
            self.at_key = None
            self.at_view = self.source
            self.atl_key = None
            self.atl_view = None
            self.config = None
            self.body = None
            self.view = QTEImageView(self.clock)

        def configure(self, config, transition, restart_atl=False):
            props = config["properties"]
            explicit_position = all(props.get(key) is not None for key in ("xpos", "ypos"))
            at_key = None if explicit_position else config["at"]
            at_changed = self.config is None or at_key != self.at_key
            at_view = self.at_view
            if at_changed:
                factory = qte_image_transform(at_key)
                if factory is None:
                    at_view = self.source
                else:
                    transform = factory(child=self.source)
                    transform.set_transform_event("show")
                    at_view = QTEImageTimed(transform, self.clock, self.clock.time)

            atl_key = config["atl"]
            atl_view = self.atl_view
            if atl_key is None:
                atl_view = None
            elif restart_atl or at_changed or atl_key != self.atl_key:
                transform = qte_image_transform(atl_key)(child=at_view)
                origin = self.clock.time
                if not restart_atl and atl_key == self.atl_key and self.atl_view is not None:
                    # Reparent an unchanged ATL while retaining its execution
                    # state. Ordinary property updates reuse the original ATL.
                    transform.take_state(self.atl_view.child)
                    transform.take_execution_state(self.atl_view.child)
                    origin = self.atl_view.origin
                else:
                    transform.set_transform_event("show")
                atl_view = QTEImageTimed(transform, self.clock, origin)

            outer = {"anchor": (0.5, 0.5)} if explicit_position else {}
            outer.update(props)
            body = Transform(child=atl_view or at_view, **outer)
            self.view.change(body if config["visible"] else None, transition)
            self.at_key, self.at_view = at_key, at_view
            self.atl_key, self.atl_view = atl_key, atl_view
            self.body, self.config = body, config

        def update(self, dt):
            if not self.view.drawing:
                return False
            self.clock.time += dt
            finished = self.view.update()
            animated = self.native or self.atl_key is not None or self.at_key not in QTE_IMAGE_AT
            if dt > 0 and (animated or self.view.effect is not None):
                renpy.redraw(self.view, 0)
            return finished

    class QTEImages:
        """Session-owned registry. Hidden entries persist; removed ones do not."""
        def __init__(self, qte_manager):
            self.qte_manager = qte_manager
            self.items = {}
            self.outgoing = []
            self.serial = 0
            self.revision = 0

        def validate(self, step):
            qte_require({"op", "name"} <= set(step) <= QTE_IMAGE_OPTIONS and step["op"] == "image", "Invalid image instruction fields")
            names, choice = qte_image_names(step["name"])
            actions = qte_image_actions(step.get("action"))
            explicit_position = all(step.get(k) is not None for k in ("xpos", "ypos"))
            for key in ("at", "atl"):
                if key in step and not (key == "at" and explicit_position):
                    qte_image_transform(step[key])
            qte_image_transition(step.get("trans"))
            qte_image_properties({k: step[k] for k in ("xpos", "ypos") if k in step})
            if "zorder" in step:
                qte_require(type(step["zorder"]) is int, "image.zorder must be an integer")
            if any(action == "show" for action, _ in actions):
                for name in names:
                    qte_image_source(name)
            return names, choice, actions

        def _config(self, old, step):
            config = dict(old) if old is not None else {
                "at": "Center", "atl": None, "properties": {}, "zorder": 0, "visible": True,
            }
            props = dict(config["properties"])
            explicit_position = all(step.get(k) is not None for k in ("xpos", "ypos"))
            if "at" in step and not explicit_position:
                # An explicitly requested placement replaces older direct
                # coordinates; coordinates from this instruction still win.
                config["at"] = step["at"]
                props.pop("xpos", None)
                props.pop("ypos", None)
            config["properties"] = qte_image_merge_properties(props, {k: step[k] for k in ("xpos", "ypos") if k in step})
            for key in ("atl", "zorder"):
                if key in step:
                    config[key] = step[key]
            return config

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

            # Work on a copy first. A bad action list cannot partially hide
            # or remove the current object before raising its error.
            for action, properties in actions:
                if action == "show":
                    if config is None:
                        config = self._config(None, step)
                        recreated = True
                    config["visible"] = True
                elif action == "hide":
                    if config is not None:
                        config["visible"] = False
                elif action == "remove":
                    config = None
                else:
                    qte_require(config is not None, "Show image before setting its properties: " + name)
                    config["properties"] = qte_image_merge_properties(config["properties"], properties)

            transition = qte_image_transition(step.get("trans")) if preferences.transitions else None
            if config is None:
                if old is not None:
                    old.view.change(None, transition)
                    del self.items[name]
                    if old.view.drawing:
                        self.outgoing.append(old)
                    self.revision += 1
                return None

            # Repeating Show/Hide without another change is an actual no-op.
            changed = old is None or recreated or config != old.config or "atl" in step
            replay = transition is not None and config["visible"]
            if not changed and not replay:
                return None

            if old is None or recreated:
                source, native = qte_image_source(name)
                item = QTEImageItem(name, self.serial + 1, source, native)
            else:
                item = old
            item.configure(config, transition, restart_atl="atl" in step)
            if item is not old:
                self.serial += 1
            self.items[name] = item
            self.revision += 1
            return None

        def update(self, dt):
            for item in list(self.items.values()) + list(self.outgoing):
                was_drawing = item.view.drawing
                item.update(dt)
                if was_drawing != item.view.drawing:
                    self.revision += 1
            self.outgoing = [item for item in self.outgoing if item.view.drawing]

        def draw_order(self, foreground=False):
            # Negative zorder: behind actors. Zero and above: in front.
            items = list(self.items.values()) + list(self.outgoing)
            return sorted(
                (item for item in items if item.view.drawing and (item.config["zorder"] >= 0) == foreground),
                key=lambda item: (item.config["zorder"], item.serial),
            )

        def clear(self):
            if self.items or self.outgoing:
                self.items.clear()
                self.outgoing.clear()
                self.revision += 1
