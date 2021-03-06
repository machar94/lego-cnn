"""
Mask R-CNN
Train on the lego dataset and implement color splash effect.

Copyright (c) 2018 Matterport, Inc.
Licensed under the MIT License (see LICENSE for details)
Written by Waleed Abdulla

------------------------------------------------------------

Usage: import the module (see Jupyter notebooks for examples), or run from
       the command line as such:

    # Train a new model starting from pre-trained COCO weights
    python3 lego.py train --dataset=/path/to/lego/dataset --weights=coco

    # Resume training a model that you had trained earlier
    python3 lego.py train --dataset=/path/to/lego/dataset --weights=last

    # Train a new model starting from ImageNet weights
    python3 lego.py train --dataset=/path/to/lego/dataset --weights=imagenet

    # Apply color splash to an image
    python3 lego.py splash --weights=/path/to/weights/file.h5 --image=<URL or path to file>

    # Apply color splash to video using the last weights you trained
    python3 lego.py splash --weights=last --video=<URL or path to file>
"""

import os
import sys
import json
import datetime
import numpy as np
import skimage.draw

import imgaug.augmenters as iaa

from keras.utils.vis_utils import plot_model

# Root directory of the project
ROOT_DIR = os.path.abspath("../../")

# Import Mask RCNN
sys.path.append(ROOT_DIR)  # To find local version of the library
from mrcnn.config import Config
from mrcnn import model as modellib, utils

# Path to trained weights file
COCO_WEIGHTS_PATH = os.path.join(ROOT_DIR, "mask_rcnn_coco.h5")

# Directory to save logs and model checkpoints, if not provided
# through the command line argument --logs
DEFAULT_LOGS_DIR = os.path.join(ROOT_DIR, "logs")

# polygon annotation file name
POLYGON_ANNOTATION_FILE_NAME = 'annotations.json'

############################################################
#  Configurations
############################################################


