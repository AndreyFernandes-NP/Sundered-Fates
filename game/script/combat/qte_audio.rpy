init -5 python:
    import posixpath

    QTE_AUDIO_EXTENSIONS = {
        ".mp3",
        ".ogg",
        ".opus",
        ".wav",
    }

    class QTEAudio:
        """Validates and plays immediate sound effects during any action inside a QTE"""

        def __init__(self, qte_manager):
            self.qte_manager = qte_manager

        def resolve_source(self, source):
            qte_require(isinstance(source, str) and bool(source.strip()), "Invalid SFX source: %r" % (source,))

            source = source.strip().replace("\\", "/")
            has_extension = bool(posixpath.splitext(source)[1])
            has_directory = "/" in source
            requested = source[6:] if source.startswith("audio/") else source
            matches = []

            for path in SF_ASSETS:
                path = path.replace("\\", "/")
                if not path.startswith("audio/"):
                    continue

                stem, extension = posixpath.splitext(path)
                if not has_extension and extension.lower() not in QTE_AUDIO_EXTENSIONS:
                    continue

                relative_path = path[6:]
                relative_stem = stem[6:]

                if has_directory:
                    candidate = (relative_path if has_extension else relative_stem)
                    if candidate == requested:
                        matches.append(path)
                else:
                    candidate = (posixpath.basename(relative_path) if has_extension else posixpath.basename(relative_stem))
                    if candidate == requested:
                        matches.append(path)

            if len(matches) > 1:
                raise ValueError("[QTE AUDIO] Ambiguous SFX source %r, matches: %r" % (source, matches))

            if matches:
                return matches[0]

            qte_require(has_extension and renpy.loadable(source, directory="audio"), "Audio file not found or extension is required: " + source)

            return source

        def validate(self, value):
            self._resolve(value, choose=False)

        def resolve(self, value):
            return self._resolve(value, choose=True)

        def _resolve(self, value, choose):
            if value is None:
                return []

            if isinstance(value, (str, builtins.dict)):
                value = [value]

            qte_require(isinstance(value, (builtins.list, tuple)), "SFX must be a filename, an object, a list, or None")

            cues = []

            allowed = {
                "op", "source", "channel",
                "volume", "fadein", "fadeout",
            }

            for entry in value:
                if isinstance(entry, str):
                    entry = qte_sfx(entry)

                qte_require(isinstance(entry, builtins.dict), "Invalid SFX definition, make it a dictionary before calling")
                qte_require({"source"} <= set(entry) <= allowed, "Missing or unknown SFX fields, got: %r" % (entry,))
                qte_require(entry.get("op", "sfx") == "sfx", "Expected an sfx instruction, not %r" % (entry.get("op", "sfx"),))

                cue = qte_sfx(entry["source"])
                cue.update(entry)

                source_choice = qte_choice_info(cue["source"])
                sources = (source_choice["options"] if source_choice is not None else cue["source"])

                if isinstance(sources, str):
                    sources = [sources]

                qte_require(isinstance(sources, (builtins.list, tuple)) and bool(sources), "SFX source must be a filename or a non-empty list of filenames")

                options = {}
                for key in ("channel", "volume", "fadein", "fadeout"):
                    values = cue[key]
                    if isinstance(values, (builtins.list, tuple)):
                        qte_require(bool(values), key + " list cannot be empty")
                        qte_require(len(values) in (1, len(sources)), key + " list must contain one value or match the number of SFX sources")
                        options[key] = [
                            values[0] if len(values) == 1 else values[index]
                            for index in range(len(sources))
                        ]
                    else:
                        options[key] = [values] * len(sources)

                candidates = []

                for index, source in enumerate(sources):
                    channel = options["channel"][index]
                    volume = options["volume"][index]
                    fadein = options["fadein"][index]
                    fadeout = options["fadeout"][index]

                    source = self.resolve_source(source)
                    qte_require(isinstance(channel, str) and bool(channel.strip()), "Invalid SFX channel: %r" % (channel,))
                    qte_require(renpy.music.channel_defined(channel), "Unknown audio channel: " + repr(channel))
                    qte_require(qte_number(volume) and 0 <= volume <= 1, "SFX volume must be between 0 and 1")
                    qte_require(qte_number(fadein) and fadein >= 0, "fadein must be a non-negative number")
                    qte_require(qte_number(fadeout) and fadeout >= 0, "fadeout must be a non-negative number")

                    if channel == "audio":
                        qte_require(fadeout == 0, "The audio channel cannot fadeout sounds")

                    candidates.append({
                        "op": "sfx",
                        "source": source,
                        "channel": channel,
                        "volume": volume,
                        "fadein": fadein,
                        "fadeout": fadeout,
                    })

                if source_choice is not None:
                    selected = qte_choice_index(source_choice, self.qte_manager.choice_history, choose)
                else:
                    selected = (renpy.random.randrange(len(candidates)) if choose and len(candidates) > 1 else 0)

                cues.append(candidates[selected])

            return cues

        def play(self, value):
            cues = self.resolve(value)

            for cue in cues:
                renpy.music.play(
                    cue["source"],
                    channel=cue["channel"],
                    loop=False,
                    fadein=cue["fadein"],
                    fadeout=cue["fadeout"],
                    relative_volume=cue["volume"],
                )

            if cues:
                renpy.music.pump()
