init -5 python:
    QTE_SKINS = {
        "default": {
            "idle": "images/testing/ui/qte_test.png",
            "hover": None,
            "approach": "images/testing/ui/zoom_circle.png",
            "scale": 1.0,
            "base_size": 256,
        },

        "small_d": {
            "scale": 0.5,
        }
    }

    def qte_skin(name="default", overrides=None):
        """Copies a preset and applies any local overrides to the button skin"""

        qte_require(isinstance(name, str) and name in QTE_SKINS, "Unknown QTE skin: " + repr(name))

        if overrides is None:
            overrides = {}

        qte_require(isinstance(overrides, builtins.dict), "Visual override must be an object, instead got %r" % (overrides,))

        skin = dict(QTE_SKINS["default"])
        skin.update(QTE_SKINS[name])
        skin.update(overrides)

        allowed = {
            "idle",
            "hover",
            "approach",
            "scale",
            "base_size",
        }

        qte_require(set(skin) <= allowed, "There are unknown fields present in QTE skin, got: %r" % skin)
        qte_require(isinstance(skin["idle"], str) and bool(skin["idle"].strip()), "A skin needs at least an idle image")

        for key in ("hover", "approach"):
            value = skin[key]

            qte_require(value is None or (isinstance(value, str) and bool(value.strip())), key + " must be an image name/path or None")
        
        scale = skin["scale"]

        qte_require(qte_number(scale) and scale > 0, "Skin scale must be a positive number")

        if skin["approach"] is not None:
            qte_require(scale * 0.75 > 0.01, "Approach scale is too small for the approaching formula, must be bigger than 0.1")
        
        qte_require(type(skin["base_size"]) is int and skin["base_size"] > 0, "Skin base_size must be a positive integer")

        if skin["hover"] is None:
            skin["hover"] = skin["idle"]
        
        return skin
    
    class QTEButtonVisual:
        """Display an interaction button with specific skin values"""

        def __init__(self, interaction):
            self.interaction = interaction
            definition = interaction.definition

            self.skin = qte_skin(definition.get("skin", "default"), definition.get("visual"))
            self.scale = float(self.skin["scale"])
            self.box_size = max(1, int(self.skin["base_size"] * self.scale * 3))
            duration = interaction.duration

            self.button_fade = min(max(0.2, duration / 10.0), 0.5)
            self.approach_fade = min(0.2 + (duration / 10.0), 0.5)

            self.approach_start = self.scale * 3.0
            self.approach_end = self.scale * 0.75
            self.approach_duration = None

            if self.skin["approach"] is not None:
                self.approach_duration = (duration * (self.approach_start - self.approach_end) / (self.approach_start - 0.01))

        def animate_button(self, trans, st, at):
            elapsed = max(0.0, self.interaction.elapsed)

            trans.zoom = self.scale
            trans.alpha = min(1.0, elapsed / self.button_fade)

            return 0.0 if elapsed < self.button_fade else None

        def animate_approach(self, trans, st, at):
            elapsed = max(0.0, self.interaction.elapsed)
            duration = self.approach_duration

            if duration is None:
                trans.alpha = 0.0
                return None

            progress = min(1.0, elapsed / duration)
            trans.zoom = self.approach_start + (self.approach_end - self.approach_start) * progress

            if elapsed >= duration:
                trans.alpha = 0.0
                return None
            
            trans.alpha = min(1.0, elapsed / self.approach_fade)

            return 0.0