class LegoConfig(Config):
    """Configuration0 for training on the toy  dataset.
    Derives from the base Config class and overrides some values.
    """
    # Give the configuration a recognizable name
    NAME = "lego"

    # We use a GPU with 12GB memory, which can fit two images.
    # Adjust down if you use a smaller GPU.
    IMAGES_PER_GPU = 1                                              # MW kaggle and colab ran out of memory if I set to 2

    # Number of classes (including background)
    NUM_CLASSES = 1 + 14  # Background + lego classes

    # Number of training steps per epoch
    STEPS_PER_EPOCH = 1280                                          # MW it looks like batch size is always 1, meaning that this should correspond to the nummber of images to train

    VALIDATION_STEPS = 256                                          # MW it looks like batch size for validation data is also 1, meaning this should correspond to the number of images to evaluate

    # Define number of epochs
    NB_OF_EPOCHS = 5

    # Percent of positive ROIs used to train classifier/mask heads
    ROI_POSITIVE_RATIO = 0.33

    # Skip detections with < 90% confidence
    DETECTION_MIN_CONFIDENCE = 0.7                                  # default is 0.7, sollte kein Einfluss auf Training haben. Wird nur im DetectionLayer() verwendet, währen Inference.

    # Non-maximum suppression threshold for detection
    DETECTION_NMS_THRESHOLD = 0.3

    # Learning rate and momentum
    LEARNING_RATE = 0.001                                           # Default 0.001, in Retinanet I set it to 0.00001, if I use default mrcnn_class_losses do not get small enough, use 0.00001

    # Um die NN Grösse zu reduzieren, nimm kleinst mögliche Bildgrösse 
    # 800x600px die noch durch 64 teilbar ist -> 832
    IMAGE_MAX_DIM = 832

    # Enable and use RPN ROIs or disable RPN and use externally generated 
    # ROIs for training Keep this True for most situations. Set False if 
    # you want to train the head branches on ROI generated by code rather 
    # than the ROIs from the RPN. For example, to debug the classifier head 
    # without having to train the RPN. This esentially freezes the RPN
    # layers, disconnects the RPN losses from backpropagation and adds
    # a new input layer to replace the output from the RPN.
    USE_RPN_ROIS = True                                             # True = with RPN, False = externally generated

    PRE_NMS_LIMIT = 6000                                            # default 6000, for LPRN set to 2048
    
    # Build targets for training (anchors)
    RPN_TRAIN_ANCHOR_IOU_POS_TH = 0.9                               # Default 0.9, set slightly higher to show RPN to only accept anchors with high overlap
    RPN_TRAIN_ANCHOR_IOU_NEG_TH = 0.85                              # Default 0.85, set much higher, to ensure RPN ignores badly overlaping anchors for training I think with 0.6
                                                                    #              I should have still enough anchors

    RPN_NMS_THRESHOLD = 0.3                                         # Default 0.7, reduce to allow more anchors in final selection. Maybe I would exlude 
                                                                    # unintentially anchors that match the lego well. 

    # Length of square anchor side in pixels
    RPN_ANCHOR_SCALES = (80, 112, 144, 180, 256)

    # If USE_RPN_ROIS = False, choose to generate random ROIs or
    # ROIs from the GT bboxes for training. For inference it
    # will always use the GT boxes, hence this settin is ignored.
    USE_RANDOM_RPN_ROIS = False                                     # True = GT Boxes, False = Random
    
    # Enable and use the second stage (head branches including, classifier
    # bbo regressor and mask network). Set False if you want to train
    # RPN only. In this case USE_RPN_ROIS must be True. This will essentially
    # freeze all header layers and disconnect the losses from the header
    # leaving the RPN losses as only feedback for the backpropagation.
    USE_STAGE_TWO = True

    # Enable separate backbone for RPN and MRCNN (classifier, regression
    # and mask) network or use one backbone for all, like in the 
    # origninal Mask R-CNN implementation.
    USE_SEPARATE_BACKBONES = False

    # Choose backbone network architecture. Supported values are: resnet50, 
    # resnet101 and resnet18 whisch uses keras-resnet library 
    BACKBONE_RPN = "resnet18"
    BACKBONE_MRCNN = "resnet18"

    # This are the backbone filter configurations, the default settings 
    # and accordinng to wide residual network according to http://arxiv.org/pdf/1605.07146v1.pdf
    # This setting will change the Resnet filter configuration.
    BACKBONE_RESNET_BOTTLE_DEFAULT = {"S2": [64, 64, 256],   "S3": [128, 128, 512], "S4": [256, 256, 1024],   "S5": [512, 512, 2048]}
    BACKBONE_RESNET_BOTTLE_WIDER   = {"S2": [256, 256, 256], "S3": [512, 512, 512], "S4": [1024, 1024, 1024], "S5": [1024, 1024, 2048]}
    BACKBONE_RESNET_BASIC_DEFAULT  = {"S2": [64, 64],        "S3": [128, 128],      "S4": [256, 256],         "S5": [512, 512]}
    BACKBONE_RESNET_BASIC_WIDER    = {"S2": [160, 160],      "S3": [320, 320],      "S4": [640, 640],         "S5": [1280, 1280]}

     # Resnet backbone filter configuration
    BACKBONE_FITLERS_CONFIG = BACKBONE_RESNET_BASIC_DEFAULT

    #FPN_CLASSIF_FC_LAYERS_SIZE = 256                        # With LSTM cannot be more than 256                     
    #TRAIN_ROIS_PER_IMAGE = 20                               # Test in training (default 200), remove later
    POST_NMS_ROIS_INFERENCE = 1000                           # Test in interference (default 1000), remove later

    # Plot and save graph to file.
    PLOT_GRAPH = False                                       # None: to not plot, False: plot, True: plot nested / details

############################################################
#  Dataset
############################################################

