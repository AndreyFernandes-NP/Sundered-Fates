init -10 python:
    import re
    import posixpath

    SF_ASSETS = tuple(renpy.list_files())
    QTE_FRAME_CACHE = {}

    QTE_IMAGE_EXTENSIONS = {
        ".png",
        ".webp",
        ".jpg",
        ".jpeg",
        ".svg",
    }

    def qte_clip(source, duration=None, loop=False, scale=1.0, fit=False):
        """Describes a visual resource without starting its playback"""

        return {
            "source": source,
            "duration": duration,
            "loop": loop,
            "scale": scale,
            "fit": fit,
        }
    
    def qte_natural_key(value):
        """Sorts numbered names naturally, like name2 will always come first than name10"""

        return tuple((1, int(part)) if part.isdecimal() else (0, part.lower()) for part in re.split(r"(\d+)", value))

    def qte_get_frames(source):
        """Finds an ordered frame sequence by a prefix or directory"""

        source = source.replace("\\", "/")

        if source in QTE_FRAME_CACHE:
            return QTE_FRAME_CACHE[source]
        
        found = {}
        directory = source.endswith("/")

        pattern = re.compile(re.escape(source) + r"(?:[_-]?(\d+))?$")

        for path in SF_ASSETS:
            stem, ext = posixpath.splitext(path)

            if ext.lower() not in QTE_IMAGE_EXTENSIONS:
                continue

            if directory:
                if posixpath.dirname(path) + "/" != source:
                    continue
                
                key = qte_natural_key(posixpath.basename(stem))
            
            else:
                match = pattern.fullmatch(stem)

                if match is None:
                    continue
                
                key = (int(match.group(1)) if match.group(1) else 1)

            qte_require(key not in found, "Ambiguous animation frame: " + path)

            found[key] = path

        result = tuple(found[key] for key in sorted(found))
        qte_require(bool(result), "No frames found for: " + source)

        QTE_FRAME_CACHE[source] = result
        
        return result
    
    def qte_resolve_clip(value, duration=None):
        """Creates a clip based on a filename, sequence of frames or any images in Ren'py"""
        
        if isinstance(value, str):
            value = {"source": value}
        
        qte_require(isinstance(value, builtins.dict), "A clip must be a string or an object")

        allowed = {
            "source",
            "duration",
            "loop",
            "scale",
            "fit",
        }

        qte_require({"source"} <= set(value) <= allowed, "Invalid fields in clip section, got: %r" % repr(value))

        clip = qte_clip(value["source"])
        clip.update(value)

        if duration is not None:
            clip["duration"] = duration
        
        source = clip["source"]

        qte_require(isinstance(source, str) and bool(source.strip()), "Invalid clip source: %r" % repr(source))

        source = source.strip().replace("\\", "/")
        clip["source"] = source

        for key in ("loop", "fit"):
            qte_require(type(clip[key]) is bool, key + " must be boolean")
        
        qte_require(qte_number(clip["scale"]) and clip["scale"] > 0, "Invalid clip scale")

        ext = posixpath.splitext(source)[1].lower()

        if ext in QTE_IMAGE_EXTENSIONS:
            qte_require(renpy.loadable(source), "Image file not found: " + source)

            clip["kind"] = "frames"
            clip["frames"] = (source,)
        
        elif "/" not in source and renpy.has_image(source, exact=True):
            clip["kind"] = "native"
            clip["frames"] = ()
        
        else:
            clip["kind"] = "frames"
            clip["frames"] = qte_get_frames(source)

            if clip["duration"] is None:
                clip["duration"] = 1.0
        
        length = clip["duration"]

        qte_require(length is None or (qte_number(length) and length > 0), "Clip duration must be a positive integer or None")

        if clip["loop"]:
            qte_require(clip["kind"] == "frames" and length is not None, f"If '{clip["kind"]}' is 'frames' you should have a valid duration and frames for a loop, else, you must define any loop inside the ATL, definite this as false instead")

        return clip
