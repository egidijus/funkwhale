#!/usr/bin/env python3
"""
This scripts handles all the heavy-lifting of parsing CSS files from ``fomantic-ui-css`` and:

1. Replace hardcoded values by their CSS vars counterparts, for easier theming
2. Strip unused styles and icons to reduce the final size of CSS

Updated files are not modified in place, but instead copied to another directory (``fomantic-ui-css/tweaked``), in order
to allow easy comparison detection of changes.

If you change this file, you'll need to run ``yarn run fix-fomantic-css`` manually for the changes
to be picked up. If the ``NOSTRIP`` environment variable is set, the second step will be skipped.
"""
import argparse
import os

STRIP_UNUSED = "NOSTRIP" not in os.environ

# Perform a blind replacement of some strings in all fomantic CSS files
GLOBAL_REPLACES = [
    # some selectors are repeated in the stylesheet, for some reason
    (".ui.ui.ui.ui", ".ui"),
    (".ui.ui.ui", ".ui"),
    (".ui.ui", ".ui"),
    (".icon.icon.icon.icon", ".icon"),
    (".icon.icon.icon", ".icon"),
    (".icon.icon", ".icon"),
    # actually useful stuff
    ("'Lato', 'Helvetica Neue', Arial, Helvetica, sans-serif", "var(--font-family)"),
    (".orange", ".vibrant"),
    ("#F2711C", "var(--vibrant-color)"),
    ("#FF851B", "var(--vibrant-color)"),
    ("#f26202", "var(--vibrant-hover-color)"),
    ("#e76b00", "var(--vibrant-hover-color)"),
    ("#cf590c", "var(--vibrant-active-color)"),
    ("#f56100", "var(--vibrant-active-color)"),
    ("#e76b00", "var(--vibrant-active-color)"),
    ("#e55b00", "var(--vibrant-focus-color)"),
    ("#f17000", "var(--vibrant-focus-color)"),
    (".teal", ".accent"),
    ("#00B5AD", "var(--accent-color)"),
    ("#009c95", "var(--accent-hover-color)"),
    ("#00827c", "var(--accent-active-color)"),
    ("#008c86", "var(--accent-focus-color)"),
    (".green", ".success"),
    ("#21BA45", "var(--success-color)"),
    ("#2ECC40", "var(--success-color)"),
    ("#16ab39", "var(--success-hover-color)"),
    ("#1ea92e", "var(--success-hover-color)"),
    ("#198f35", "var(--success-active-color)"),
    ("#25a233", "var(--success-active-color)"),
    ("#0ea432", "var(--success-focus-color)"),
    ("#19b82b", "var(--success-focus-color)"),
    (".blue", ".primary"),
    ("#2185D0", "var(--primary-color)"),
    ("#54C8FF", "var(--primary-color)"),
    ("#54C8FF", "var(--primary-color)"),
    ("#1678c2", "var(--primary-hover-color)"),
    ("#21b8ff", "var(--primary-hover-color)"),
    ("#1a69a4", "var(--primary-active-color)"),
    ("#0d71bb", "var(--primary-focus-color)"),
    ("#2bbbff", "var(--primary-focus-color)"),
    (".yellow", ".warning"),
    ("#FBBD08", "var(--warning-color)"),
    ("#FFE21F", "var(--warning-color)"),
    ("#eaae00", "var(--warning-hover-color)"),
    ("#ebcd00", "var(--warning-hover-color)"),
    ("#cd9903", "var(--warning-active-color)"),
    ("#ebcd00", "var(--warning-active-color)"),
    ("#daa300", "var(--warning-focus-color)"),
    ("#f5d500", "var(--warning-focus-color)"),
    (".red.", ".danger."),
    ("#DB2828", "var(--danger-color)"),
    ("#FF695E", "var(--danger-color)"),
    ("#d01919", "var(--danger-hover-color)"),
    ("#ff392b", "var(--danger-hover-color)"),
    ("#b21e1e", "var(--danger-active-color)"),
    ("#ca1010", "var(--danger-focus-color)"),
    ("#ff4335", "var(--danger-focus-color)"),
]

