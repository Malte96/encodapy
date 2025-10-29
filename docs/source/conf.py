import os
import sys
sys.path.insert(0, os.path.abspath("../.."))
# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'EnCoDaPy Config'
copyright = '2025, Martin Altenburger'
author = 'Martin Altenburger'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
    "sphinxcontrib.autodoc_pydantic",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pandas": ("https://pandas.pydata.org/docs/", None),
    "filip": ("https://rwth-ebc.github.io/FiLiP/master/docs/", None),
}


exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'


# Cross-Referencing für local class
autodoc_typehints_format = "short"
typehints_use_rtype = True
typehints_document_rtype = True

# autodoc default settings
autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
    "member-order": "bysource",
    "exclude-members": "__init__",
}


# Einstellungen für Typ-Hints: Typen in der Beschreibung ausgeben (klare Felder)
autodoc_typehints = "description"  # alternativ: "signature", "both"
# falls du voll-qualifizierte Typnamen vermeiden willst:
typehints_fully_qualified = False
always_document_param_types = False  # Keine automatischen Parameter-Dokumentationen
typehints_defaults = "comma"
simplify_optional_unions = False
typehints_use_signature = True
typehints_use_signature_return = True

# Napoleon Einstellungen - Parameter aus Docstrings verstecken
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = False
napoleon_use_param = False  # Versteckt :param: Abschnitte
napoleon_use_keyword = False  # Versteckt :keyword: Abschnitte
napoleon_use_rtype = True  # Behält :rtype: bei
napoleon_use_ivar = True  # Behält Instanzvariablen bei
napoleon_preprocess_types = True
napoleon_type_aliases = {
    'Union': '`typing.Union`',
    'Dict': '`typing.Dict`',
    'List': '`typing.List`',
    'Optional': '`typing.Optional`',
    'DataType': ':class:`filip.models.base.DataType`',
}

# pydantic-spezifische Einstellungen - für automodule
autodoc_pydantic_model_show_json = True
autodoc_pydantic_model_show_config_summary = False
autodoc_pydantic_field_list_validators = False
autodoc_pydantic_model_show_field_summary = False
autodoc_pydantic_model_show_validator_members = False
autodoc_pydantic_model_show_validator_summary = False
# Verstecke die automatisch generierten Parameter-Listen für Pydantic-Modelle
autodoc_pydantic_model_hide_paramlist = True


# Prevent display of docstrings
def suppress_module_docstring(app, what, name, obj, options, lines):
    """Entfernt alle Modul-Docstrings aus der Ausgabe."""
    if what == "module":
        lines[:] = []

def suppress_pydantic_parameters(app, what, name, obj, options, lines):
    """Entfernt Parameter-Sektionen aus Pydantic-Modellen."""
    if what == "class" and hasattr(obj, '__pydantic_core_schema__'):
        # Entferne Parameter-bezogene Zeilen aus dem Docstring
        in_parameters_section = False
        new_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.strip() == "Parameters" or line.strip().startswith("Parameters:"):
                # Finde das Ende der Parameters-Sektion
                in_parameters_section = True
                # Überspringe diese Zeile und die nachfolgenden Parameter
                i += 1
                while i < len(lines) and (
                    lines[i].strip() == "" or 
                    lines[i].startswith("    ") or 
                    lines[i].startswith("\t") or
                    not lines[i].strip().endswith(":")
                ):
                    i += 1
                continue
            else:
                new_lines.append(line)
                i += 1
        lines[:] = new_lines

import re


def setup(app):
    app.connect("autodoc-process-docstring", suppress_module_docstring)
    app.connect("autodoc-process-docstring", suppress_pydantic_parameters)
