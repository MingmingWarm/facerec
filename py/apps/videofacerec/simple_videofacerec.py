#    Copyright (c) 2012. Philipp Wagner <bytefish[at]gmx[dot]de>.
#    Released to public domain under terms of the BSD Simplified license.
#
#    Redistribution and use in source and binary forms, with or without
#    modification, are permitted provided that the following conditions are met:
#        * Redistributions of source code must retain the above copyright
#          notice, this list of conditions and the following disclaimer.
#        * Redistributions in binary form must reproduce the above copyright
#          notice, this list of conditions and the following disclaimer in the
#          documentation and/or other materials provided with the distribution.
#        * Neither the name of the organization nor the names of its contributors 
#          may be used to endorse or promote products derived from this software 
#          without specific prior written permission.
#
#    See <http://www.opensource.org/licenses/bsd-license>
import logging
# cv2 and helper:
import cv2
from helper.common import *
from helper.video import *
# add facerec to system path
import sys
sys.path.append("../..")
# facerec imports
from facerec.dataset import DataSet
from facedet.detector import CascadedDetector
from facerec.preprocessing import TanTriggsPreprocessing
from facerec.feature import LBP
from facerec.classifier import NearestNeighbor
from facerec.operators import ChainOperator
from facerec.model import PredictableModel
from facerec.distance import ChiSquareDistance

def get_model():
    """ This method returns the PredictableModel which is used to learn a model
        for possible further usage. If you want to define your own model, this
        is the method to return it from!
    """
    # Define the Fisherfaces Method as Feature Extraction method:
    feature = Fisherfaces()
    # Define a 1-NN classifier with Euclidean Distance:
    classifier = NearestNeighbor(dist_metric=EuclideanDistance(), k=1)
    # Return the model as the combination:
    return PredictableModel(feature=feature, classifier=classifier)

def read_images(path, sz=None):
    """Reads the images in a given folder, resizes images on the fly if size is given.

    Args:
        path: Path to a folder with subfolders representing the subjects (persons).
        sz: A tuple with the size Resizes 

    Returns:
        A list [X, y, folder_names]

            X: The images, which is a Python list of numpy arrays.
            y: The corresponding labels (the unique number of the subject, person) in a Python list.
            folder_names: The names of the folder, so you can display it in a prediction.
    """
    c = 0
    X,y,folder_names = [], []
    for dirname, dirnames, filenames in os.walk(path):
        for subdirname in dirnames:
            folder_names.append(subdirname)
            subject_path = os.path.join(dirname, subdirname)
            for filename in os.listdir(subject_path):
                try:
                    im = Image.open(os.path.join(subject_path, filename))
                    im = im.convert("L")
                    # resize to given size (if given)
                    if (sz is not None):
                        im = im.resize(self.sz, Image.ANTIALIAS)
                    X.append(np.asarray(im, dtype=np.uint8))
                    y.append(c)
                except IOError, (errno, strerror):
                    print "I/O error({0}): {1}".format(errno, strerror)
                except:
                    print "Unexpected error:", sys.exc_info()[0]
                    raise
            c = c+1
    return [X,y,folder_names]


class App(object):
    def __init__(self, model, image_size, camera_id, cascade_filename, subject_names):
        self.face_sz = face_sz
        self.detector = CascadedDetector(cascade_fn=cascade_fn, minNeighbors=5, scaleFactor=1.1)
        self.model = model
        self.cam = create_capture(camera_id)
            
    def run(self):
        while True:
            ret, frame = self.cam.read()
            # Resize the frame to half the original size for speeding up the detection process:
            img = cv2.resize(frame, (frame.shape[1]/2, frame.shape[0]/2), interpolation = cv2.INTER_CUBIC)
            imgout = img.copy()
            for i,r in enumerate(self.detector.detect(img)):
                x0,y0,x1,y1 = r
                # (1) Get face, (2) Convert to grayscale & (3) resize to image_size:
                face = img[y0:y1, x0:x1]
                face = cv2.cvtColor(face,cv2.COLOR_BGR2GRAY)
                face = cv2.resize(face, self.image_size, interpolation = cv2.INTER_CUBIC)
                # Get a prediction from the model:
                prediction = self.model.predict(face)[0]
                # Draw the face area in image:
                cv2.rectangle(imgout, (x0,y0),(x1,y1),(0,255,0),2)
                # Draw the predicted name (folder name...):
                draw_str(imgout, (x0-20,y0-20), subject_names[prediction])
            cv2.imshow('videofacerec', imgout)
            # Show image & exit on escape:
            ch = cv2.waitKey(10)
            if ch == 27:
                break