def discard_unused_icons(rule):
    """
    Add an icon to this list if you want to use it in the app.
    """
    used_icons = [
        ".angle",
        ".arrow",
        ".at",
        ".ban",
        ".bell",
        ".book",
        ".bookmark",
        ".check",
        ".clock",
        ".close",
        ".cloud",
        ".code",
        ".comment",
        ".copy",
        ".copyright",
        ".danger",
        ".database",
        ".delete",
        ".disc",
        ".down angle",
        ".download",
        ".dropdown",
        ".edit",
        ".ellipsis",
        ".eraser",
        ".external",
        ".eye",
        ".feed",
        ".file",
        ".forward",
        ".globe",
        ".hashtag",
        ".headphones",
        ".heart",
        ".home",
        ".hourglass",
        ".info",
        ".layer",
        ".lines",
        ".link",
        ".list",
        ".loading",
        ".lock",
        ".minus",
        ".mobile",
        ".music",
        ".paper",
        ".pause",
        ".pencil",
        ".play",
        ".plus",
        ".podcast",
        ".question",
        ".question  ",
        ".random",
        ".redo",
        ".refresh",
        ".repeat",
        ".rss",
        ".search",
        ".server",
        ".share",
        ".shield",
        ".sidebar",
        ".sign",
        ".spinner",
        ".step",
        ".stream",
        ".track",
        ".trash",
        ".undo",
        ".upload",
        ".user",
        ".users",
        ".volume",
        ".wikipedia",
        ".wrench",
        ".x",
    ]
    if ":before" not in rule["lines"][0]:
        return False

    return not match(rule, used_icons)


