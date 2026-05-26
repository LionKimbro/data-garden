# Shared procedural namespace wiring for the first monolith-to-package split.

from data_garden import ui, inspector, file_ops, history, runtime
from data_garden.continuity import input_and_organisms
from data_garden.discrete import events, reducer
from data_garden.projection import camera, render
from data_garden.world import model

MODULES = [
    ui,
    input_and_organisms,
    camera,
    events,
    reducer,
    model,
    render,
    inspector,
    file_ops,
    history,
    runtime,
]


def wire():
    symbols = {}
    for module in MODULES:
        for name, value in module.__dict__.items():
            if name.startswith('_'):
                continue
            if getattr(value, '__module__', None) == module.__name__:
                symbols[name] = value
    for module in MODULES:
        module.__dict__.update(symbols)
    return symbols