class LegoDataset(utils.Dataset):

    def load_lego(self, dataset_dir, subset):
        """Load a subset of the Lego dataset.
        dataset_dir: Root directory of the dataset.
        subset: Subset to load: train or val
        """
        # Add classes. We have only one class to add.
        self.add_class("lego", 1, "0")
        self.add_class("lego", 2, "1")
        self.add_class("lego", 3, "2")
        self.add_class("lego", 4, "3")
        self.add_class("lego", 5, "4")
        self.add_class("lego", 6, "5")
        self.add_class("lego", 7, "6")
        self.add_class("lego", 8, "7")
        self.add_class("lego", 9, "8")
        self.add_class("lego", 10, "9")
        self.add_class("lego", 11, "10")
        self.add_class("lego", 12, "11")
        self.add_class("lego", 13, "12")
        self.add_class("lego", 14, "13")


        # Train or validation dataset?
        assert subset in ["train", "val", "eval"]
        dataset_dir = os.path.join(dataset_dir, subset)

        # Load annotations
        # VGG Image Annotator (up to version 1.6) saves each image in the form:
        # { 'filename': '28503151_5b5b7ec140_b.jpg',
        #   'regions': {
        #       '0': {
        #           'region_attributes': {},
        #           'shape_attributes': {
        #               'all_points_x': [...],
        #               'all_points_y': [...],
        #               'name': 'polygon'}},
        #       ... more regions ...
        #   },
        #   'size': 100202
        # }
        # We mostly care about the x and y coordinates of each region
        # Note: In VIA 2.0, regions was changed from a dict to a list.
        annotations = json.load(open(os.path.join(dataset_dir,POLYGON_ANNOTATION_FILE_NAME)))
        annotations = list(annotations.values())  # don't need the dict keys

        # The VIA tool saves images in the JSON even if they don't have any
        # annotations. Skip unannotated images.
        annotations = [a for a in annotations if a['regions']]

        # Add images
        for a in annotations:
            # Get the x, y coordinaets of points of the polygons that make up
            # the outline of each object instance. These are stores in the
            # shape_attributes (see json format above)
            # The if condition is needed to support VIA versions 1.x and 2.x.
            if type(a['regions']) is dict:

                assert subset in ["train", "val"]

                # Meine train und val daten schlussendlich doch nicht so wie VIA, lese diese direkt ein
                polygons = [r['shape_attributes'] for r in a['regions'].values()]   
            else:

                assert subset in ["eval"]

                # Bei dem VIA Format ist die class id am falschen Ort, wird hier korrigiert
                polygons = [r['shape_attributes'] for r in a['regions']]
                class_ids = [r['region_attributes'] for r in a['regions']]

                for i ,c in enumerate(class_ids):
                    polygons[i].update(class_ids[i])

            # load_mask() needs the image size to convert polygons to masks.
            # Unfortunately, VIA doesn't include it in JSON, so we must read
            # the image. This is only managable since the dataset is tiny.
            image_path = os.path.join(dataset_dir, a['filename'])
            image = skimage.io.imread(image_path)
            height, width = image.shape[:2]

            self.add_image(
                "lego",
                image_id=a['filename'],  # use file name as a unique image id
                path=image_path,
                width=width, height=height,
                polygons=polygons)

    def load_mask(self, image_id):
        """Generate instance masks for an image.
       Returns:
        masks: A bool array of shape [height, width, instance count] with
            one mask per instance.
        class_ids: a 1D array of class IDs of the instance masks.
        """
        # If not a lego dataset image, delegate to parent class.
        image_info = self.image_info[image_id]
        if image_info["source"] != "lego":
            return super(self.__class__, self).load_mask(image_id)

        # Convert polygons to a bitmap mask of shape
        # [height, width, instance_count]
        info = self.image_info[image_id]
        num_masks =  len(info["polygons"])
        mask = np.zeros([info["height"], info["width"], num_masks],
                        dtype=np.uint8)

        class_ids = np.empty(num_masks, dtype=int)

        for i, p in enumerate(info["polygons"]):

            # Get indexes of pixels inside the polygon and set them to 1
            rr, cc = skimage.draw.polygon(p['all_points_y'], p['all_points_x'])
            mask[rr, cc, i] = 1
            class_ids[i] = int(p['class_id']) + 1        # MW - must increment class number mrcnn internally to match class indexes, see line 93 


        # Return mask, and array of class IDs of each instance. Since we have
        # one class ID only, we return an array of 1s

        return mask.astype(np.bool), class_ids
    
    def load_bbox_gt(self, image_id):
        """Load ground truth bounding box.
        Returns:
        bbox: A bbox: [num_instances, (y1, x1, y2, x2)] with one mask per instance.
        class_ids: a 1D array of class IDs of the instance masks.
        """
        # If not a lego dataset image, delegate to parent class.
        image_info = self.image_info[image_id]
        if image_info["source"] != "lego":
            assert('Cannot get BBox, not a lego dataset.')

        info = self.image_info[image_id]
        num_bboxes =  len(info["polygons"])

        class_ids = np.empty(num_bboxes, dtype=int)
        bboxes_gt = np.empty((num_bboxes, 4), dtype=np.int32)

        for i, p in enumerate(info["polygons"]):

            # bbox is stored in json in the format [x1, y1, x2, y2], translate to [y1, x1, y2, x2]
            bboxes_gt[i] = np.array([p['bbox_gt'][1], p['bbox_gt'][0], p['bbox_gt'][3], p['bbox_gt'][2]])
            class_ids[i] = int(p['class_id'] + 1) # MW - must increment class number mrcnn internally to match class indexes, see line 93 

        return bboxes_gt, class_ids

    def image_reference(self, image_id):
        """Return the path of the image."""
        info = self.image_info[image_id]
        if info["source"] == "lego":
            return info["path"]
        else:
            super(self.__class__, self).image_reference(image_id)


