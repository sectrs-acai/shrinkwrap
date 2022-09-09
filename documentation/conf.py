# Copyright (c) 2022, Arm Limited.
#
# SPDX-License-Identifier: MIT


# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))


# -- Project information -----------------------------------------------------

project = 'Shrinkwrap'
copyright = '2022, Arm Limited'
author = 'Arm Limited'


# -- General configuration ---------------------------------------------------

#import sphinx_rtd_theme

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autosectionlabel',
    'sphinx_rtd_theme',
    'sphinx_copybutton',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = 'en'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

html_css_files = [
    'css/custom.css',
]

# Don't show the "Built with Sphinx" footer
html_show_sphinx = False

html_theme_options = {
    'collapse_navigation': False,
    'navigation_depth': 5,
    'prev_next_buttons_location': "both"
}

# -- Extension configuration -------------------------------------------------

# -- Options for autosectionlabel --------------------------------------------

# Prefix each section label with the name of the document it is in
autosectionlabel_prefix_document = True
# Only generate automatic section labels for document titles
autosectionlabel_maxdepth = 1

# -- Options for copybutton --------------------------------------------------
copybutton_prompt_text = r'\$ '
copybutton_prompt_is_regexp = True
copybutton_remove_prompts = True
copybutton_only_copy_prompt_lines = True
copybutton_copy_empty_lines = False
copybutton_line_continuation_character = "\\"