"""
Below is the main configuration object that is used for fine-grained replacement of properties
in component files. It also handles removal of unused selectors.

Example config for a component:

REPLACEMENTS = {
    # applies to fomantic-ui-css/components/component-name.css
    "component-name": {
        # Discard any CSS rule matching one of the selectors listed below
        # matching is done using a simple string search, so ``.pink`` will remove
        # rules applied to ``.pink``, ``.pink.button`` and `.pinkdark`
        "skip": [
            ".unused.variation",
            ".pink",
        ],
        # replace some CSS properties values in specific selectors
        (".inverted", ".dark"): [
            ("background", "var(--inverted-background)"),
            ("color", "var(--inverted-color)"),
        ],
        (".active"): [
            ("font-size", "var(--active-font-size)"),
        ],
    }
}

Given the previous config, the following style sheet:

.. code-block:: css

    .unsed.variation {
        color: yellow;
    }

    .primary {
        color: white;
    }
    .primary.pink {
        color: pink;
    }
    .inverted.primary {
        background: black;
        color: white;
        border-top: 1px solid red;
    }
    .inverted.primary.active {
        font-size: 12px;
    }

Would be converted to:

.. code-block:: css

    .primary {
        color: white;
    }
    .inverted.primary {
        background: var(--inverted-background);
        color: var(--inverted-color);
        border-top: 1px solid red;
    }
    .inverted.primary.active {
        font-size: var(--active-font-size);
    }

"""
REPLACEMENTS = {
    "site": {
        ("a",): [
            ("color", "var(--link-color)"),
            ("text-decoration", "var(--link-text-decoration)"),
        ],
        ("a:hover",): [
            ("color", "var(--link-hover-color)"),
            ("text-decoration", "var(--link-hover-text-decoration)"),
        ],
        ("body",): [
            ("background", "var(--site-background)"),
            ("color", "var(--text-color)"),
        ],
        ("::-webkit-selection", "::-moz-selection", "::selection",): [
            ("color", "var(--text-selection-color)"),
            ("background-color", "var(--text-selection-background)"),
        ],
        (
            "textarea::-webkit-selection",
            "input::-webkit-selection",
            "textarea::-moz-selection",
            "input::-moz-selection",
            "textarea::selection",
            "input::selection",
        ): [
            ("color", "var(--input-selection-color)"),
            ("background-color", "var(--input-selection-background)"),
        ],
    },
    "button": {
        "skip": [
            ".vertical",
            ".animated",
            ".active",
            ".olive",
            ".brown",
            ".teal",
            ".violet",
            ".purple",
            ".brown",
            ".grey",
            ".black",
            ".positive",
            ".negative",
            ".secondary",
            ".tertiary",
            ".facebook",
            ".twitter",
            ".google.plus",
            ".vk",
            ".linkedin",
            ".instagram",
            ".youtube",
            ".whatsapp",
            ".telegram",
        ],
        (".ui.orange.button", ".ui.orange.button:hover"): [
            ("background-color", "var(--button-orange-background)")
        ],
        (".ui.basic.button",): [
            ("background", "var(--button-basic-background)"),
            ("color", "var(--button-basic-color)"),
            ("box-shadow", "var(--button-basic-box-shadow)"),
        ],
        (".ui.basic.button:hover",): [
            ("background", "var(--button-basic-hover-background)"),
            ("color", "var(--button-basic-hover-color)"),
            ("box-shadow", "var(--button-basic-hover-box-shadow)"),
        ],
    },
    "card": {
        "skip": [
            ".inverted",
            ".olive",
            ".brown",
            ".teal",
            ".violet",
            ".purple",
            ".brown",
            ".grey",
            ".pink",
            ".black",
            ".vibrant",
            ".success",
            ".warning",
            ".danger",
            ".primary",
            ".secondary",
            ".horizontal",
            ".raised",
        ]
    },
    "checkbox": {
        (
            ".ui.toggle.checkbox label",
            ".ui.toggle.checkbox input:checked ~ label",
            '.ui.checkbox input[type="checkbox"]',
            ".ui.checkbox input:focus ~ label",
            ".ui.toggle.checkbox input:focus:checked ~ label",
            ".ui.checkbox input:active ~ label",
        ): [("color", "var(--form-label-color)"),],
        (".ui.toggle.checkbox label:before",): [
            ("background", "var(--input-background)"),
        ],
    },
    "divider": {
        (".ui.divider:not(.vertical):not(.horizontal)",): [
            ("border-top", "var(--divider)"),
            ("border-bottom", "var(--divider)"),
        ],
        (".ui.divider",): [("color", "var(--text-color)"),],
    },
    "dimmer": {
        (".ui.inverted.dimmer",): [
            ("background-color", "var(--dimmer-background)"),
            ("color", "var(--dropdown-color)"),
        ],
    },
    "dropdown": {
        "skip": [".error", ".info", ".success", ".warning",],
        (
            ".ui.selection.dropdown",
            ".ui.selection.visible.dropdown > .text:not(.default)",
            ".ui.dropdown .menu",
        ): [
            ("background", "var(--dropdown-background)"),
            ("color", "var(--dropdown-color)"),
        ],
        (".ui.dropdown .menu > .item",): [("color", "var(--dropdown-item-color)"),],
        (".ui.dropdown .menu > .item:hover",): [
            ("color", "var(--dropdown-item-hover-color)"),
            ("background", "var(--dropdown-item-hover-background)"),
        ],
        (".ui.dropdown .menu .selected.item",): [
            ("color", "var(--dropdown-item-selected-color)"),
            ("background", "var(--dropdown-item-selected-background)"),
        ],
        (".ui.dropdown .menu > .header:not(.ui)",): [
            ("color", "var(--dropdown-header-color)"),
        ],
        (".ui.dropdown .menu > .divider",): [("border-top", "var(--divider)"),],
    },
    "form": {
        "skip": [".inverted", ".success", ".warning", ".error", ".info",],
        ('.ui.form input[type="text"]', ".ui.form select", ".ui.input textarea"): [
            ("background", "var(--input-background)"),
            ("color", "var(--input-color)"),
        ],
        (
            '.ui.form input[type="text"]:focus',
            ".ui.form select:focus",
            ".ui.form textarea:focus",
        ): [
            ("background", "var(--input-focus-background)"),
            ("color", "var(--input-focus-color)"),
        ],
        (
            ".ui.form ::-webkit-input-placeholder",
            ".ui.form :-ms-input-placeholder",
            ".ui.form ::-moz-placeholder",
        ): [("color", "var(--input-placeholder-color)"),],
        (
            ".ui.form :focus::-webkit-input-placeholder",
            ".ui.form :focus:-ms-input-placeholder",
            ".ui.form :focus::-moz-placeholder",
        ): [("color", "var(--input-focus-placeholder-color)"),],
        (".ui.form .field > label", ".ui.form .inline.fields .field > label",): [
            ("color", "var(--form-label-color)"),
        ],
    },
    "grid": {
        "skip": [
            "wide tablet",
            "screen",
            "mobile only",
            "tablet only",
            "computer only",
            "computer reversed",
            "tablet reversed",
            "wide computer",
            "wide mobile",
            "wide tablet",
            "vertically",
            ".celled",
            ".doubling",
            ".olive",
            ".brown",
            ".teal",
            ".violet",
            ".purple",
            ".brown",
            ".grey",
            ".black",
            ".positive",
            ".negative",
            ".secondary",
            ".tertiary",
            ".danger",
            ".vibrant",
            ".warning",
            ".primary",
            ".success",
            ".justified",
            ".centered",
        ]
    },
    "icon": {"skip": discard_unused_icons},
    "input": {
        (".ui.input > input",): [
            ("background", "var(--input-background)"),
            ("color", "var(--input-color)"),
        ],
        (".ui.input > input:focus",): [
            ("background", "var(--input-focus-background)"),
            ("color", "var(--input-focus-color)"),
        ],
        (
            ".ui.input > input::-webkit-input-placeholder",
            ".ui.input > input::-moz-placeholder",
            ".ui.input > input:-ms-input-placeholder",
        ): [("color", "var(--input-placeholder-color)"),],
        (
            ".ui.input > input:focus::-webkit-input-placeholder",
            ".ui.input > input:focus::-moz-placeholder",
            ".ui.input > input:focus:-ms-input-placeholder",
        ): [("color", "var(--input-focus-placeholder-color)"),],
    },
    "item": {
        (".ui.divided.items > .item",): [("border-top", "var(--divider)"),],
        (".ui.items > .item > .content",): [("color", "var(--text-color)"),],
        (".ui.items > .item .extra",): [
            ("color", "var(--really-discrete-text-color)"),
        ],
    },
    "header": {
        "skip": [
            ".inverted",
            ".block",
            ".olive",
            ".brown",
            ".teal",
            ".violet",
            ".purple",
            ".brown",
            ".grey",
            ".black",
            ".pink",
        ],
        (".ui.header",): [("color", "var(--header-color)"),],
        (".ui.header .sub.header",): [("color", "var(--header-color)"),],
    },
    "label": {
        "skip": [
            ".olive",
            ".brown",
            ".teal",
            ".violet",
            ".purple",
            ".brown",
            ".grey",
            ".black",
            ".positive",
            ".negative",
            ".secondary",
            ".tertiary",
            ".facebook",
            ".twitter",
            ".google.plus",
            ".vk",
            ".linkedin",
            ".instagram",
            ".youtube",
            ".whatsapp",
            ".telegram",
            ".corner",
            "ribbon",
            "pointing",
            "attached",
        ],
    },
    "list": {
        "skip": [
            ".mini",
            ".tiny",
            ".small",
            ".large",
            ".big",
            ".huge",
            ".massive",
            ".celled",
            ".horizontal",
            ".bulleted",
            ".ordered",
            ".suffixed",
            ".inverted",
            ".fitted",
            "aligned",
        ],
        (".ui.list .list > .item a.header", ".ui.list .list > a.item"): [
            ("color", "var(--link-color)"),
            ("text-decoration", "var(--link-text-decoration)"),
        ],
        ("a:hover", ".ui.list .list > a.item:hover"): [
            ("color", "var(--link-hover-color)"),
            ("text-decoration", "var(--link-hover-text-decoration)"),
        ],
    },
    "loader": {
        "skip": [
            ".olive",
            ".brown",
            ".teal",
            ".violet",
            ".purple",
            ".brown",
            ".grey",
            ".black",
            ".pink",
            ".primary",
            ".vibrant",
            ".warning",
            ".success",
            ".danger",
            ".elastic",
        ],
        (".ui.inverted.dimmer > .ui.loader",): [("color", "var(--dimmer-color)"),],
    },
    "message": {
        "skip": [
            ".olive",
            ".brown",
            ".teal",
            ".violet",
            ".purple",
            ".brown",
            ".grey",
            ".black",
            ".pink",
            ".vibrant",
            ".primary",
            ".secondary",
            ".floating",
        ],
    },
    "menu": {
        "skip": [
            ".inverted.pointing",
            ".olive",
            ".brown",
            ".teal",
            ".violet",
            ".purple",
            ".brown",
            ".grey",
            ".black",
            ".vertical.tabular",
            ".primary.menu",
            ".pink.menu",
            ".vibrant.menu",
            ".warning.menu",
            ".success.menu",
            ".danger.menu",
            ".fitted",
            "fixed",
        ],
        (".ui.menu .item",): [("color", "var(--menu-item-color)"),],
        (".ui.vertical.inverted.menu .menu .item", ".ui.inverted.menu .item"): [
            ("color", "var(--inverted-menu-item-color)"),
        ],
        (".inverted-ui.menu .active.item",): [
            ("color", "var(--menu-inverted-active-item-color)"),
        ],
        (".ui.secondary.pointing.menu .active.item",): [
            ("color", "var(--secondary-menu-active-item-color)"),
        ],
        (
            ".ui.secondary.pointing.menu a.item:hover",
            ".ui.secondary.pointing.menu .active.item:hover",
        ): [("color", "var(--secondary-menu-hover-item-color)"),],
        (".ui.menu .ui.dropdown .menu > .item",): [
            ("color", "var(--dropdown-item-color) !important"),
        ],
        (".ui.menu .ui.dropdown .menu > .item:hover",): [
            ("color", "var(--dropdown-item-hover-color) !important"),
            ("background", "var(--dropdown-item-hover-background) !important"),
        ],
        (".ui.menu .dropdown.item .menu",): [
            ("color", "var(--dropdown--color)"),
            ("background", "var(--dropdown-background)"),
        ],
        (".ui.menu .ui.dropdown .menu > .active.item",): [
            ("color", "var(--dropdown-item-selected-color)"),
            ("background", "var(--dropdown-item-selected-background) !important"),
        ],
    },
    "modal": {
        (".ui.modal", ".ui.modal > .actions", ".ui.modal > .content"): [
            ("background", "var(--modal-background)"),
            ("border-bottom", "var(--divider)"),
            ("border-top", "var(--divider)"),
        ],
        (".ui.modal > .close.inside",): [("color", "var(--text-color)"),],
        (".ui.modal > .header",): [
            ("color", "var(--header-color)"),
            ("background", "var(--modal-background)"),
            ("border-bottom", "var(--divider)"),
            ("border-top", "var(--divider)"),
        ],
    },
    "search": {
        (
            ".ui.search > .results",
            ".ui.search > .results .result",
            ".ui.category.search > .results .category .results",
            ".ui.category.search > .results .category",
            ".ui.category.search > .results .category > .name",
            ".ui.search > .results > .message .header",
            ".ui.search > .results > .message .description",
        ): [
            ("background", "var(--dropdown-background)"),
            ("color", "var(--dropdown-item-color)"),
        ],
        (
            ".ui.search > .results .result .title",
            ".ui.search > .results .result .description",
        ): [("color", "var(--dropdown-item-color)"),],
        (".ui.search > .results .result:hover",): [
            ("color", "var(--dropdown-item-hover-color)"),
            ("background", "var(--dropdown-item-hover-background)"),
        ],
    },
    "segment": {
        "skip": [
            ".stacked",
            ".horizontal.segment",
            ".inverted.segment",
            ".circular",
            ".piled",
        ],
    },
    "sidebar": {
        (".ui.left.visible.sidebar",): [("box-shadow", "var(--sidebar-box-shadow)"),]
    },
    "statistic": {
        (".ui.statistic > .value", ".ui.statistic > .label"): [
            ("color", "var(--text-color)"),
        ],
    },
    "progress": {
        (".ui.progress.success > .label",): [("color", "var(--text-color)"),],
    },
    "table": {
        "skip": [
            ".marked",
            ".active",
            ".olive",
            ".brown",
            ".teal",
            ".violet",
            ".purple",
            ".brown",
            ".grey",
            ".black",
            ".padded",
            ".column.table",
            ".inverted",
            ".definition",
            ".error",
            ".negative",
            ".structured",
            "tablet stackable",
        ],
        (".ui.table", ".ui.table > thead > tr > th",): [
            ("color", "var(--text-color)"),
            ("background", "var(--table-background)"),
        ],
        (".ui.table > tr > td", ".ui.table > tbody + tbody tr:first-child > td"): [
            ("border-top", "var(--table-border)"),
        ],
    },
}


