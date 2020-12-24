## Using HEIC Images

Download and install ImageMagick and then use [Wand](https://docs.wand-py.org/en/0.6.4/). Make sure the pip install takes place in the conda environment if you are using one.

``` zsh
brew install imagemagick
pip install Wand
```

## Resizing and Cropping

Need to install the following package in order to be able to use the opencv imshow function with a conda environment ([reference](https://stackoverflow.com/questions/64838511/opencv-imshow-crashes-python-launcher-on-macos-11-0-1-big-sur)).

``` zsh
pip install opencv-python-headless
```

