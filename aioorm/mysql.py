import aiomysql
from peewee import MySQLDatabase
from .context import _aio_atomic, aio_transaction, aio_savepoint
from .database import AioDatabase


class AioMySQLDatabase(AioDatabase, MySQLDatabase):

    def set_autocommit(self, autocommit):
        self.autocommit = autocommit

    def get_autocommit(self):
        if self.autocommit is None:
            self.set_autocommit(self.autocommit)
        return self.autocommit

    def transaction(self, transaction_type=None):
        return aio_transaction(self, transaction_type)
    commit_on_success = property(transaction)

    def savepoint(self, sid=None):
        if not self.savepoints:
            raise NotImplementedError
        return aio_savepoint(self, sid)

    def atomic(self, transaction_type=None):
        return _aio_atomic(self, transaction_type)

    async def commit(self):
        with self.exception_wrapper:
            await self.get_conn().commit()

    async def rollback(self):
        with self.exception_wrapper:
            await self.get_conn().rollback()

    async def _connect(self, database, loop=None, **kwargs):
        # if not mysql:
        #     raise ImproperlyConfigured('MySQLdb or PyMySQL must be installed.')
        conn_kwargs = {
            'charset': 'utf8',
            'use_unicode': True,
        }
        conn_kwargs.update(kwargs)
        return await aiomysql.create_pool(db=database, loop=loop,**conn_kwargs)

    async def get_tables(self, schema=None):
        cursor = await self.execute_sql('SHOW TABLES')
        return [row for row, in await cursor.fetchall()]

    async def get_indexes(self, table, schema=None):
        cursor = await self.execute_sql('SHOW INDEX FROM `%s`' % table)
        unique = set()
        indexes = {}
        for row in cursor.fetchall():
            if not row[1]:
                unique.add(row[2])
            indexes.setdefault(row[2], [])
            indexes[row[2]].append(row[4])
        return [IndexMetadata(name, None, indexes[name], name in unique, table)
                for name in indexes]

    async def get_columns(self, table, schema=None):
        sql = """
            SELECT column_name, is_nullable, data_type
            FROM information_schema.columns
            WHERE table_name = %s AND table_schema = DATABASE()"""
        cursor = await self.execute_sql(sql, (table,))
        pks = set(self.get_primary_keys(table))
        return [ColumnMetadata(name, dt, null == 'YES', name in pks, table)
                for name, null, dt in await cursor.fetchall()]

    async def get_primary_keys(self, table, schema=None):
        cursor = await self.execute_sql('SHOW INDEX FROM `%s`' % table)
        return [row[4] for row in await cursor.fetchall()
                if row[2] == 'PRIMARY']

    async def get_foreign_keys(self, table, schema=None):
        query = """
            SELECT column_name, referenced_table_name, referenced_column_name
            FROM information_schema.key_column_usage
            WHERE table_name = %s
                AND table_schema = DATABASE()
                AND referenced_table_name IS NOT NULL
                AND referenced_column_name IS NOT NULL"""
        cursor = await self.execute_sql(query, (table,))
        return [
            ForeignKeyMetadata(column, dest_table, dest_column, table)
            for column, dest_table, dest_column in await cursor.fetchall()]

    # TODO
    def get_binary_type(self):
        return mysql.Binary
