################################################################################
## EVENTS FILE
##
## Welcome to the Event Dispatcher System, or EDS for short! This is where all the 
## magic happens when scenes get called and we need to check for events and trigger
## any of them. It works by storing dictionary formatted data about events, their
## conditions and their effects, and then checking for when the player enters their
## specific scene or context, so that makes sure only the right stuff gets triggered.
## Spoiler Alert: even though the ids are the only most spoiler-y part, it could still
## reveal heavily story related stuff, so beware if you don't want to get spoiled!
################################################################################

default event_debug = False # Set this to True to enable debug prints for events

init -2 python:
    EVENTS_BY_SCENE = {}

    def add_event(ev: dict):
        scene = ev["scene"]
        ev_id = ev["id"]

        if scene not in EVENTS_BY_SCENE:
            EVENTS_BY_SCENE[scene] = []

            if ev_id not in EVENTS_BY_SCENE[scene]:
                EVENTS_BY_SCENE[scene].append(ev)

    def sort_events():
        for key, events in EVENTS_BY_SCENE.items():
            events.sort(key=lambda e: e.get("priority", 0), reverse=True)

    def can_trigger_event(ev: dict):
        ev_id = ev["id"]

        if ev.get("once", False) and ev_id in store.seen_events:
            if event_debug:
                print(f"Event {ev_id} already seen once, skipping.")

            return False

        cond = ev.get("condition")
        if cond is not None and not cond():
            if event_debug:
                print(f"Event {ev_id} condition not met, skipping.")

            return False

        return True
    
    def trigger_event(ev: dict):
        ev_id = ev["id"]
        
        if ev_id not in store.seen_events:
            store.seen_events.add(ev_id)

        effect = ev.get("effect")
        if effect is not None:
            if event_debug:
                print(f"Running effect for event {ev_id}...")

            effect()

        renpy.call(ev["label"])

    def check_event(target):
        events = EVENTS_BY_SCENE.get(target, [])

        for ev in events:
            if event_debug:
                print(f"Checking event {ev['id']} for scene {target}...")

            if can_trigger_event(ev):
                if event_debug:
                    print(f"Triggering event {ev['id']} for scene {target}...")

                trigger_event(ev)
                return True

        return False

    # Register all events from the evs_db into the system.
    # Even though the event data is stored in another variable, we need to add it to the system's internal storage for it to work,
    # and then sort it by priority. I prefer it this way cus I have a more visual organization of events per scene in the evs_db.
    for ev_list in evs_db.values():
        for ev in ev_list:
            add_event(ev)
    sort_events()


## Event data structure explanation:
# Each event in evs_db is organized by scene, containing a set of event dictionaries.
# Every event must have the following properties:
#
# "id":            Unique identifier for the event (needed for tracking seen_events)
# "scene":         The scene name this event triggers in
# "label":         The label to call when the event is triggered
# "priority":      Higher priority events trigger first (default: 0)
# "once":          If True, event only triggers once (default: False)
# "condition":     Lambda function that returns True/False to determine if event can trigger (optional)
# "effect":        Lambda function that runs before calling the label, good for side effects (optional)
#
## Example basic event:
# {
#     "id": "scene_ev01",
#     "scene": "myScene",
#     "label": "my_event_label",
#     "priority": 100,
#     "once": True,
# }
#
## Example with conditions and effects:
# {
#     "id": "scene_ev02",
#     "scene": "myScene",
#     "label": "my_event_label_2",
#     "priority": 50,
#     "once": False,
#     "condition": lambda: store.flag_name == True,
#     "effect": lambda: setattr(store, "another_flag", True),
# }
#
## Example of what I use:
# {
#     "id": "scene_ev03",
#     "scene": "myScene",
#     "label": "my_event_label_3",
#     "priority": 1000,             // see priority table below
#     "once": True,
#     "condition": lambda: store.evs_variables.get("templateVar", 0) == 1, // evs_variables is where I store variables related to events
#     "effect": lambda: setattr(store, "evs_flags", {"templateFlag"}),    // evs_flags is where I store flags related to events, which are just identifiers without values
# }

define evs_db = {
    "templateScene": {
        {
            "id": "templatescene_ev01",
            "scene": "templateScene",
            "label": "templatescene_event01",
            "priority": 1000,
            "once": True,
            "condition": lambda: True,
            "effect": lambda: setattr(store, "evs_variables", {"templateVar": 1}),
        },
        {
            "id": "templatescene_ev02",
            "scene": "templateScene",
            "label": "templatescene_event02",
            "priority": 100,
            "once": False,
            "condition": lambda: store.evs_variables.get("templateVar", 0) == 1,
            "effect": lambda: setattr(store, "evs_flags", {"templateFlag"}),
        },
        {
            "id": "templatescene_ev03",
            "scene": "templateScene",
            "label": "templatescene_event03",
            "priority": 0,
            "once": False,
            "condition": lambda: "templateFlag" in store.evs_flags,
            "effect": lambda: renpy.notify("Event 3 triggered!"),
        },
    }
}

init python:
    # Function database for events that conditions and effects can call. 
    # This is just to avoid having too much code in the lambda functions inside the event definitions, which can get messy.