def train(model, args, config):
    """Train the model."""
    # Training dataset.
    dataset_train = LegoDataset()
    dataset_train.load_lego(args.dataset, "train")
    dataset_train.prepare()

    # Validation dataset
    dataset_val = LegoDataset()
    dataset_val.load_lego(args.dataset, "val")
    dataset_val.prepare()

    # MW add augmentation like I did in Reginanet
    if args.enable_augmentation:
        print('Augmentation Enabled.')
        # Little augmentation (3)
        augmentation = iaa.Sometimes(0.8, [
            iaa.AdditiveGaussianNoise(loc=0, scale=(0.0, 0.015 * 255)),
            iaa.Add((-10, 10)),                                             # change brightness of images (by -10 to 10 RGB value of original value)
            iaa.AddToHueAndSaturation((-10, 10))                            # change hue and saturation
        ])

        # Normal augmentation (1) -> soweit schlechtere Resultate als mit "Little"
        # augmentation = iaa.Sometimes(0.8, [
        #     iaa.AdditiveGaussianNoise(loc=0, scale=(0.0, 0.03 * 255)),
        #     iaa.Add((-40, 40)),                                             # change brightness of images (by -40 to 40 RGB value of original value)
        #     iaa.AddToHueAndSaturation((-50, 50))                            # change hue and saturation
        # ])
        
    else:
        augmentation = None

    # *** This training schedule is an example. Update to your needs ***
    # Since we're using a very small dataset, and starting from
    # COCO trained weights, we don't need to train too long. Also,
    # no need to train all layers, just the heads should do it.

    # Train all
    if config.USE_STAGE_TWO and config.USE_RPN_ROIS:
        layers = 'all'

    # Train MRCNN only
    elif config.USE_STAGE_TWO and not config.USE_RPN_ROIS:
        layers = 'mrcnn_only'

    # Train RPN only
    elif not config.USE_STAGE_TWO and config.USE_RPN_ROIS:
        
        layers = 'rpn_only'

    else:
        assert('No valid layer training configuration.')

    print("Training '{}' network".format(layers))

    model.train(dataset_train, dataset_val,
                learning_rate=config.LEARNING_RATE,
                epochs=config.NB_OF_EPOCHS,
                layers=layers,
                augmentation=augmentation)


def color_splash(image, mask):
    """Apply color splash effect.
    image: RGB image [height, width, 3]
    mask: instance segmentation mask [height, width, instance count]

    Returns result image.
    """
    # Make a grayscale copy of the image. The grayscale copy still
    # has 3 RGB channels, though.
    gray = skimage.color.gray2rgb(skimage.color.rgb2gray(image)) * 255
    # Copy color pixels from the original color image where mask is set
    if mask.shape[-1] > 0:
        # We're treating all instances as one, so collapse the mask into one layer
        mask = (np.sum(mask, -1, keepdims=True) >= 1)
        splash = np.where(mask, image, gray).astype(np.uint8)
    else:
        splash = gray.astype(np.uint8)
    return splash


