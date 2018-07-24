import unittest
import asyncio
from collections import namedtuple
try:
    from aioorm import (
        aio_dbconnect,
        AioMysqlConnect,
        AioPostgresqlConnect
    )
except:
    import sys
    from pathlib import Path
    path = str(
        Path(__file__).absolute().parent.parent.parent
    )
    if path not in sys.path:
        sys.path.insert(0, path)
    from aioorm import (
        aio_dbconnect,
        AioMysqlConnect,
        AioPostgresqlConnect
    )


class NCls:
    def __init__(self, n):
        self.N = n


Nnt = namedtuple('Nnt', ('N',))


class TestPgConnect(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("setUp aio pg test")

    @classmethod
    def tearDownClass(cls):
        print("tearDown aio pg test")

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    async def _test_connect(self):
        connection = aio_dbconnect("postgresql://postgres:@localhost:5432/test")
        with self.assertRaisesRegex(Exception, r"please connect again") as a:
            connection.pool
        await connection.connect()
        assert connection.pool is not None
        await connection.close()
        with self.assertRaisesRegex(Exception, r"please connect again") as a:
            connection.pool

    def test_connect(self):
        self.loop.run_until_complete(self._test_connect())

    async def _test_execute_sql(self):
        async with aio_dbconnect("postgresql://postgres:@localhost:5432/test") as connection:
            aiter = connection.execute_sql("select 1")
            async for i in aiter:
                assert i == (1,)

    def test_execute_sql(self):
        self.loop.run_until_complete(self._test_execute_sql())

    async def _test_execute_sql_with_class(self):
        async with aio_dbconnect("postgresql://postgres:@localhost:5432/test") as connection:
            aiter = connection.execute_sql("select 1;", NCls)
            async for i in aiter:
                assert i.N == 1

    def test_execute_sql_with_class(self):
        self.loop.run_until_complete(self._test_execute_sql_with_class())

    async def _test_execute_sql_with_nametuple(self):
        async with aio_dbconnect("postgresql://postgres:@localhost:5432/test") as connection:
            aiter = connection.execute_sql("select 1;", Nnt)
            async for i in aiter:
                assert i.N == 1

    def test_execute_sql_with_nametuple(self):
        self.loop.run_until_complete(self._test_execute_sql_with_nametuple())


class TestMysqlConnect(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("setUp aio mysql test")

    @classmethod
    def tearDownClass(cls):
        print("tearDown aio mysql test")

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    async def _test_connect(self):
        connection = aio_dbconnect("mysql://root:dev123@localhost:3306/mysql")
        with self.assertRaisesRegex(Exception, r"please connect again") as a:
            connection.pool
        await connection.connect()
        assert connection.pool is not None
        await connection.close()
        with self.assertRaisesRegex(Exception, r"please connect again") as a:
            connection.pool

    def test_connect(self):
        self.loop.run_until_complete(self._test_connect())

    async def _test_execute_sql(self):
        async with aio_dbconnect("mysql://root:dev123@localhost:3306/mysql") as connection:
            aiter = connection.execute_sql("select 1")
            async for i in aiter:
                assert i == (1,)

    def test_execute_sql(self):
        self.loop.run_until_complete(self._test_execute_sql())

    async def _test_execute_sql_with_class(self):
        async with aio_dbconnect("mysql://root:dev123@localhost:3306/mysql") as connection:
            aiter = connection.execute_sql("select 1;", NCls)
            async for i in aiter:
                assert i.N == 1

    def test_execute_sql_with_class(self):
        self.loop.run_until_complete(self._test_execute_sql_with_class())

    async def _test_execute_sql_with_nametuple(self):
        async with aio_dbconnect("mysql://root:dev123@localhost:3306/mysql") as connection:
            aiter = connection.execute_sql("select 1;", Nnt)
            async for i in aiter:
                assert i.N == 1

    def test_execute_sql_with_nametuple(self):
        self.loop.run_until_complete(self._test_execute_sql_with_nametuple())

def pg_suite():
    suite = unittest.TestSuite()
    suite.addTest(TestPgConnect("test_connect"))
    suite.addTest(TestPgConnect("test_execute_sql"))
    suite.addTest(TestPgConnect("test_execute_sql_with_class"))
    suite.addTest(TestPgConnect("test_execute_sql_with_nametuple"))
    suite.addTest(TestMysqlConnect("test_connect"))
    suite.addTest(TestMysqlConnect("test_execute_sql"))
    suite.addTest(TestMysqlConnect("test_execute_sql_with_class"))
    suite.addTest(TestMysqlConnect("test_execute_sql_with_nametuple"))
    return suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner(verbosity=2)
    test_suite = pg_suite()
    runner.run(test_suite)
