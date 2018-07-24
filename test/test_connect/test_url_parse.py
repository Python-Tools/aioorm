import platform
import getpass
import unittest

try:
    from aioorm.connect.utils.url_parser import parser
    from aioorm.connect.error import InvalidURI
except:
    import sys
    from pathlib import Path
    path = str(
        Path(__file__).absolute().parent.parent.parent
    )
    if path not in sys.path:
        sys.path.insert(0, path)
    for i in sys.path:
        print("********")
        print(i)
    from aioorm.connect.utils.url_parser import parser
    from aioorm.connect.error import InvalidURI


def setUpModule():
    print("setUp [url parse] Module")


def tearDownModule():
    print("tearDown [url parse] Module")


class MysqlURITest(unittest.TestCase):

    def test_mysql(self):
        uri = "mysql:///test"
        self.assertDictEqual(dict(scheme="mysql",
                                  username='root',
                                  password='',
                                  host='localhost',
                                  port=3306,
                                  database='test'),
                             parser(uri))

    def test_mysql_host(self):
        uri = "mysql://192.168.1.23/test"
        self.assertDictEqual(dict(scheme="mysql",
                                  username='root',
                                  password='',
                                  host='192.168.1.23',
                                  port=3306,
                                  database='test'),
                             parser(uri))

    def test_mysql_port(self):
        uri = "mysql://:123/test"
        self.assertDictEqual(dict(scheme="mysql",
                                  username='root',
                                  password='',
                                  host='localhost',
                                  port=123,
                                  database='test'),
                             parser(uri))

    def test_mysql_user(self):
        uri = "mysql://user@/test"
        self.assertDictEqual(dict(scheme="mysql",
                                  username='user',
                                  password='',
                                  host='localhost',
                                  port=3306,
                                  database='test'),
                             parser(uri))

    def test_mysql_password(self):
        uri = "mysql://:password@/test"
        self.assertDictEqual(dict(scheme="mysql",
                                  username='root',
                                  password='password',
                                  host='localhost',
                                  port=3306,
                                  database='test'),
                             parser(uri))

    def test_mysql_host_port(self):
        uri = "mysql://192.168.1.23:123/test"
        self.assertDictEqual(dict(scheme="mysql",
                                  username='root',
                                  password='',
                                  host='192.168.1.23',
                                  port=123,
                                  database='test'),
                             parser(uri))

    def test_mysql_user_pass(self):
        uri = "mysql://user:password@/test"
        self.assertDictEqual(dict(scheme="mysql",
                                  username='user',
                                  password='password',
                                  host='localhost',
                                  port=3306,
                                  database='test'),
                             parser(uri))

    def test_mysql_user_host(self):
        uri = "mysql://user@192.168.1.23/test"
        self.assertDictEqual(dict(scheme="mysql",
                                  username='user',
                                  password='',
                                  host='192.168.1.23',
                                  port=3306,
                                  database='test'),
                             parser(uri))

    def test_mysql_user_port(self):
        uri = "mysql://user@:123/test"
        self.assertDictEqual(dict(scheme="mysql",
                                  username='user',
                                  password='',
                                  host='localhost',
                                  port=123,
                                  database='test'),
                             parser(uri))

    def test_mysql_host_pass(self):
        uri = "mysql://:password@192.168.1.23/test"
        self.assertDictEqual(dict(scheme="mysql",
                                  username='root',
                                  password='password',
                                  host='192.168.1.23',
                                  port=3306,
                                  database='test'),
                             parser(uri))

    def test_mysql_port_pass(self):
        uri = "mysql://:password@:123/test"
        self.assertDictEqual(dict(scheme="mysql",
                                  username='root',
                                  password='password',
                                  host='localhost',
                                  port=123,
                                  database='test'),
                             parser(uri))

    def test_mysql_port_user_pass(self):
        uri = "mysql://user:password@:123/test"
        self.assertDictEqual(dict(scheme="mysql",
                                  username='user',
                                  password='password',
                                  host='localhost',
                                  port=123,
                                  database='test'),
                             parser(uri))

    def test_mysql_host_user_pass(self):
        uri = "mysql://user:password@192.168.1.23/test"
        self.assertDictEqual(dict(scheme="mysql",
                                  username='user',
                                  password='password',
                                  host='192.168.1.23',
                                  port=3306,
                                  database='test'),
                             parser(uri))

    def test_mysql_host_port_pass(self):
        uri = "mysql://:password@192.168.1.23:123/test"
        self.assertDictEqual(dict(scheme="mysql",
                                  username='root',
                                  password='password',
                                  host='192.168.1.23',
                                  port=123,
                                  database='test'),
                             parser(uri))

    def test_mysql_host_port_user(self):
        uri = "mysql://user@192.168.1.23:123/test"
        self.assertDictEqual(dict(scheme="mysql",
                                  username='user',
                                  password='',
                                  host='192.168.1.23',
                                  port=123,
                                  database='test'),
                             parser(uri))

    def test_mysql_host_port_user_pass(self):
        uri = "mysql://user:password@192.168.1.23:123/test"
        self.assertDictEqual(dict(scheme="mysql",
                                  username='user',
                                  password='password',
                                  host='192.168.1.23',
                                  port=123,
                                  database='test'),
                             parser(uri))


