default persistent.choosen_language = False
default persistent.endings_unlocked = []
default current_llm_job = None
default seen_labels = set()
default routes_number = []

init -2 python:
    def scene_register(label_name):
        if label_name not in store.seen_labels:
            store.seen_labels.add(label_name)
        return

    def seen_label(label_name):
        return label_name in store.seen_labels

    # Transitions
    menueffect = None
    charchange = dissolve
    scenechange = dissolve
    contextchange = fade
    flash = Fade(0.1, 0.0, 0.5, color="#FFFFFF")
    bigflash = Fade(0.2, 0.0, 0.7, color="#FFFFFF")

    # Vars
    from_splash = False

    # Other functions
    def chroma_animated(child, **kwargs):
        return animated_glitch(child, **kwargs)