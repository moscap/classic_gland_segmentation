import skimage.io as io
import skimage.transform as trans
import tensorflow as tf
print(tf.__version__)
from tensorflow.keras import backend as keras
from skimage import exposure
from tensorflow.keras import utils as np_utils
from tensorflow.keras.datasets import cifar10
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from tensorflow.keras.callbacks import CSVLogger, TensorBoard, ModelCheckpoint
from sklearn.preprocessing import LabelBinarizer
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from imutils import paths
import matplotlib.pyplot as plt
import numpy as np
import argparse
import imutils
import random
import pickle
import platform
import cv2
import os

from model import mynet, densenet, smallnet
# set the matplotlib backend so figures can be saved in the background
import matplotlib
matplotlib.use("Agg")

ROTATION_ANGLES = [0, 90, 180, 270]
MIN_LR = 0.0000001
BASE_PATIENCE = 6
FACTOR = 0.2
MODEL_BASE_TYPE = 'std'
MODEL_DENSE_TYPE = 'dense'
MODEL_SMALL_TYPE = 'small'
BATCH_SIZE = 32
VAL_BATCH_SIZE = 8
ROTATION_RANGE = 15
EPOCHS = 300
TRAIN_MODE = 'train'
VALIDATION_MODE = 'validation'
AUG_FACTOR = 4

AXIS_X = 1
AXIS_Y = 0

class InputGenerator:
    def __init__(self, imgs, labels, batch_size: int = BATCH_SIZE, mode = TRAIN_MODE):
        assert imgs.shape[0] == labels.shape[0]
        self.imgs = imgs
        self.labels = labels
        self.batch_size = batch_size
        self.n_imgs = imgs.shape[0]
        self.mode = mode
    def __iter__(self):
        while True:
            idx = np.random.choice(self.n_imgs, self.batch_size)
            img_batch = np.stack([self.__aug__(self.imgs[i, ...]) for i in idx])
            label_batch = np.stack([self.labels[i, ...] for i in idx])
            yield img_batch, label_batch, [None]
    def __aug__(self, img):
        if(self.mode == VALIDATION_MODE):
            return img
        
        angle = np.random.randint(0, len(ROTATION_ANGLES))
        angle = ROTATION_ANGLES[angle]
        img = imutils.rotate_bound(img, angle)
            
        flag = np.random.randint(0, 2)
        if flag > 0:
            img = np.flip(img, axis = AXIS_Y)
                
        flag = np.random.randint(0, 2)
        if flag > 0:
            img = np.flip(img, axis = AXIS_X)
        return img
            

#starts traning
def Train(train_x, train_y, validation_x, validation_y, 
          model_type = MODEL_BASE_TYPE, epochs = EPOCHS, 
          batch_size = BATCH_SIZE, checkpoint_file = './checkpoint.hdf5', 
          history_file = 'history.csv', statistic_folder = './', save_to_dir = None):
    
    TrainGenerator = InputGenerator(train_x, train_y, batch_size)
    ValidationGenerator = InputGenerator(validation_x, validation_y, VAL_BATCH_SIZE)

    if(model_type == MODEL_BASE_TYPE):
        model = mynet(input_size = (256, 256, 3))
    elif(model_type == MODEL_DENSE_TYPE):
        model = densenet(input_size = (256, 256, 3))
    else:
        model = smallnet(input_size = (256, 256, 3), learning_rate = 0.01)
        
    model_checkpoint = ModelCheckpoint(checkpoint_file, monitor='val_loss',verbose=1, save_best_only=True)
    early_stopping = EarlyStopping(monitor='val_loss', patience=BASE_PATIENCE + 2) #ptiaence provides number of epocs befour this function will be activated
    reduce_lr = ReduceLROnPlateau(monitor='val_loss', factor=FACTOR, patience=BASE_PATIENCE, min_lr=MIN_LR) #factor is a scaling fator to learning rate
    csv_logger = CSVLogger( statistic_folder + history_file)
    
    # tensorboard_logger = TensorBoard(log_dir='/content/drive/My Drive/Diploma/logs/tensorboard', histogram_freq=1, batch_size=batch_size,
    #                                                                 write_graph=True, write_grads=False, write_images=False,
    #                                                                 embeddings_freq=0, embeddings_layer_names=None,
    #                                                                 embeddings_metadata=None, embeddings_data=None, update_freq='epoch')
    model.fit_generator(iter(TrainGenerator), steps_per_epoch=len(train_x) * AUG_FACTOR / batch_size,
                        epochs=EPOCHS, callbacks=[model_checkpoint, early_stopping, reduce_lr, csv_logger], 
                        validation_data = iter(ValidationGenerator), 
                        validation_steps=len(validation_x) * AUG_FACTOR / VAL_BATCH_SIZE)

#prepare data
def train(train_path, validation_path, model_type = MODEL_BASE_TYPE, epochs = EPOCHS, 
          batch_size = BATCH_SIZE, checkpoint_file = './checkpoint.hdf5', 
          history_file = 'history.csv', statistic_folder = './', save_to_dir = None):
    epochs = int(epochs)
    batch_size = int(batch_size)

    data = np.load('../stdmapinvert.npz')
    tr_x = data['tr_x']
    tr_y = data['tr_y']
    val_x = data['val_x']
    val_y = data['val_y']
        
    print(np.asarray(tr_y).shape) 
    print(np.asarray(tr_x).shape) 
    print(np.asarray(val_y).shape) 
    print(np.asarray(val_x).shape) 
        
    Train(tr_x, tr_y, val_x, val_y, model_type, epochs, batch_size, checkpoint_file , 
             history_file, statistic_folder, save_to_dir)

#argparse
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-t", "--train", required=True,
    	help="path to train dataset of images")
    ap.add_argument("-v", "--validation", required=True,
    	help="path to validation dataset of images")
    ap.add_argument("-b", "--batchsize", required=False,
    	help="number of images in one batch")
    ap.add_argument("-e", "--epochs", required=False,
    	help="number of epochs")
    ap.add_argument("-c", "--checkpoint", required=False,
    	help="path to checkpoint hdf5 file")
    ap.add_argument("-hist", "--history", required=False,
    	help="name of cvsv file with trainig history")
    ap.add_argument("-stat", "--statistics", required=False,
    	help="statistics folder")
    ap.add_argument("-type", "--type", required=False,
    	help="model type: std, dense or small")
    
    args = vars(ap.parse_args())
    
    train_args = dict(train_path = args["train"],
                      validation_path = args["validation"])
    
    if args["epochs"] != None:
        train_args["epochs"] = args["epochs"]
    if args["batchsize"] != None:
        train_args["batch_size"] = args["batchsize"]
    if args["checkpoint"] != None:
        train_args["checkpoint_file"] = args["checkpoint"]
    if args["statistics"] != None:
        train_args["statistic_folder"] = args["statistics"]
    if args["type"] != None:
        train_args["model_type"] = args["type"]
    if args["history"] != None:
        train_args["history_file"] = args["history"]

    train(**train_args)

if __name__ == "__main__":
    main()