class PostgresqlURITest(unittest.TestCase):

    def setUp(self):
        if platform.system() == 'Darwin':
            self.user = getpass.getuser()
            self.password = ''
        elif platform.system() == 'windows':
            self.user = 'postgres'
            self.password = 'postgres'
        else:
            self.user = 'postgres'
            self.password = ''

        self.host = 'localhost'
        self.port = 5432

    def test_postgresql(self):
        uri = "postgresql:///test"
        self.assertDictEqual(dict(scheme="postgresql",
                                  username=self.user,
                                  password=self.password,
                                  host=self.host,
                                  port=self.port,
                                  database='test'),
                             parser(uri))

    def test_postgresql_host(self):
        uri = "postgresql://192.168.1.23/test"
        self.assertDictEqual(dict(scheme="postgresql",
                                  username=self.user,
                                  password=self.password,
                                  host="192.168.1.23",
                                  port=self.port,
                                  database='test'),
                             parser(uri))

    def test_postgresql_port(self):
        uri = "postgresql://:123/test"
        self.assertDictEqual(dict(scheme="postgresql",
                                  username=self.user,
                                  password=self.password,
                                  host=self.host,
                                  port=123,
                                  database='test'),
                             parser(uri))

    def test_postgresql_user(self):
        uri = "postgresql://user@/test"
        self.assertDictEqual(dict(scheme="postgresql",
                                  username='user',
                                  password=self.password,
                                  host=self.host,
                                  port=self.port,
                                  database='test'),
                             parser(uri))

    def test_postgresql_password(self):
        uri = "postgresql://:password@/test"
        self.assertDictEqual(dict(scheme="postgresql",
                                  username=self.user,
                                  password='password',
                                  host=self.host,
                                  port=self.port,
                                  database='test'),
                             parser(uri))

    def test_postgresql_host_port(self):
        uri = "postgresql://192.168.1.23:123/test"
        self.assertDictEqual(dict(scheme="postgresql",
                                  username=self.user,
                                  password=self.password,
                                  host='192.168.1.23',
                                  port=123,
                                  database='test'),
                             parser(uri))

    def test_postgresql_user_pass(self):
        uri = "postgresql://user:password@/test"
        self.assertDictEqual(dict(scheme="postgresql",
                                  username='user',
                                  password='password',
                                  host=self.host,
                                  port=self.port,
                                  database='test'),
                             parser(uri))

    def test_postgresql_user_host(self):
        uri = "postgresql://user@192.168.1.23/test"
        self.assertDictEqual(dict(scheme="postgresql",
                                  username='user',
                                  password=self.password,
                                  host='192.168.1.23',
                                  port=self.port,
                                  database='test'),
                             parser(uri))

    def test_postgresql_user_port(self):
        uri = "postgresql://user@:123/test"
        self.assertDictEqual(dict(scheme="postgresql",
                                  username='user',
                                  password=self.password,
                                  host=self.host,
                                  port=123,
                                  database='test'),
                             parser(uri))

    def test_postgresql_host_pass(self):
        uri = "postgresql://:password@192.168.1.23/test"
        self.assertDictEqual(dict(scheme="postgresql",
                                  username=self.user,
                                  password='password',
                                  host='192.168.1.23',
                                  port=self.port,
                                  database='test'),
                             parser(uri))

    def test_postgresql_port_pass(self):
        uri = "postgresql://:password@:123/test"
        self.assertDictEqual(dict(scheme="postgresql",
                                  username=self.user,
                                  password='password',
                                  host=self.host,
                                  port=123,
                                  database='test'),
                             parser(uri))

    def test_postgresql_port_user_pass(self):
        uri = "postgresql://user:password@:123/test"
        self.assertDictEqual(dict(scheme="postgresql",
                                  username='user',
                                  password='password',
                                  host=self.host,
                                  port=123,
                                  database='test'),
                             parser(uri))

    def test_postgresql_host_user_pass(self):
        uri = "postgresql://user:password@192.168.1.23/test"
        self.assertDictEqual(dict(scheme="postgresql",
                                  username='user',
                                  password='password',
                                  host='192.168.1.23',
                                  port=self.port,
                                  database='test'),
                             parser(uri))

    def test_postgresql_host_port_pass(self):
        uri = "postgresql://:password@192.168.1.23:123/test"
        self.assertDictEqual(dict(scheme="postgresql",
                                  username=self.user,
                                  password='password',
                                  host='192.168.1.23',
                                  port=123,
                                  database='test'),
                             parser(uri))

    def test_postgresql_host_port_user(self):
        uri = "postgresql://user@192.168.1.23:123/test"
        self.assertDictEqual(dict(scheme="postgresql",
                                  username='user',
                                  password=self.password,
                                  host='192.168.1.23',
                                  port=123,
                                  database='test'),
                             parser(uri))

    def test_postgresql_host_port_user_pass(self):
        uri = "postgresql://user:password@192.168.1.23:123/test"
        self.assertDictEqual(dict(scheme="postgresql",
                                  username='user',
                                  password='password',
                                  host='192.168.1.23',
                                  port=123,
                                  database='test'),
                             parser(uri))


