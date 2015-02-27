"""
db.py
"""

# import pymongo # DB
# from bson import json_util # DB
# from pymongo import MongoClient # DB

class Logger:
	def __init__(self):
		self.LOG_NAME = datetime.strftime(datetime.now(), self.LOG_FORMAT)
        self.MONGO_NAME = datetime.strftime(datetime.now(), self.MONGO_FORMAT)
        if self.VERBOSE: print('[Initialing MongoDB] %s' % datetime.strftime(datetime.now(), self.TIME_FORMAT))
        if self.VERBOSE: print('\tConnecting to MongoDB: %s' % self.MONGO_NAME)
        if self.VERBOSE: print('\tNew session: %s' % self.LOG_NAME)
        try:
            self.client = MongoClient()
            self.database = self.client[self.MONGO_NAME]
            self.collection = self.database[self.LOG_NAME]
            self.log = open('logs/' + self.LOG_NAME + '.csv', 'w')
            self.log.write(','.join(['time', 'lat', 'long', 'speed', 'cam0', 'cam1', 'estimate', 'average', 'pwm','\n']))
        except Exception as error:
            print('\tERROR in __init__(): %s' % str(error))
            
    ## Logs to Mongo
    """
    1. Log results to the database
    2. Returns Doc ID
    """
    def log_db(self, sample):
        if self.VERBOSE: print('[Logging to Database] %s' % datetime.strftime(datetime.now(), self.TIME_FORMAT))
        try:          
            doc_id = self.collection.insert(sample)
        except Exception as error:
            print('\tERROR in log_db(): %s' % str(error))
        if self.VERBOSE: print('\tDoc ID: %s' % str(doc_id))
        return doc_id
        
    ## Log to File
    """
    1. Open new text file
    2. For each document in session, print parameters to file
    """
    def log_file(self, sample):
        if self.VERBOSE: print('[Logging to File] %s' % datetime.strftime(datetime.now(), self.TIME_FORMAT))
        try:
            time = str(sample['time'])
            latitude = str(sample['lat'])
            longitude = str(sample['long'])
            speed = str(sample['speed'])
            cam0 = str(sample['cam0'])
            cam1 = str(sample['cam1'])
            estimate = str(sample['estimate'])
            average = str(sample['average'])
            pwm = str(sample['pwm'])
            self.log.write(','.join([time, latitude, longitude, speed, cam0, cam1, estimate, average, pwm,'\n']))
        except Exception as error:
            print('\tERROR: %s' % str(error))
