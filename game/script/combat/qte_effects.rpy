init -10 python:

    class QTEEffects:
        def __init__(self, qte_manager):
            self.qte_manager = qte_manager
            self.revision = 0

        def validate(self, value):
            """Validates every transition option without selecting one"""

            self._resolve(value, choose=False)

        def _resolve(self, value, choose):

            if value is None:
                return []

            if isinstance(value, (str, builtins.dict)):
                value = [value]

            qte_require(isinstance(value, (builtins.list, tuple)), "effect must be a name, an effect instruction or a list")

            resolved = []
            allowed = {"op", "name", "layers", "always"}

            for entry in value:
                if isinstance(entry, str):
                    entry = qte_effect(entry)

                qte_require(isinstance(entry, builtins.dict), "Invalid effect entry, it should be a dictionary")
                qte_require({"name"} <= set(entry) <= allowed, "Missing or unknown effect fields, got: %r, expected: %r" % (entry, allowed))
                qte_require(entry.get("op", "effect") == "effect", "Expected an effect instruction, got: %r" % (entry.get("op", "effect"),))

                cue = qte_effect(entry["name"])
                cue.update(entry)

                name_choice = qte_choice_info(cue["name"])
                names = (name_choice["options"] if name_choice is not None else cue["name"])

                if isinstance(names, str):
                    names = [names]

                qte_require(isinstance(names, (builtins.list, tuple)) and bool(names), "effect name must be a name or a non-empty list of names")

                transitions = []
                for name in names:
                    qte_require(isinstance(name, str) and name.isidentifier(), "Effect name must identify a variable, such as 'dissolve', 'hpunch', 'vpunch' etc")

                    transition = getattr(renpy.store, name, None)

                    qte_require(callable(transition), "Unknown or invalid transition: " + name)
                    transitions.append(transition)

                qte_require(type(cue["always"]) is bool, "effect.always must be boolean, got: %r" % (cue["always"],))

                layers = cue["layers"]

                if layers is None:
                    layers = [None]

                else:
                    if isinstance(layers, str):
                        layers = [layers]

                    qte_require(isinstance(layers, (builtins.list, tuple)) and bool(layers), "effect.layers must be a layer name, a non-empty list or None, got: " + repr(layers))

                    for layer in layers:
                        qte_require(isinstance(layer, str) and layer in config.layers, "Unknown effect layer: " + repr(layer))

                options = [(transition, tuple(layers), cue["always"]) for transition in transitions]
                if name_choice is not None:
                    selected = qte_choice_index(name_choice, self.qte_manager.choice_history, choose)
                else:
                    selected = (renpy.random.randrange(len(options)) if choose and len(options) > 1 else 0)

                resolved.append(options[selected])

            return resolved

        def play(self, value):
            """Schedules effects and makes Ren'py play them"""

            resolved = self._resolve(value, choose=True)

            for transition, layers, always in resolved:
                for layer in layers:
                    renpy.transition(transition, layer=layer, always=always)

            if resolved:
                self.revision += 1
