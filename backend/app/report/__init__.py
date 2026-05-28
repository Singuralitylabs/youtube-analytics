"""Monthly report generation package.

Pipeline: ``builder`` (collect + compute deterministic data) ->
``author`` (Gemini API writes the interpretive sections) ->
``renderer`` (assemble final Markdown) -> ``slack`` (notify).

All modules reuse the existing collector singletons in
``app.collectors`` rather than going through the FastAPI HTTP layer.
"""