def match(rule, skip):
    if hasattr(skip, "__call__"):
        return skip(rule)
    for s in skip:
        for rs in rule["selectors"]:
            if s in rs:
                return True

    return False


def rules_from_media_query(rule):
    internal = rule["lines"][1:-1]
    return parse_rules("\n".join(internal))


def wraps(rule, internal_rules):
    return {
        "lines": [rule["lines"][0]]
        + [line for r in internal_rules for line in r["lines"]]
        + ["}"]
    }


def set_vars(component_name, rules):
    """
    Given rules parsed via ``parse_rules``, replace properties values when needed
    using ``REPLACEMENTS`` and ``GLOBAL_REPLACES``.

    Also remove unused styles if STRIP_UNUSED is set to True.
    """
    final_rules = []
    try:
        conf = REPLACEMENTS[component_name]
    except KeyError:
        return rules
    selectors = list(conf.keys()) + list()
    skip = None
    if STRIP_UNUSED:
        skip = conf.get("skip", [])
        try:
            skip = set(skip)
        except TypeError:
            pass

    for rule in rules:
        if rule["lines"][0].startswith("@media"):
            # manual handling of media queries, becaues our parser is really
            # simplistic
            internal_rules = rules_from_media_query(rule)
            internal_rules = set_vars(component_name, internal_rules)
            rule = wraps(rule, internal_rules)
            if len(rule["lines"]) > 2:
                final_rules.append(rule)
            continue

        if skip and match(rule, skip):
            # discard rule entirely
            continue

        matching = []
        for s in selectors:
            if set(s) & set(rule["selectors"]):
                matching.append(s)
        if not matching:
            # no replacements to apply, keep rule as is
            final_rules.append(rule)
            continue
        new_rule = {"lines": []}

        for m in matching:
            # the block match one of our replacement rules, so we loop on each line
            # and replace values if needed.
            replacements = conf[m]
            for line in rule["lines"]:
                for property, new_value in replacements:
                    if line.strip().startswith("{}:".format(property)):
                        new_property = "{}: {};".format(property, new_value)
                        indentation = " " * (len(line) - len(line.lstrip(" ")))
                        line = indentation + new_property
                        break
                new_rule["lines"].append(line)
        final_rules.append(new_rule)
    return final_rules


