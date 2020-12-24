"""
Converts iPhone images to pngs
"""

import argparse
import os

from wand.image import Image


def convert(source, dest):
    """
    Convert from HEIC format to PNG
    
    args:
        source: folder with HEIC photos
        dest: destination of converted photos
    """
    
    # Create the destination folder
    try:
        os.makedirs(dest)
    except OSError as e:
        pass
    
    # Create a list of only .HEIC image files
    heic_imgs = [file for file in os.listdir(source) if file.endswith('.HEIC')]
    
    # Loop through each and write as a png
    for file in heic_imgs:
        heic_name = os.path.join(source, file)
        png_name = os.path.join(dest, file).replace('.HEIC', '.png')
        
        img = Image(filename=heic_name)
        img.format = 'png'
        img.save(filename=png_name)
        img.close()
        print('Saved file ' + png_name)
    
def main():
    # Make parser object
    p = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    
    p.add_argument("source", help="source folder path")
    p.add_argument("dest", help="destination folder path")
        
    args = p.parse_args()
    
    convert(args.source, args.dest)
    
if __name__ == '__main__':
    main()
