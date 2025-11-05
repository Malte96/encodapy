import os
import sys
import subprocess
from pathlib import Path
sys.path.insert(0, os.path.abspath("../.."))
from sphinx.util import logging

# Recommended logger for Sphinx config/extensions
logger = logging.getLogger(__name__)


# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'EnCoDaPy'
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
    "myst_parser",
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

# GitHub "Edit on GitHub" Link
html_context = {
    "display_github": True,
    "github_user": "gewv-tu-dresden",
    "github_repo": "encodapy",
    "github_version": "main",
    "conf_py_path": "/docs/source/",
}

# Optional: Direct edit links in theme
html_theme_options = {
    "vcs_pageview_mode": "blob",
}


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

# Import of myst-parser settings / for markdown support
myst_config = {
    "enable_extensions": [
        "colon_fence",
        "deflist",
        "substitution",
        "tasklist",
        "attrs_block",
        "attrs_inline",
        "replacements",
        "include",
    ],
    "heading_anchors": 3,
}


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


def _generate_readme(app):

    readmes: dict(str, str)= {
        "README.md": "README_FOR_DOCS.md",
        "encodapy/components/readme.md": "COMPONENTS_README_FOR_DOCS.md"
    }

    # script is under docs/scripts relative to repo root
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "docs" / "scripts" / "generate_readme_for_docs.py"
    print("Generating README for docs using script:", str(script))
    if not script.exists():
        # falls das Skript fehlt: nur loggen, nicht abstürzen
        logger.warning("README generator script not found: %s", str(script))
        return

    # read repo info from html_context (set above in this file)
    owner = html_context.get("github_user") or html_context.get("github_org") or ""
    repo = html_context.get("github_repo") or ""
    branch = html_context.get("github_version") or html_context.get("github_branch") or "main"
    repo_root = Path(__file__).resolve().parents[2]  # docs/source -> repo_root

    for readme_src, output_name in readmes.items():
        cmd = [sys.executable, str(script), "--owner", owner, "--repo", repo, "--branch", branch,
               "--repo_root", str(repo_root),
               "--readme-src", readme_src,
               "--output_name", output_name]

        try:
            subprocess.check_call(cmd, cwd=str(repo_root))
            logger.info("README generator finished: %s", str(script))

        except subprocess.CalledProcessError as exc:
            logger.warning("README generator failed (non-zero exit): %s", exc)



def setup(app):
    app.connect("builder-inited", _generate_readme)
    app.connect("autodoc-process-docstring", suppress_module_docstring)
    # app.connect("autodoc-process-docstring", suppress_pydantic_parameters)
