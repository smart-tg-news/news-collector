import os

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

from typing import Callable


class MissingMongoEnv(Exception):
    pass


class MongoClientSingleton:
    _client: MongoClient = None
    _uri_template: Callable[..., str] = \
        "mongodb+srv://{mongo_user}:{mongo_pass}@cluster0.1wshziu.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0".format

    @classmethod
    def init(cls, **kwargs):
        """
        Initialize the singleton MongoClient. Can be called once at startup.
        """
        mongo_user = cls.get_mongo_env_var('MONGO_USER')
        mongo_pass = cls.get_mongo_env_var('MONGO_PASS')
        uri = cls._uri_template(mongo_user=mongo_user, mongo_pass=mongo_pass)

        if cls._client is None:
            cls._client = MongoClient(
                uri, 
                server_api=ServerApi('1'), 
                **kwargs
            )
        return cls._client
    
    @classmethod
    def close(cls):
        if cls._client:
            cls._client.close()
            cls._client = None

    @staticmethod
    def get_mongo_env_var(var_name):
        try:
            env_var = os.environ[var_name]
        except KeyError:
            raise MissingMongoEnv(f"Variable {var_name} doesn't exist")
        return env_var

    def __new__(cls, *args, **kwargs):
        """
        Return the singleton MongoClient, create if needed.
        """
        if cls._client is None:
            cls.init(*args, **kwargs)
        return cls._client
