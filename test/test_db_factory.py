from unittest import TestCase,expectedFailure
from aioorm.utils import AioDbFactory
from aioorm.postgresql import AioPostgreSQLDatabase
from aioorm.mysql import AioMySQLDatabase

class  AioDbFactoryTest(TestCase):

    def test_mysql(self):
        assert isinstance(AioDbFactory("mysql:///test"), AioMySQLDatabase)

    def test_Postgre(self):
        assert isinstance(AioDbFactory("postgresql:///test"), AioPostgreSQLDatabase)

    @expectedFailure
    def test_Failure(self):
        AioDbFactory("sqlit://")