def parse_rules(text):
    """
    Really basic CSS parsers that stores selectors and corresponding properties. Only works
    because the source files have coma-separated selectors (one per line), and one
    property/value per line.

    Returns a list of dictionaries, each dictionarry containing the selectors and
    lines of of each block.
    """
    rules = []
    current_rule = None
    opened_brackets = 0
    current_selector = []
    for line in text.splitlines():
        if not current_rule and line.endswith(","):
            current_selector.append(line.rstrip(",").strip())
        elif line.endswith(" {"):
            # for media queries
            opened_brackets += 1
            if not current_rule:
                current_selector.append(line.rstrip("{").strip())
                current_rule = {
                    "lines": [",\n".join(current_selector) + " {"],
                    "selectors": current_selector,
                }
            else:
                current_rule["lines"].append(line)
        elif current_rule:
            current_rule["lines"].append(line)
            if line.strip() == "}":
                opened_brackets -= 1
                if not opened_brackets:
                    # move on to next rule
                    rules.append(current_rule)
                    current_rule = None
                    current_selector = []

    return rules


def serialize_rules(rules):
    """
    Convert rules back to valid CSS.
    """
    lines = []
    for rule in rules:
        for line in rule["lines"]:
            lines.append(line)

    return "\n".join(lines)


def iter_components(dir):
    for dname, dirs, files in os.walk(dir):
        for fname in files:
            if fname.endswith(".min.css"):
                continue
            if fname.endswith(".js"):
                continue
            if "semantic" in fname:
                continue
            if fname.endswith(".css"):
                yield os.path.join(dname, fname)


def replace_vars(source, dest):
    components = list(sorted(iter_components(os.path.join(source, "components"))))
    for c in components:
        with open(c, "r") as f:
            text = f.read()

        for s, r in GLOBAL_REPLACES:
            text = text.replace(s, r)
            text = text.replace(s.lower(), r)
            text = text.replace(s.upper(), r)
        rules = parse_rules(text)
        name = c.split("/")[-1].split(".")[0]
        updated_rules = set_vars(name, rules)
        text = serialize_rules(updated_rules)
        with open(os.path.join(dest, "{}.css".format(name)), "w") as f:
            f.write(text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Replace hardcoded values by CSS vars and strip unused rules")
    parser.add_argument(
        "source", help="Source path of the fomantic-ui-less distribution to fix"
    )
    parser.add_argument(
        "dest", help="Destination directory where fixed files should be written"
    )
    args = parser.parse_args()

    replace_vars(source=args.source, dest=args.dest)
