from unittest import TestCase
import asyncio
from aioorm import AioModel, AioMySQLDatabase,AioPostgreSQLDatabase
from aioorm.utils import aiodump_csv,aioload_csv
from peewee import (ForeignKeyField, IntegerField, CharField,
                    DateTimeField, TextField, PrimaryKeyField,Proxy,
                    SQL)

from io import StringIO
import aiofiles
from itertools import count
from pathlib import Path
import os
from aitertools import alist
db = Proxy()

c = count()

class User_csv_f(AioModel):
    id = PrimaryKeyField()
    name = CharField(max_length=25)
    age = IntegerField()
    sex = CharField(max_length=1)

    def __repr__(self):
        return '{self.id},{self.name},{self.age},{self.sex}'.format(self=self)

    class Meta:
        database = db

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
    query = User_csv.select().order_by(User_csv.id)
    await aiodump_csv(query,str(filepath))
    with StringIO(newline='') as f:
        f = await aiodump_csv(query,f)
        async with aiofiles.open(str(filepath)) as ff:
            r1 = await ff.read()
            r2 = f.getvalue()
            assert r1 == r2

    await User_csv.drop_table()
    assert await User_csv.table_exists() is False

    await db.close()

async def test_csv_load(loop):
    await db.connect(loop)

    p = Path(__file__).absolute().parent
    filepath = p.joinpath('source/user.csv')
    filepath1 = p.joinpath('source/0_user_out.csv')
    head = "id,name,age,sex"+os.linesep
    content = """1,u1,18,f
2,u2,17,f
3,u3,16,m
4,u4,15,f
"""
    with StringIO() as f:
        f.write(head+content)
        await aioload_csv(User_csv_f, f,pk_in_csv=True)
        all_cols = SQL('*')
        query0 = User_csv_f.select(all_cols).order_by(User_csv_f.id)
        user0 = await alist(query0)
        s = (os.linesep).join([str(i) for i in user0]).strip()
        r = content.strip()
        assert s == r
    await User_csv_f.drop_table()

    async with aiofiles.open(str(filepath)) as ff:
        er = await aioload_csv(User_csv_f, ff,pk_in_csv=False)
        all_cols = SQL('*')
        query0 = User_csv_f.select(all_cols).order_by(User_csv_f.id)
        user0 = await alist(query0)
        s = (os.linesep).join([str(i) for i in user0]).strip()
        r = content.strip()
        assert s == r

    await User_csv_f.drop_table()

    await aioload_csv(User_csv_f, '0_user_out.csv',pk_in_csv=True)
    all_cols = SQL('*')
    query0 = User_csv_f.select(all_cols).order_by(User_csv_f.id)
    user0 = await alist(query0)
    s = (os.linesep).join([str(i) for i in user0]).strip()
    r = content.strip()
    assert s == r


    await User_csv_f.drop_table()

    assert await User_csv_f.table_exists() is False

    await db.close()

class ModelMysqlTest(TestCase):
        @classmethod
        def setUpClass(cls, *args, **kwargs):
            """Configure database managers, create test tables.
            """
            database = AioMySQLDatabase('test', host='localhost', port=3306,
                       user='root', password='dev123')
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

        def test_csv_load(self):
            self.loop.run_until_complete(test_csv_load(self.loop))



class ModelPostgreSQLTest(TestCase):
        @classmethod
        def setUpClass(cls, *args, **kwargs):
            """Configure database managers, create test tables.
            """
            database = AioPostgreSQLDatabase('test', host='localhost', port=5432,
                      user='postgres')
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

        def test_csv_load(self):
            self.loop.run_until_complete(test_csv_load(self.loop))
