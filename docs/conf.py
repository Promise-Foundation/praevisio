import os
import sys
from datetime import datetime

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath("../src"))


# -- Project information -----------------------------------------------------

project = "praevisio"
author = ""
copyright = f"{datetime.now():%Y}, {author}" if author else f"{datetime.now():%Y}"
try:
    import praevisio
    release = getattr(praevisio, "__version__", "0.0.0")
except Exception:
    release = "0.0.0"


# -- General configuration ---------------------------------------------------

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.todo",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.intersphinx",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

# Support Markdown with MyST
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "linkify",
]

# Auto-generate heading anchors to support #fragment cross-references in MyST
myst_heading_anchors = 3

templates_path = ["_templates"]
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
]

todo_include_todos = True

# Auto-generate summary pages for API
autosummary_generate = True

# Autodoc options
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}

# Napoleon settings for Google/NumPy style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = True


# -- Options for HTML output -------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_title = project

# Keep sidebar/navigation compact: show only top-level pages, not page sections
html_theme_options = {
    "navigation_depth": 1,  # do not expand into page sections in sidebar
    "titles_only": True,    # only show doc titles, not section titles
    "collapse_navigation": True,
}
