from unittest import TestCase,expectedFailure
from aioorm.utils import AioDbFactory
from aioorm.postgresql import AioPostgreSQLDatabase
from aioorm.mysql import AioMySQLDatabase

class  AioDbFactoryTest(TestCase):

    def test_mysql(self):
        assert isinstance(AioDbFactory("mysql://root:dev123@localhost:3306/test"), AioMySQLDatabase)

    def test_Postgre(self):
        assert isinstance(AioDbFactory("postgresql://postgres@localhost:5432/test"), AioPostgreSQLDatabase)

    @expectedFailure
    def test_Failure(self):
        AioDbFactory("sqlit://")
