from aitertools import alist

from aioorm import AioModel, AioMySQLDatabase, AioManyToManyField,AioPostgreSQLDatabase
from peewee import (ForeignKeyField, IntegerField, CharField,Proxy,
                    DateTimeField, TextField, PrimaryKeyField)

from unittest import TestCase
import asyncio

db = Proxy()

class User(AioModel):
    username = CharField(unique=True)

    class Meta:
        database = db


class Note(AioModel):
    text = TextField()
    users = AioManyToManyField(User)

    class Meta:
        database = db


NoteUserThrough = Note.users.get_through_model()

async def create_users_notes():
    usernames = ['charlie', 'huey', 'mickey', 'zaizee']
    n_notes = 5
    for username in usernames:
        await User.create(username=username)
    for i in range(n_notes):
        await Note.create(text='note-%s' % (i + 1))

    # create relationship
    user_to_note = {'charlie': [1, 2],
                    'huey': [2, 3],
                    'mickey': [3, 4],
                    'zaizee': [4, 5]}
    for username, notes in user_to_note.items():
        user = await User.get(User.username == username)
        for note in notes:
            note = await Note.get(Note.text == 'note-%s' % note)
            await NoteUserThrough.create(note=note, user=user)


async def assert_notes(query, expected):
    notes = [note.text async for note in query]
    assert sorted(notes) == ['note-%s' % i for i in sorted(expected)]


async def assert_users(query, expected):
    usernames = [user.username async for user in query]
    assert sorted(usernames) == sorted(expected)


async def set_values(loop):
    await db.connect(loop)
    await db.create_tables([User, Note, NoteUserThrough], safe=True)
    await create_users_notes()

    charlie = await User.get(User.username == 'charlie')
    huey = await User.get(User.username == 'huey')
    n1, n2, n3, n4, n5 = await alist(Note.select().order_by(Note.text))

    await assert_notes(charlie.notes, [1, 2])
    await assert_users(n1.users, ['charlie'])

    await charlie.notes.set([n2, n3])
    await assert_notes(charlie.notes, [2, 3])
    await assert_users(n1.users, [])
    await assert_users(n2.users, ['charlie', 'huey'])
    await assert_users(n3.users, ['charlie', 'huey', 'mickey'])

    await db.drop_tables([User, Note, NoteUserThrough], safe=True)
    await db.close()

class ManyToManyMysqlTest(TestCase):
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

        def test_mtm(self):
            self.loop.run_until_complete(set_values(self.loop))

class ManyToManyPostgreSQLTest(TestCase):
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

        def test_mtm(self):
            self.loop.run_until_complete(set_values(self.loop))
