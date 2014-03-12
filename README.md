PlotDevice Manual
=================

This repository contains the unassembled parts that make up the `doc` subdirectory of the
plotdevice module (plus a script to glue them together).

To build the manual, set up a virtualenv and install the dependencies, then run `build.py`.
It will chug through the source files and generate a `file://` url-friendly hierarchy of
pages in the `doc` subdirectory:

```sh
$ virtualenv env
$ source ./env/bin/activate
(env)$ pip -r requirements.txt # uses jinja, pygments, beautiful soup, & html5lib
(env)$ python build.py         # build the manual
(env)$ open doc/manual.html    # view the table of contents
```