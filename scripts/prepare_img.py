"""
Interactive script for cropping images to match
the expected model input size
"""

import click
import cv2
import os
import matplotlib

def crop_image(image_path):
    
    image = cv2.imread(image_path)
    
    # To Do:
    # 1. Figure out max crop size
    # 2. Resize image 
    y = 0
    x = 0
    h = 300
    w = 510
    
    crop_image = image[x:, y:]
    cv2.imshow('Cropped', crop_image)
    cv2.waitKey(0)

@click.command()
@click.argument('source')
def main(source):
    click.echo('Reading images from ' + source)
    
    images = [os.path.join(source, file)
              for file in os.listdir(source) if file.endswith('.png')]
    
    for png_image in images:
        crop_image(png_image)
    
if __name__ == '__main__':
    main()
    