class ParserErrorTest(unittest.TestCase):

    def test_unknow_scheme(self):
        with self.assertRaisesRegex(InvalidURI, r'unknow database') as a:
            parser('sqlit:///test')

    def test_without_datebase(self):
        with self.assertRaisesRegex(InvalidURI, r"need to point out the db's name") as a:
            parser('mysql://')

    def test_without_scheme(self):
        with self.assertRaisesRegex(InvalidURI, r'must have a database uri') as a:
            parser(':///test')

    def test_not_a_scheme(self):
        with self.assertRaisesRegex(InvalidURI, r'must have a database uri') as a:
            parser(':adf/test')


def error_suite():
    suite = unittest.TestSuite()
    suite.addTest(ParserErrorTest("test_unknow_scheme"))
    suite.addTest(ParserErrorTest("test_without_datebase"))
    suite.addTest(ParserErrorTest("test_without_scheme"))
    suite.addTest(ParserErrorTest("test_not_a_scheme"))
    return suite


def pg_suite():
    suite = unittest.TestSuite()
    suite.addTest(PostgresqlURITest("test_postgresql"))
    suite.addTest(PostgresqlURITest("test_postgresql_host"))
    suite.addTest(PostgresqlURITest("test_postgresql_port"))
    suite.addTest(PostgresqlURITest("test_postgresql_user"))
    suite.addTest(PostgresqlURITest("test_postgresql_password"))
    suite.addTest(PostgresqlURITest("test_postgresql_host_port"))
    suite.addTest(PostgresqlURITest("test_postgresql_user_pass"))
    suite.addTest(PostgresqlURITest("test_postgresql_user_host"))
    suite.addTest(PostgresqlURITest("test_postgresql_user_port"))
    suite.addTest(PostgresqlURITest("test_postgresql_host_pass"))
    suite.addTest(PostgresqlURITest("test_postgresql_port_pass"))
    suite.addTest(PostgresqlURITest("test_postgresql_port_user_pass"))
    suite.addTest(PostgresqlURITest("test_postgresql_host_user_pass"))
    suite.addTest(PostgresqlURITest("test_postgresql_host_port_pass"))
    suite.addTest(PostgresqlURITest("test_postgresql_host_port_user"))
    suite.addTest(PostgresqlURITest("test_postgresql_host_port_user_pass"))
    return suite


def mysql_suite():
    suite = unittest.TestSuite()
    suite.addTest(MysqlURITest("test_mysql"))
    suite.addTest(MysqlURITest("test_mysql_host"))
    suite.addTest(MysqlURITest("test_mysql_port"))
    suite.addTest(MysqlURITest("test_mysql_user"))
    suite.addTest(MysqlURITest("test_mysql_password"))
    suite.addTest(MysqlURITest("test_mysql_host_port"))
    suite.addTest(MysqlURITest("test_mysql_user_pass"))
    suite.addTest(MysqlURITest("test_mysql_user_host"))
    suite.addTest(MysqlURITest("test_mysql_user_port"))
    suite.addTest(MysqlURITest("test_mysql_host_pass"))
    suite.addTest(MysqlURITest("test_mysql_port_pass"))
    suite.addTest(MysqlURITest("test_mysql_port_user_pass"))
    suite.addTest(MysqlURITest("test_mysql_host_user_pass"))
    suite.addTest(MysqlURITest("test_mysql_host_port_pass"))
    suite.addTest(MysqlURITest("test_mysql_host_port_user"))
    suite.addTest(MysqlURITest("test_mysql_host_port_user_pass"))
    return suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner(verbosity=2)
    test_suite = error_suite()
    runner.run(test_suite)
    test_suite = pg_suite()
    runner.run(test_suite)
    test_suite = mysql_suite()
    runner.run(test_suite)
