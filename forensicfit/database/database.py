# -*- coding: utf-8 -*-
"""
Created on Mon Apr 12 09:36:25 2021

@author: Pedram Tavadze
used PyChemia Database class as a guide
https://github.com/MaterialsDiscovery/PyChemia/blob/master/pychemia/db/db.py
"""
import os
import h5py
import pandas as pd
import numpy as np
import pymongo
import gridfs
import io
from bson.objectid import ObjectId
from ..core import Tape, TapeAnalyzer
# from ..preprocess import TapeImage


class Database:
    def __init__(self,
                 name='forensicfit',
                 host='localhost',
                 port=27017,
                 username="",
                 password=""):

        self.name = name
        self.host = host
        self.port = port

        self.username = username
        self.password = password
        if len(password) != 0:
            self.password = ":"+password+"@"
        else:
            if len(username) != 0:
                self.username += "@"
        self.uri = "mongodb://%s%s%s:%d" % (username, password, host, port)
        self.client = pymongo.MongoClient(self.uri)
        self.db = self.client[name]
        self.entries = self.db.forensicfit_entries

        self.gridfs_item = gridfs.GridFS(self.db, "items")
        self.gridfs_analysis = gridfs.GridFS(self.db, "analysis")
        self.db_info = {"Database Name": self.name,
                        "Host": self.host,
                        "Port": self.port,
                        "User": self.username}

    def __str__(self):
        ret = ""
        for key in self.db_info:
            ret += "{:<7}    :  {}\n".format(key, self.db_info[key])
        return ret

    def insert_item(self, item):
        if item.metadata['mode'] == 'analysis':
            for key in item.values:
                if type(item[key]) is np.ndarray:
                    output = io.BytesIO()
                    np.save(output, item.values[key])
                    # # This is to erase the other types of analysis
                    metadata = item.metadata.copy()
                    # metadata['analysis'] = {}
                    metadata['analysis_mode'] = key
                    # if key != 'image':

                    #     if key in item.metadata['analysis']:
                    #         metadata['analysis'][key] = item.metadata['analysis'][key]
                    # metadata = item.metadata
                    self.gridfs_analysis.put(output.getvalue(), filename=item.label,
                                             metadata=metadata)
        elif item.metadata['mode'] == 'item':
            for key in item.values:
                if type(item[key]) is np.ndarray:
                    output = io.BytesIO()
                    np.save(output, item.values[key])
                    self.gridfs_item.put(output.getvalue(), filename=item.filename,
                                         metadata=item.metadata)

    def query(self, criteria={}, version=-1):
        ret = None
        queries = self.gridfs_analysis.find(
            criteria).sort("uploadDate", version)
        if queries.count() != 0:
            metadata = {}
            values = {}
            for iq in queries:
                # if len(metadata) == 0:
                #     metadata = iq.metadata
                # if len(iq.metadata["analysis"]) != 0:
                #     metadata['analysis'][iq.metadata['analysis_mode']
                #                          ] = iq.metadata['analysis'][iq.metadata['analysis_mode']]
                values[iq.metadata['analysis_mode']] = np.load(
                    io.BytesIO(iq.read()))
                # values['metadata'] = metadata
            values['metadata'] = iq.metadata
            ret = TapeAnalyzer.from_dict(values)
        return ret

    def get_item(self, filename=None, _id=None, mode='analysis', side="R", version=-1):
        ret = None
        if mode == 'analysis':
            if _id is not None:
                iq = self.gridfs_analysis.get(ObjectId(_id), version=version)
                ret = {'data': np.load(io.BytesIO(iq.read())),
                       'metadata': iq.metadata}
            else:
                queries = self.gridfs_analysis.find(
                    {"filename": filename, "metadata.split_vertical.side": side}).sort("uploadDate", version)
                if queries.count() != 0:
                    metadata = {}
                    values = {}
                    for iq in queries:
                        # if len(metadata) == 0:
                        #     metadata = iq.metadata
                        # if len(iq.metadata["analysis"]) != 0:
                        #     metadata['analysis'][iq.metadata['analysis_mode']
                        #                          ] = iq.metadata['analysis'][iq.metadata['analysis_mode']]
                        values[iq.metadata['analysis_mode']] = np.load(
                            io.BytesIO(iq.read()))
                        # values['metadata'] = metadata
                    values['metadata'] = iq.metadata
                    ret = TapeAnalyzer.from_dict(values)
                    # ret = values
        elif mode == 'item':
            if _id is not None:
                iq = self.gridfs_analysis.get(ObjectId(_id))
                ret = {'data': np.load(io.BytesIO(iq.read())),
                       'metadata': iq.metadata}
            else:
                queries = self.gridfs_item.find(
                    {"filename": filename, "metadata.split_vertical.side": side}).sort("uploadDate", version).limit(1)

                iq = next(queries, None)
                if iq is not None:

                    metadata = {}
                    values = {}
                    values['image'] = np.load(
                        io.BytesIO(iq.read()))
                    values['filename'] = filename
                    values['label'] = iq.metadata['label']
                    values['metadata'] = iq.metadata

                    ret = Tape.from_dict(values=values)

        return ret

    def delete_database(self):
        self.client.drop_database(self.name)

    def get_