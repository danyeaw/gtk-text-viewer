# GTK Text Viewer

A GTK 4 text editor application built with Python and PyGObject with code
highlighting support from GtkSource.

## Installation

### Prerequisites (Conda)

Install the required dependencies using conda:

```bash
conda install -c conda-forge python pygobject gtk4 meson ninja gettext
```

### Build

```bash
meson setup builddir --prefix=$PWD/install
ninja -C builddir install
```

### Run

```bash
./install/bin/text-viewer
```

### Credits

Based on the 
[GTK Getting Started Tutorial](https://developer.gnome.org/documentation/tutorials/beginners/getting_started.html) 
which is licensed CC0.

