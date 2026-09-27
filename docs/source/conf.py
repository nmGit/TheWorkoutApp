"""Sphinx configuration for the WorkoutApp documentation."""

project = "WorkoutApp"
copyright = "2026, Noah Meltzer"
author = "Noah Meltzer"
release = "0.1.0"

extensions = [
    "myst_parser",
    "sphinx.ext.duration",
    "sphinx.ext.autosectionlabel",
    "sphinx_copybutton",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

autosectionlabel_prefix_document = True

html_theme = "furo"
html_static_path = ["_static"]
html_title = "WorkoutApp Docs"

html_theme_options = {
    "sidebar_hide_name": False,
}
