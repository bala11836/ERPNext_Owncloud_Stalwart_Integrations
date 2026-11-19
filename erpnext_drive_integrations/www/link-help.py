"""Shown at the bare respond address (audit P6): it explains that only private links work. No data, no login."""
no_cache = 1


def get_context(context):
    context.no_cache = 1
    context.title = "Example Organization Constructions"
    context.web_include_js = []
    context.web_include_css = []
