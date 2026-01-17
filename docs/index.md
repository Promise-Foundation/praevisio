# praevisio Documentation

Welcome to the documentation site for the praevisio CLI tool.

This project follows Readme-Driven Development and an outside-in approach. The initial, authoritative description of the tool is the white paper below, which serves as the north star for implementation decisions.

Recent architecture note: application services are now split into focused modules (`hook_service.py`, `promise_service.py`, and `engine.py`). The older `services.py` module remains as a compatibility re-export.

## Contents

```{toctree}
:maxdepth: 1
:titlesonly:
:caption: Project Docs

white-paper
quickstart
api
tutorials/index
```

## Getting started

- To build these docs locally, see the top-level README for setup instructions.
