from unittest import TestCase
import asyncio
from aioorm import AioModel, AioMySQLDatabase,AioPostgreSQLDatabase
from aioorm.utils import aiodump_csv
from peewee import (ForeignKeyField, IntegerField, CharField,
                    DateTimeField, TextField, PrimaryKeyField,Proxy,
                    SQL)

from pathlib import Path
db = Proxy()
from itertools import count
c = count()

class User_csv(AioModel):
    name = CharField(max_length=25)
    age = IntegerField()
    sex = CharField(max_length=1)

    class Meta:
        database = db

async def test_csv_dump(loop):
    await db.connect(loop)

    assert await User_csv.table_exists() is False
    await User_csv.create_table()
    assert await User_csv.table_exists() is True
    iq = User_csv.insert_many([
        {'name': 'u1',"age":18,'sex':'f'},
        {'name': 'u2',"age":17,'sex':'f'},
        {'name': 'u3',"age":16,'sex':'m'},
        {'name': 'u4',"age":15,'sex':'f'}])

    await iq.execute()
    p = Path(__file__).absolute().parent
    filepath = p.joinpath('source/{}_user_out.csv'.format(str(next(c))))
    print(str(filepath))
    query = User_csv.select().order_by(User_csv.id)
    await aiodump_csv(query,str(filepath))
    await User_csv.drop_table()
    assert await User_csv.table_exists() is False

    await db.close()

class ModelMysqlTest(TestCase):
        @classmethod
        def setUpClass(cls, *args, **kwargs):
            """Configure database managers, create test tables.
            """
            database = AioMySQLDatabase('test', host='localhost', port=3306,
                       user='root', password='hsz881224')
            db.initialize(database)
            cls.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(cls.loop)
        @classmethod
        def tearDownClass(cls, *args, **kwargs):
            """Remove all test tables and close connections.
            """
            cls.loop.close()

        def test_csv_dump(self):
            self.loop.run_until_complete(test_csv_dump(self.loop))



class ModelPostgreSQLTest(TestCase):
        @classmethod
        def setUpClass(cls, *args, **kwargs):
            """Configure database managers, create test tables.
            """
            database = AioPostgreSQLDatabase('test_ext', host='localhost', port=5432,
                      user='huangsizhe', password='')
            db.initialize(database)
            cls.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(cls.loop)
        @classmethod
        def tearDownClass(cls, *args, **kwargs):
            """Remove all test tables and close connections.
            """
            cls.loop.close()

        def test_csv_dump(self):
            self.loop.run_until_complete(test_csv_dump(self.loop))
