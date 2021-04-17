# -*- coding: utf-8 -*-
"""
Created on Mon Apr 12 09:36:25 2021

@author: Pedram Tavadze
"""
import os
import h5py
import pandas as pd
import pymongo
from .tape_image import TapeImage


class Database():
    def __init__(self, 
                 name="forensicdb",
                 host="localhost",
                 port="27017",
                 username="",
                 password=""):
        
        self.name=name
        self.host=host
        self.port=port
        self.username=username
        self.password=password
        self.uri = 'mongodb'
        
        self.fname = fname
        self.modes = modes
        self.mask_threshold = mask_threshold
        self.gaussian_blur = gaussian_blur
        self.dynamic_window = dynamic_window
        self.nsegments = nsegments
        self.window_background = window_background
        self.window_tape = window_tape
        self.sizes = sizes
        self.meta_file = meta_file
        self.meta_dataframe = None
        self.src_dir = src_dir
        self.verbose = verbose

        if initiate:
            self.create_db()

    def create_db(self):
        """
        

        Returns
        -------
        None.

        """
        if os.path.exists(self.fname):
            if self.verbose:
                print("%s already exists, changing the name to %s" %
                      (self.fname, self.fname+"_1"))
            self.fname = self.fname+"_1"
        if self.verbose:
            print("Openning the metadata file.")
        self.meta_dataframe = pd.read_excel(self.meta_file)
        ndata = 4  # self.meta_dataframe.shape[0]
        if self.verbose:
            print("creating the database file %s" % self.fname)
        wf = h5py.File(self.fname, 'w')
        for mode in self.modes:
            if self.verbose:
                print("creating dataset %s" % mode)
            size = self.sizes[mode]
            size = tuple([ndata, 4]+list(size))
            wf.create_dataset(mode, shape=size, dtype=float)

        wf.create_dataset('match', shape=(ndata,), dtype=bool)
        
        for idata in range(ndata):
            df = self.meta_dataframe.iloc[idata]
            tf1 = TapeImage(fname=self.src_dir+os.sep+df['tape_f1']+'.tif', split_side=df['side_f1'],
                            mask_threshold=self.mask_threshold, gaussian_blur=self.gaussian_blur)
            tf1.auto_crop_y()
            wf['max_contrast'][idata, 0, :, :] = tf1.max_contrast(window_background=self.window_background,
                                                      window_tape=self.window_tape, size=self.sizes["max_contrast"])[:, :]
            tf2 = TapeImage(fname=self.src_dir+os.sep+df['tape_f2']+'.tif', flip=df["flip_f"], split_side=df['side_f2'],
                            mask_threshold=self.mask_threshold, gaussian_blur=self.gaussian_blur)
            tf2.auto_crop_y()
            wf['max_contrast'][idata, 1, :, :] = tf2.max_contrast(window_background=self.window_background,
                                                                  window_tape=self.window_tape, size=self.sizes["max_contrast"])[:, :]
            tb1 = TapeImage(fname=self.src_dir+os.sep+df['tape_b1']+'.tif', split_side=df['side_b1'],
                            mask_threshold=self.mask_threshold, gaussian_blur=self.gaussian_blur)
            tb1.auto_crop_y()
            wf['max_contrast'][idata, 2, :, :] = tb1.max_contrast(window_background=self.window_background,
                                                                  window_tape=self.window_tape, size=self.sizes["max_contrast"])[:, :]
            tb2 = TapeImage(fname=self.src_dir+os.sep+df['tape_b2']+'.tif', flip=df["flip_b"], split_side=df['side_b2'],
                            mask_threshold=self.mask_threshold, gaussian_blur=self.gaussian_blur)
            tb2.auto_crop_y()
            wf['max_contrast'][idata, 3, :, :] = tb2.max_contrast(window_background=self.window_background,
                                                                  window_tape=self.window_tape, size=self.sizes["max_contrast"])[:, :]
            
        wf.close()