import os

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi


class MongoClientSingleton:
    _client: MongoClient = None

    @classmethod
    def init(cls, uri: str = "mongodb://localhost:27017/", **kwargs):
        """
        Initialize the singleton MongoClient. Can be called once at startup.
        """
        mongo_user = os.getenv('MONGO_USER')
        mongo_pass = os.getenv('MONGO_PASS')
        print(f"Mongo user {mongo_user}; momgo_pass {mongo_pass}")
        uri = f"mongodb+srv://{mongo_user}:{mongo_pass}@cluster0.1wshziu.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
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

    def __new__(cls, *args, **kwargs):
        """
        Return the singleton MongoClient, create if needed.
        """
        if cls._client is None:
            cls.init(*args, **kwargs)
        return cls._client
