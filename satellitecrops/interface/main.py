import numpy as np
import tensorflow as tf
from colorama import Fore, Style
import itertools

from sklearn.model_selection import train_test_split
#from tensorflow.keras.optimizer import Adam

from satellitecrops.params import *
from satellitecrops.model.unet import unet, train_model
from satellitecrops.registry import save_model, save_results
from satellitecrops.data import create_Xy
from satellitecrops.preproc import scaling, clean_y


def train(
        path:str,
        learning_rate:float=0.001,
        batch_size:int= 16,
        patience:int= 5,
        alpha:float=0.25,
        gamma:float=2,
        validation_split:float=0.2,
        test_size:float=0.2,
        grid_search:bool=False
    ) -> float:

    """
    - Create X and y arrays from the BQ path
    - Train on the preprocessed dataset
    - Store training results and model weights

    Return val_meanIoU as a float
    """

    print(Fore.MAGENTA + "\n⭐️ Use case: train" + Style.RESET_ALL)
    print(Fore.BLUE + "\nLoading preprocessed validation data..." + Style.RESET_ALL)

    # Create train and test set
    X , y = create_Xy(path, min_crops_coverage=0.1)
    y = clean_y(y)
    print(f"y cleaned. {y.shape}")
    y_cat = tf.keras.utils.to_categorical(y)
    n_classes = len(np.unique(y))
    print("n_classes :", n_classes)
    img_height = y.shape[1]
    img_width = y.shape[2]
    channels = X.shape[1]
    del y
    print('y_cat created')
    X_scaled = scaling(X, 1)
    del X
    print("X_scaled done")
    X_scaled = np.moveaxis(X_scaled, 1, 3)
    print("")
    # test_offset = X_scaled.shape[0] - round(X_scaled.shape[0]*test_size)
    # X_train = X_scaled[:test_offset]
    # y_train = y_cat[:test_offset]
    # X_test = X_scaled[test_offset:]
    # y_test = y_cat[test_offset:]
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y_cat, test_size=0.2)
    del X_scaled
    del y_cat
    print(f"X_train : {X_train.shape}\ny_train : {y_train.shape}\nX_test : {X_test.shape}\ny_test : {y_test.shape}")

    # Train a model on the training set, using `model.py`
    model = None

    #optimizer = tf.keras.optimizer.Adam(learning_rate=learning_rate)

    model = unet(n_classes=n_classes,
                 img_height=img_height,
                 img_width=img_width,
                 img_channels=channels,
                 optimizer='adam',
                 alpha=alpha,
                 gamma=gamma,
                 learning_rate=learning_rate)
    print("model initialized")
    model, history = train_model(
        model,
        X_train,
        y_train,
        batch_size=batch_size,
        patience=patience,
        validation_split=validation_split
    )

    val_meanIoU = np.max(history.history['val_mean_io_u'])

    params = dict(
        context="train",
        training_set_size=X_train.shape[0],
        row_count=len(X_train), #To be changed,
    )
    if grid_search:
        params["grid"] = dict(
            batch_size=batch_size,
            patience=patience,
            learning_rate=learning_rate
        )

    # Save results on the hard drive using taxifare.ml_logic.registry
    save_results(params=params, metrics=dict(mean_IoU=val_meanIoU, history=history))

    # Save model weight on the hard drive (and optionally on GCS too!)
    if not grid_search:
        save_model(model=model)

    print("✅ train() done \n")

    return val_meanIoU


def grid_search():
    models = []
    histories = []

    learning_rates = [0.0001, 0.005, 0.001, 0.1, 1, 10]
    batch_sizes = [16, 32]
    patience = [5, 10]
    for params in itertools.product(learning_rates, batch_sizes, patience):
        print(f"--->New run with params {params[0]}, {params[1]}, {params[2]}")
        train(
            './data/departments/landes/eopatches',
            params[0],
            params[1],
            params[2],
            grid_search=True
            )
        # models.append(model)
        # histories.append(history)

if __name__ == '__main__':
    #preprocess()
    train('./data/departments/landes/eopatches')
    # grid_search()
    #evaluate()
    #pred()