if __name__ == '__main__':
    from optparse import OptionParser
    # model.pkl is a pickled (hopefully trained) PredictableModel, which is
    # used to make predictions. You can learn a model yourself by passing the
    # parameter -d (or --dataset) to learn the model from a given dataset.
    usage = "usage: %prog [options] model.pkl"
    # Add options for training, resizing, validation and setting the camera id:
    parser = OptionParser(usage=usage)
    parser.add_option("-r", "--resize", action="store", type="string", dest="size", default="100x100", 
        help="Resizes the given dataset to a given size in format [width]x[height] (default: 100x100).")
    parser.add_option("-v", "--validate", action="store", dest="validate", type="int", default=None, 
        help="Performs a k-fold cross validation on the dataset, if given (default: None).")
    parser.add_option("-d", "--dataset", action="store", type="string", dest="dataset", default=None, 
        help="Learns a new model, defined in get_model, from the given dataset (default: None).")
    parser.add_option("-i", "--id", action="store", dest="camera", type="int", default=0, 
        help="Sets the Camera Id to be used (default: 0).")
    parser.add_option("-c", "--cascade", action="store", dest="cascade_filename", default="haarcascade_frontalface_alt2.xml",
        help="Sets the path to the Haar Cascade used for the face detection part (default: haarcascade_frontalface_alt2.xml).")
    # Show the options to the user:
    parser.print_help()
    print "Script output:"
    # Parse arguments:
    (options, args) = parser.parse_args()
    # Check if a model name was passed:
    if len(args) == 0:
        print "[Error] No prediction model was given.", options.cascade_filename
        sys.exit()
    # This model will be used (or created if the dataset parameter (-d, --dataset) exists:
    model_filename = args[0]
    # Check if the given model exists, if no dataset was passed:
    if (options.dataset is None) and (not os.path.exists(model_filename)):
        print "[Error] No prediction model found at '%s'." % model_filename
        sys.exit()
    # Check if the given (or default) cascade file exists:
    if not os.path.exists(options.cascade_filename):
        print "[Error] No Cascade File found at '%s'." % options.cascade_filename
        sys.exit()
    # We are resizing the images to a fixed size, as this is neccessary for some of
    # the algorithms, some algorithms like LBPH don't have this requirement. To 
    # prevent problems from popping up, we resize them with a default value if none
    # was given:
    image_size = map(int, options.size.split("x"))
    # We have got a dataset to learn a new model from:
    if options.dataset:
        # Reads the images, labels and folder_names from a given dataset. Images
        # are resized to given size on the fly:
        print "Loading dataset..."
        [images, labels, folder_names] = read_images(options.dataset, sz=image_size)
        # Get the model we want to compute:
        model = get_model()
        # Sometimes you want to know how good the model may perform on the data
        # given, the script allows you to perform a k-fold Cross Validation before
        # the Detection & Recognition part starts:
        if options.validate:
            print "Validating model..."
            # Number of folds to be used:
            numFolds = options.validate
            # We want to have some log output, so set up a new logging handler
            # and point it to stdout:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            # Add a handler to facerec modules, so we see what's going on inside:
            logger = logging.getLogger("facerec")
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)
            # Perform the validation & print results:
            cv = KFoldCrossValidation(model, k=10)
            cv.validate(X, y)
            print cv
        # Compute the model:
        print "Computing the model..."
        model.compute(images, labels)
        # And save the model, which uses Pythons pickle module:
        save_model(model_filename, model)
    else:
        print "Loading the model..."
        model = load_model(model_filename)
    # Now it's time to finally start the Application! It simply get's the model
    # and the image size the incoming webcam or video images are resized to:
    print "Starting application..."
    App(model=model,
        image_size=image_size,
        camera_id=options.camera_id,
        cascade_filename=options.cascade_filename,
        subject_names=folder_names).run()