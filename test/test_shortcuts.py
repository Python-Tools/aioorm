from peewee import CharField, TextField, ForeignKeyField, CompositeKey,Proxy
from aioorm import AioModel, AioMySQLDatabase, model_to_dict, AioPostgreSQLDatabase
import asyncio
from unittest import TestCase
db = Proxy()



class User(AioModel):
    username = CharField()

    class Meta:
        database = db


class Note(AioModel):
    user = ForeignKeyField(User, related_name='notes')
    text = TextField()

    class Meta:
        database = db


class Tag(AioModel):
    tag = CharField()

    class Meta:
        database = db


class NoteTag(AioModel):
    note = ForeignKeyField(Note)
    tag = ForeignKeyField(Tag)

    class Meta:
        database = db
        primary_key = CompositeKey('note', 'tag')


async def simple_recurse_t(loop):
    await db.connect(loop)
    await db.create_tables([User, Note], safe=True)

    user = await User.create(username='test')
    note = await Note.create(user=user, text='note-1')

    result = await model_to_dict(note)
    expected = {
        'id': note.id,
        'text': note.text,
        'user': {
            'id': user.id,
            'username': user.username
        }
    }
    assert result == expected

    result = await model_to_dict(note, recurse=False)
    expected = {
        'id': note.id,
        'text': note.text,
        'user': user.id
    }
    assert result == expected

    await db.drop_tables([User, Note], safe=True)
    await db.close()


async def model_to_dict_t(loop):
    await db.connect(loop)
    await db.create_tables([User, Note, Tag, NoteTag], safe=True)

    user = await User.create(username='peewee')
    n0, n1, n2 = [await Note.create(user=user, text='n%s' % i)
                  for i in range(3)]
    t0, tx = [await Tag.create(tag=t) for t in ('t0', 'tx')]
    await NoteTag.create(note=n0, tag=t0)
    await NoteTag.create(note=n0, tag=tx)
    await NoteTag.create(note=n1, tag=tx)

    data = await model_to_dict(user, recurse=True, backrefs=True)
    expected = {
        'id': user.id,
        'username': 'peewee',
        'notes': [
            {'id': n0.id, 'text': 'n0', 'notetag_set': [
                {'tag': {'tag': 't0', 'id': t0.id}},
                {'tag': {'tag': 'tx', 'id': tx.id}},
            ]},
            {'id': n1.id, 'text': 'n1', 'notetag_set': [
                {'tag': {'tag': 'tx', 'id': tx.id}},
            ]},
            {'id': n2.id, 'text': 'n2', 'notetag_set': []},
        ]
    }
    assert data == expected

    data = await model_to_dict(user, recurse=True, backrefs=True, max_depth=2)

    await db.drop_tables([User, Note, Tag, NoteTag], safe=True)
    await db.close()


class ShortCutMysqlTest(TestCase):
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

        def test_simple_recurse(self):
            self.loop.run_until_complete(simple_recurse_t(self.loop))

        def test_model_to_dict(self):
            self.loop.run_until_complete(model_to_dict_t(self.loop))

class ShortCutPostgreSQLTest(TestCase):
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

        def test_simple_recurse(self):
            self.loop.run_until_complete(simple_recurse_t(self.loop))

        def test_model_to_dict(self):
            self.loop.run_until_complete(model_to_dict_t(self.loop))