def detect_and_color_splash(model, image_path=None, video_path=None):
    assert image_path or video_path

    # Image or video?
    if image_path:
        # Run model detection and generate the color splash effect
        print("Running on {}".format(image_path))
        # Read image
        image = skimage.io.imread(image_path)
        # Detect objects
        r = model.detect([image], verbose=1)[0]
        # Color splash
        splash = color_splash(image, r['masks'])
        # Save output
        file_name = "splash_{:%Y%m%dT%H%M%S}.png".format(datetime.datetime.now())
        skimage.io.imsave(file_name, splash)
    elif video_path:
        import cv2
        # Video capture
        vcapture = cv2.VideoCapture(video_path)
        width = int(vcapture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(vcapture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = vcapture.get(cv2.CAP_PROP_FPS)

        # Define codec and create video writer
        file_name = "splash_{:%Y%m%dT%H%M%S}.avi".format(datetime.datetime.now())
        vwriter = cv2.VideoWriter(file_name,
                                  cv2.VideoWriter_fourcc(*'MJPG'),
                                  fps, (width, height))

        count = 0
        success = True
        while success:
            print("frame: ", count)
            # Read next image
            success, image = vcapture.read()
            if success:
                # OpenCV returns images as BGR, convert to RGB
                image = image[..., ::-1]
                # Detect objects
                r = model.detect([image], verbose=0)[0]
                # Color splash
                splash = color_splash(image, r['masks'])
                # RGB -> BGR to save image to video
                splash = splash[..., ::-1]
                # Add image to video writer
                vwriter.write(splash)
                count += 1
        vwriter.release()
    print("Saved to ", file_name)


############################################################
#  Training
############################################################

def main(args=None):
    import argparse

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Train Mask R-CNN to detect balloons.')
    parser.add_argument("command",
                        metavar="<command>",
                        help="'train' or 'splash'")
    parser.add_argument('--dataset', required=False,
                        metavar="/path/to/lego/dataset/",
                        help='Directory of the Lego dataset')
    parser.add_argument('--weights', required=False,
                        metavar="/path/to/weights.h5",
                        help="Path to weights .h5 file or 'coco'")
    parser.add_argument('--logs', required=False,
                        default=DEFAULT_LOGS_DIR,
                        metavar="/path/to/logs/",
                        help='Logs and checkpoints directory (default=logs/)')
    parser.add_argument('--image', required=False,
                        metavar="path or URL to image",
                        help='Image to apply the color splash effect on')
    parser.add_argument('--video', required=False,
                        metavar="path or URL to video",
                        help='Video to apply the color splash effect on')
    parser.add_argument('--epochs', required=False,
                        default=1,
                        metavar="number of epochs",
                        help='Indicate number of epochs to run.')
    parser.add_argument('--steps-per-epoch', required=False,
                        metavar="number of steps/images per epoch",
                        help='number of steps/images per epoch for training data.')
    parser.add_argument('--validation-steps', required=False,
                        metavar="number of steps/images per epoch",
                        help='number of steps/images per epoch for validation data.')
    parser.add_argument('--enable-augmentation',required=False,
                        action='store_true',
                        help='Enable or disable augmentation.')

    args = parser.parse_args(args)

    # Validate arguments
    if args.command == "train":
        assert args.dataset, "Argument --dataset is required for training"
    elif args.command == "evaluate":
        assert args.image or args.video,\
               "Provide --image or --video to apply color splash"

    print("Weights: ", args.weights)
    print("Dataset: ", args.dataset)
    print("Logs: ", args.logs)

    # Configurations
    if args.command == "train":
        config = LegoConfig()
    else:
        class TrainConfig(LegoConfig):
            # Set batch size to 1 since we'll be running inference on
            # one image at a time. Batch size = GPU_COUNT * IMAGES_PER_GPU
            GPU_COUNT = 1
            IMAGES_PER_GPU = 1
        config = TrainConfig()

    # Set arguments 
    if args.epochs is not None:
        config.NB_OF_EPOCHS = int(args.epochs)
    if args.steps_per_epoch is not None:
        config.STEPS_PER_EPOCH = int(args.steps_per_epoch)
    if args.validation_steps is not None:
        config.VALIDATION_STEPS = int(args.validation_steps)

    config.display()

    # Create model
    if args.command == "train":
        model = modellib.MaskRCNN(mode="training", config=config,
                                model_dir=args.logs)
    else:
        model = modellib.MaskRCNN(mode="inference", config=config,
                                model_dir=args.logs)
    
    # Show final model graph
    if config.PLOT_GRAPH is not None:

        if config.PLOT_GRAPH:
            plot_model(model.keras_model, to_file='maskrcnn_graph.png', show_shapes=True, show_layer_names=True, expand_nested=True)
        else:
            plot_model(model.keras_model, to_file='maskrcnn_graph.png', show_shapes=True, show_layer_names=True)
        # Print model
        model.keras_model.summary()

    if args.weights is not None:

        # Select weights file to load
        if args.weights.lower() == "coco":
            weights_path = COCO_WEIGHTS_PATH
            # Download weights file
            if not os.path.exists(weights_path):
                utils.download_trained_weights(weights_path)
        elif args.weights.lower() == "last":
            # Find last trained weights
            weights_path = model.find_last()
        elif args.weights.lower() == "imagenet":
            # Start from ImageNet trained weights
            weights_path = model.get_imagenet_weights()
        else:
            weights_path = args.weights

        # Load weights
        print("Loading weights ", weights_path)
        if args.weights.lower() == "coco":
            # Exclude the last layers because they require a matching
            # number of classes
            model.load_weights(weights_path, by_name=True, exclude=[
                "mrcnn_class_logits", "mrcnn_bbox_fc",
                "mrcnn_bbox", "mrcnn_mask"])
        else:
            model.load_weights(weights_path, by_name=True)

    # Train or evaluate
    if args.command == "train":
        train(model, args, config)
    elif args.command == "evaluate":
        detect_and_color_splash(model, image_path=args.image, video_path=args.video)
    else:
        print("'{}' is not recognized. "
              "Use 'train' or 'evaluate'".format(args.command))
    
    weights_path = model.find_last()

    return weights_path

if __name__ == '__main__':
    main()
