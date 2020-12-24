"""
Resizes iPhone images from 3024x4032 to 800x600
transposing the first two dimensions before scaling
the image down
"""

import click
import cv2
import os
import matplotlib


def resize(image, scale):
    """
    args:
        image: image to be rescaled
        scale: ratio to shrink image by (0, 1]
    returns:
        image: scaled image
    """

    width, height, _ = image.shape
    new_dim = (int(height * scale), int(width * scale))
    return cv2.resize(src=image, dsize=new_dim, 
                      interpolation=cv2.INTER_LINEAR)

@click.command()
@click.argument('source')
def main(source):
    click.echo('Reading images from ' + source)
    
    images = [os.path.join(source, file)
              for file in os.listdir(source) if file.endswith('.png')]
    
    # Create output folder called 'scaled'
    parent_dir, _ = os.path.split(source)
    try:
        output_dir = os.path.join(parent_dir,'scaled')
        os.makedirs(output_dir)
    except OSError as e:
        pass
    
    for image_path in images:
        
        image = cv2.imread(image_path) 
        
        # iPhone image is 3024 x 4032 which is a 3:4 ratio
        # so no need to crop.. we transpose across the diaganol
        # We could also have rotated either direction by 90 degrees
        # but this was easier for now so we'll see how this works
        image = image.transpose(1, 0, 2)
        
        assert image.shape[0] == 3024
        assert image.shape[1] == 4032
        
        # Determine scaling ratio - as a numpy array the
        # training image dimensions are 600 x 800 
        ratio = 600 / image.shape[0]
        
        _, filename = os.path.split(image_path)
        print('Rescaling %s by a factor %.3f' % (filename, ratio))
        scaled_image = resize(image, ratio)
        
        # Visualize
        cv2.imshow('Scaled Image', scaled_image)
        cv2.waitKey(0)
        
        # Write
        cv2.imwrite(os.path.join(output_dir, filename), scaled_image)
        
if __name__ == '__main__':
    main()
    
