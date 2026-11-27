# When starting to define things to be used don't forget to erase this and review what's going here and what's not future andrey

### IMPORTANT STORY DEFINITIONS/DEFAULTS
## Character Thoughts / Personality


### Error Handling and Notifications
define ERROR_PROTOCOL = {
        "http": _("HTTP Error"),
        "llm": _("LLM Error"),
        "generic": _("Error")
}

define ERROR_MESSAGES = {
        "no_internet": _("No internet connection available."),
        "http_failure": _("Failed to get response from server. See 'http_log.txt' for details."),
        "llm_warmup_failure": _("An error occurred during LLM warmup. See 'llm_log.txt' for details."),
        "llm_request_failure": _("An error occurred while processing your request. See 'llm_log.txt' for details.")
}