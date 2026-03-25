################################################################################
## ROUTES FILES
##
## Basically all of the relevant choices you'll get to choose between
## each scene and arc. Everything's inside a single defined variable,
## but it's well organized enough for me to keep track on. Beware of spoilers!
################################################################################

## Example data format
# "choiceDataName": {
#       "flag1": {"action": "call" | "jump", "target": "where_to_go"},
#       "flag2": {"action": "call" | "Jump", "target": "where_to_go2"},
#       ...
# }
#
## Example with a set of flags/variables
# "choiceDataName": {
#       "flag1": {"action": "call", "target": "and_we_go", "set": {"store_variable_name": 1, "store_variable_name": True}},
#       "flag2": {"action": "jump", "target": "go_to_idk", "set": {"store_variable_name": "Weak", "store_variable_name": 69}}
# }
#
## That's how it mostly works, be aware that every choice that uses imenu
## should return something like: return "flag1" / return "flag2"
## Dictionary use-case: choices can also return a dict:
## return {"action": "jump", "target": "hub_main"}
## and it'll work the same as the general use-case.

default route_db = {
    "templateChoice": {
        "option1": {"action": "call", "target": "go_to_this_label"},
        "option2": {"action": "call", "target": "go_to_another_label"},
        "option3": {"action": "jump", "target": "go_to_but_cancels_current_context"},
    }
}