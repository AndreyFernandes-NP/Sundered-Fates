init -10 python:
    class QTEManager:
        """Responsible to run interactions and execute events for other callable modules"""

        def __init__(self):
            self.current = None
            self.events = []
            self.announced = False
            self.event_data = {}
            self.button_history = []
            self.choice_history = {}
            self.completed_result = None
        
        def prepare(self, definition):
            """Requester of all the events in the start hook, the main interaction only runs after it ends"""

            if self.current is not None:
                raise RuntimeError("[QTE CORE] Finish the current instance before preping another one")

            self.event_data = {}
            self.button_history = []
            self.choice_history = {}
            self.completed_result = None
            self.emit("start", definition)

        def start(self, definition):
            if self.current is not None:
                raise RuntimeError("[QTE CORE] Finish the previous instance before calling it again: %r" % (self.current,))
            
            self.current = QTEPatternRun(definition, self.event_data, self.button_history, self.choice_history)
            self.announced = False

        def set_event_data(self, key, value):
            if not isinstance(key, str) or not key.strip():
                raise ValueError("[QTE CORE] Event data keys must be non-empty strings")

            self.event_data[key] = value

            if self.completed_result is not None:
                self.completed_result["data"] = dict(self.event_data)
        
        def emit(self, name, definition, result=None):
            self.events.append({
                "name": name,
                "definition": definition,
                "result": result,
            })

        def update(self, dt, input_name=None):
            if self.current is None:
                raise RuntimeError("[QTE CORE] There's no instance available to update, got 'None'")

            if self.current.result is None and input_name is not None:
                self.current.input(input_name)
            
            if self.current.result is None:
                self.current.update(dt)

            self.events.extend(self.current.drain_events())

            if self.current.result is not None and not self.announced:
                name = ("success" if self.current.result["success"] else "failure")

                self.emit(name, self.current.definition, self.current.result)
                self.announced = True
            
            return self.current.result
        
        def drain_events(self):
            events = self.events
            self.events = []

            return events

        def collect(self):
            if self.current is None or self.current.result is None:
                raise RuntimeError("[QTE CORE] Previous instance has not been finished, end before calling collect")
            
            result = dict(self.current.result)
            result["data"] = dict(self.event_data)
            self.current = None
            self.completed_result = result

            return result
    
    class QTEContext:
        """The scope shared by a block of instructions and any branches inside it"""

        def __init__(self, event=None):
            self.event = event
            self.last_result = (None if event is None else event["result"])

    class QTEFrame:
        """A block of instructions and the context that it belongs to"""

        def __init__(self, steps, context):
            self.steps = steps
            self.index = 0
            self.context = context

    class QTERun:
        """Schedules script instructions, hooks and any interaction activation"""

        def __init__(self, script):
            self.stack = [QTEFrame(script["steps"], QTEContext())]
        
        @property
        def context(self):
            if not self.stack:
                raise RuntimeError("[QTE RUN] There's no active execution in the current context")
            
            return self.stack[-1].context

        @property
        def last_result(self):
            return self.context.last_result

        @last_result.setter
        def last_result(self, result):
            self.context.last_result = result
        
        def handle(self, event):
            """Schedule work only while executing queued instructions"""

            name = event["name"]
            definition = event["definition"]
            parent_context = self.context

            if name == "start":
                continuation = [{
                    "op": "_activate_qte",
                    "definition": definition,
                }]

                self.stack.append(QTEFrame(continuation, parent_context))
            
            elif name in ("success", "failure"):
                parent_context.last_result = event["result"]

                end_steps = definition.get("on_end", [])

                if end_steps:
                    self.stack.append(QTEFrame(end_steps, QTEContext(event)))
            
            else:
                raise RuntimeError(f"[QTE RUN] Unknown type of lifecycle event '{name}', should be either 'success' or 'failure'")
            
            steps = definition.get("on_" + name, [])

            if steps:
                self.stack.append(QTEFrame(steps, QTEContext(event)))

        def next_step(self):
            while self.stack:
                frame = self.stack[-1]

                if frame.index >= len(frame.steps):
                    self.stack.pop()
                    continue
                
                step = frame.steps[frame.index]
                frame.index += 1

                if step["op"] == "branch":
                    result = frame.context.last_result

                    if result is None:
                        raise RuntimeError("[QTE RUN] This block has no previous QTE result for its branch")
                    
                    branch = ("success" if result["success"] else "failure")

                    self.stack.append(QTEFrame(step[branch], frame.context))
                
                else:
                    return step

            raise RuntimeError("[QTE RUN] The script must reach an end step, ran into none and raised an error")
        
        def close(self):
            """Discards any pending hooks, branches or instructions"""

            self.stack = []
