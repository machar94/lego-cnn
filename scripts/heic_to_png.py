"""
Converts iPhone images to pngs
"""

import argparse
import os

from wand.image import Image

#    SourceFolder="K:/HeicFolder"
#    TargetFolder="K:/JpgFolder"

#    for file in os.listdir(SourceFolder):
#       SourceFile=SourceFolder + "/" + file
#       TargetFile=TargetFolder + "/" + file.replace(".HEIC",".JPG")
    
#       img=Image(filename=SourceFile)
#       img.format='jpg'
#       img.save(filename=TargetFile)
#       img.close()
    
def convert(source, dest):
    
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
