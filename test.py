from pymongo import MongoClient


class DatabaseManager:

    def __init__(self):
        self.client = None
        self.database = None
        self.collection = None
        self.connect()

    def connect(self):
        self.client = MongoClient(
            'mongodb+srv://Bot:XteazI8xIPrJybFK@easyfortnitestats-oxyd7.mongodb.net/test?retryWrites=true')
        self.database = self.client['EasyFortniteStats']
        self.collection = self.database['Stats']

        self.setup()

    def setup(self):
        if self.is_setup():
            return
        requests = {
            'name': 'Requests',
            'score': 0
        }
        servers = {
            'name': 'Servers',
            'score': 0,
            'highscore': 0
        }
        self.collection.insert_one(requests)
        self.collection.insert_one(servers)

    def is_setup(self):
        db_filter = {
            'name': 'Requests'
        }
        return self.collection.find_one(db_filter) is not None

    def get_document(self, name):
        db_filter = {
            'name': name
        }
        return self.collection.find_one(db_filter)

    def set_document(self, name, key, value):
        document = self.get_document(name)
        document[key] = value
        db_filter = {
            'name': name
        }
        update_operation = {
            "$set": document
        }
        self.collection.update_one(db_filter, update_operation, upsert=False)


if __name__ == '__main__':
    db_manager = DatabaseManager()
    print(type(db_manager.get_document('Requests')['value']))
    db_manager.set_document('Requests', 'value', 100)
