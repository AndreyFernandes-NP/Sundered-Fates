default qte_active_session = None

init -10 python:

    class QTEActor:
        """
        An actor that exists within any particular scene.

        actor_id identifies this instance inside our current scene,
        while character_id is the original character inside ch_db when it exists.
        """

        def __init__(self, actor_id, character_id, team, stats):
            self.actor_id = actor_id
            self.character_id = character_id
            self.team = team

            # Each actor gets their own copy of their original stats
            self.stats = dict(stats)
    
    class QTESession:
        """
        Contains everything that belongs to any interactive scene,
        it could hold like several QTEs, dialogue, narrative effects and
        also multiple characters at the same time (known as actors).
        """

        def __init__(self, scene_id, player_stats, cast, char_registry):
            self.scene_id = scene_id
            self.state = "active"

            self.actors = {}
            self.actions = []
            self.waiting = None

            self.qte = QTEManager()
            self.stage = QTEStage(self)
            self.audio = QTEAudio(self.qte)
            self.effects = QTEEffects(self.qte)

            self.run = None
            self.qte_results = []
            
            self._qte_tick_at = None
            self._qte_ui_signature = None

            if player_stats is not None:
                self.actors["player"] = QTEActor(actor_id="player", character_id=None, team="player", stats=player_stats)
            
            if (isinstance(cast, (list, tuple)) and len(cast) == 3 and not any(isinstance(value, (list, tuple)) for value in cast)):
                cast = (cast,)

            for actor_id, character_id, team in cast:
                if actor_id == "player" or actor_id in self.actors:
                    raise ValueError(f"[QTE SESSION] Duplicate or reserved actor ID: '{actor_id}'")

                if character_id not in char_registry:
                    raise ValueError(f"[QTE SESSION] Character '{character_id}' was not found in {char_registry} while making scene '{scene_id}'")
                
                character = char_registry[character_id]

                self.actors[actor_id] = QTEActor(
                    actor_id=actor_id, 
                    character_id=character_id, 
                    team=team, 
                    stats={
                        "power": character.power,
                        "agi": character.agi,
                        "vit": character.vit,
                    },
                )

        def actor(self, actor_id):
            """Returns any actor in a scene by their ID"""

            if actor_id not in self.actors:
                raise ValueError(f"[QTE SESSION] Actor '{actor_id}' is not in scene '{self.scene_id}'")
            
            return self.actors[actor_id]
        
        def _require_state(self, expected):
            """Catches calls made at any wrong point in a scene"""

            if self.state != expected:
                # While this yes, could be a little bit 'bothersome' to crash if I just want to guarantee something is paused,
                # it's also just a way to force you (and me) have good coding practice to always know the state of a scene
                # before whenever making any type of call, and to debug whenever something truly breaks or doesn't go as planned.

                raise RuntimeError(f"[QTE SESSION] Scene '{self.scene_id}' is '{self.state}', expected: '{expected}'")
            
        def pause(self):
            self._require_state("active")
            self._qte_tick_at = None
            self.state = "paused"
        
        def resume(self):
            self._require_state("paused")
            self._qte_tick_at = None
            self.state = "active"

        def adjust_stat(self, actor_id, stat, amount, operation="set"):
            """Changes any actor stat during a scene and for that scene ONLY"""

            self._require_state("active")
            actor = self.actor(actor_id)

            if stat not in actor.stats:
                raise ValueError(f"[QTE SESSION] Actor '{actor_id}' has no stat named '{stat}'")
            
            match operation:
                case "set" | "override" | "replace":
                    actor.stats[stat] = amount

                case "sum":
                    actor.stats[stat] += amount
                
                case "sub" | "subtract":
                    actor.stats[stat] -= amount
                
                case "mult" | "multiply":
                    actor.stats[stat] *= amount
                
                case "div" | "divide":
                    if amount != 0:
                        actor.stats[stat] /= amount
                    else:
                        raise ValueError(f"[QTE SESSION] Can't divide by 0, baka! Fix that in your adjust_stat call")
                
                case _:
                    raise ValueError(f"[QTE SESSION] Invalid operation '{operation}' received at adjust_stat")
            
            return actor.stats[stat]

        def record_action(self, action_id, execution, resolution, source=None, target=None):
            """Records what was attempted and how it was resolved in a scene"""

            self._require_state("active")

            for actor_id in (source, target):
                if actor_id is not None:
                    self.actor(actor_id)
            
            self.actions.append({
                "action": action_id,
                "execution": execution,
                "resolution": resolution,
                "source": source,
                "target": target,
            })
        
        def begin_wait(self, waiter):
            """Hello sir, would you mind some fine waiting time? Seconds? Minutes? Just call me, the Waiter- Ohohoho~"""
            self._require_state("active")

            if self.waiting is not None or self.qte.current is not None:
                raise RuntimeError("[QTE SESSION] There's another Wait currently being executed")
            
            if not isinstance(waiter, (QTEDelay, QTEPlayback)):
                raise RuntimeError("[QTE SESSION] Invalid type of Wait")
            
            if isinstance(waiter, QTEPlayback):
                qte_require(waiter.duration is not None and not waiter.clip["loop"], "Cannot wait while there's an animation being looped, stop that first")
            
            self.waiting = waiter
            self._qte_tick_at = None
        
        def end_wait(self):
            if self.waiting is None:
                raise RuntimeError("[QTE SESSION] There's no wait being executed to unwait")
            
            waiter = self.waiting

            if waiter.cancelled or not waiter.done:
                raise RuntimeError("[QTE SESSION] Playback was interrupted before completion")
            
            self.waiting = None
            self._qte_tick_at = None
        
        def update(self, dt, input_name=None):
            if self.state == "paused":
                return None
            
            self._require_state("active")

            qte_require(qte_number(dt) and dt >= 0, "Invalid scene delta time")

            self.stage.update(dt)

            if isinstance(self.waiting, QTEDelay):
                self.waiting.update(dt)
            
            if self.qte.current is not None:
                return self.update_qte(dt, input_name)

            if self.waiting is not None:
                if self.waiting.done or self.waiting.cancelled:
                    return True
            
            return None
                
        def prepare_qte(self, definition):
            self._require_state("active")

            if self.run is None:
                raise RuntimeError("[QTE SESSION] A script should be running to start any QTE")
            
            self.qte.prepare(definition)
            self.dispatch_qte_events()

        def start_qte(self, definition):
            self._require_state("active")

            self.qte.start(definition)
            self._qte_tick_at = None
        
        def dispatch_qte_events(self):
            if self.run is None:
                raise RuntimeError("[QTE SESSION] A script should be running to start any QTE")

            for event in self.qte.drain_events():
                if event["name"] in ("press", "miss"):
                    hook_name = "on_" + event["name"]

                    for step in event["definition"][hook_name]:
                        self.apply_feedback(step)

                else:
                    self.run.handle(event)
        
        def update_qte(self, dt, input_name=None):
            if self.state == "paused":
                return None
            
            self._require_state("active")

            result = self.qte.update(dt, input_name)
            self.dispatch_qte_events()

            return result

        def collect_qte(self):
            self._require_state("active")

            result = self.qte.collect()
            self.qte_results.append(result)

            return result
        
        def end_run(self):
            self._require_state("active")

            if self.run is None or self.qte.current is not None or self.waiting is not None:
                raise RuntimeError("[QTE SESSION] There's shouldn't be any active QTE running or you should only call this when there's a script running.")
            
            self.run.close()
            self.run = None
            self._qte_tick_at = None
        
        def apply_feedback(self, step):
            self._require_state("active")
            step = qte_resolve_event_refs(step, self)
            op = step["op"]

            if op == "sfx":
                self.audio.play(step)
                return None
            
            if op == "effect":
                self.effects.play(step)
                return None

            if op == "data_set":
                self.qte.set_event_data(step["key"], copy.deepcopy(step["value"]))
                return None

            if op in ("show", "play"):
                cues = self.audio.resolve(step.get("sfx"))
                self.effects.validate(step.get("effect"))

                playback = self.stage.apply(step)
                self.audio.play(cues)
                self.effects.play(step.get("effect"))

                return playback

            raise ValueError("[QTE SESSION] Unsupported feedback operation: " + repr(op))
        
        def finish(self, outcome):
            """Closes the session and gives the caller its final result"""

            self._require_state("active")

            if not isinstance(outcome, str) or not outcome.strip():
                raise ValueError(f"[QTE SESSION] Scene '{self.scene_id}' must return an outcome")
            
            if self.qte.current is not None or self.run is not None or self.waiting is not None:
                raise RuntimeError("[QTE SESSION] End the current execution before finishing")
            
            actors = {}

            for actor_id, actor in self.actors.items():
                actors[actor_id] = {
                    "character_id": actor.character_id,
                    "team": actor.team,
                    "stats": dict(actor.stats),
                }
            
            self.state = "finished"

            return {
                "scene": self.scene_id,
                "outcome": outcome,
                "actors": actors,
                "actions": [dict(action) for action in self.actions],
                "qtes": [dict(result) for result in self.qte_results],
            }
        
label qte_scene(scene_id, scene_label=None, player_stats=None, cast=(), script=None):
    python:
        if qte_active_session is not None:
            raise RuntimeError(f"[QTE SESSION] Tried making another scene upon an existing one, current active: {qte_active_session.scene_id}, attempted: {scene_id}")
        
        if (scene_label is None) == (script is None):
            raise ValueError(f"[QTE SESSION] Provide exactly one of 'scene_label' or 'script', not both")
        
        if scene_label is not None and not renpy.has_label(scene_label):
            raise ValueError(f"[QTE SESSION] Scene label '{scene_label}' does not exist")
        
        renpy.dynamic("qte_active_session")

        qte_active_session = QTESession(
            scene_id=scene_id,
            player_stats=player_stats,
            cast=cast,
            char_registry=ch_db,
        )
    
    if script is not None:
        call qte_execute(qte_active_session, script) from qte_session_after_script
    else:
        call expression scene_label pass (qte_active_session) from qte_session_after_scene

    return qte_active_session.finish(_return)