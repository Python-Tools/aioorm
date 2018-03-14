class MySQLDatabase(Database):
    field_types = {
        'AUTO': 'INTEGER AUTO_INCREMENT',
        'BIGAUTO': 'BIGINT AUTO_INCREMENT',
        'BOOL': 'BOOL',
        'DECIMAL': 'NUMERIC',
        'DOUBLE': 'DOUBLE PRECISION',
        'FLOAT': 'FLOAT',
        'UUID': 'VARCHAR(40)'}
    operations = {
        'LIKE': 'LIKE BINARY',
        'ILIKE': 'LIKE',
        'XOR': 'XOR'}
    param = '%s'
    quote = '`'

    commit_select = True
    for_update = True
    limit_max = 2 ** 64 - 1
    safe_create_index = False
    safe_drop_index = False

    def init(self, database, **kwargs):
        params = {'charset': 'utf8', 'use_unicode': True}
        params.update(kwargs)
        if 'password' in params:
            params['passwd'] = params.pop('password')
        super(MySQLDatabase, self).init(database, **params)

    def _connect(self):
        if mysql is None:
            raise ImproperlyConfigured('MySQL driver not installed!')
        return mysql.connect(db=self.database, **self.connect_params)

    def default_values_insert(self, ctx):
        return ctx.literal('() VALUES ()')

    def get_tables(self, schema=None):
        return [table for table, in self.execute_sql('SHOW TABLES')]

    def get_indexes(self, table, schema=None):
        cursor = self.execute_sql('SHOW INDEX FROM `%s`' % table)
        unique = set()
        indexes = {}
        for row in cursor.fetchall():
            if not row[1]:
                unique.add(row[2])
            indexes.setdefault(row[2], [])
            indexes[row[2]].append(row[4])
        return [IndexMetadata(name, None, indexes[name], name in unique, table)
                for name in indexes]

    def get_columns(self, table, schema=None):
        sql = """
            SELECT column_name, is_nullable, data_type
            FROM information_schema.columns
            WHERE table_name = %s AND table_schema = DATABASE()"""
        cursor = self.execute_sql(sql, (table,))
        pks = set(self.get_primary_keys(table))
        return [ColumnMetadata(name, dt, null == 'YES', name in pks, table)
                for name, null, dt in cursor.fetchall()]

    def get_primary_keys(self, table, schema=None):
        cursor = self.execute_sql('SHOW INDEX FROM `%s`' % table)
        return [row[4] for row in
                filter(lambda row: row[2] == 'PRIMARY', cursor.fetchall())]

    def get_foreign_keys(self, table, schema=None):
        query = """
            SELECT column_name, referenced_table_name, referenced_column_name
            FROM information_schema.key_column_usage
            WHERE table_name = %s
                AND table_schema = DATABASE()
                AND referenced_table_name IS NOT NULL
                AND referenced_column_name IS NOT NULL"""
        cursor = self.execute_sql(query, (table,))
        return [
            ForeignKeyMetadata(column, dest_table, dest_column, table)
            for column, dest_table, dest_column in cursor.fetchall()]

    def get_binary_type(self):
        return mysql.Binary

    def conflict_statement(self, on_conflict):
        if not on_conflict._action:
            return

        action = on_conflict._action.lower()
        if action == 'replace':
            return SQL('REPLACE')
        elif action == 'ignore':
            return SQL('INSERT IGNORE')
        elif action != 'update':
            raise ValueError('Un-supported action for conflict resolution. '
                             'MySQL supports REPLACE, IGNORE and UPDATE.')

    def conflict_update(self, on_conflict):
        if on_conflict._where or on_conflict._conflict_target:
            raise ValueError('MySQL does not support the specification of '
                             'where clauses or conflict targets for conflict '
                             'resolution.')

        updates = []
        if on_conflict._preserve:
            for column in on_conflict._preserve:
                entity = ensure_entity(column)
                expression = NodeList((
                    ensure_entity(column),
                    SQL('='),
                    fn.VALUES(entity)))
                updates.append(expression)

        if on_conflict._update:
            for k, v in on_conflict._update.items():
                if not isinstance(v, Node):
                    converter = k.db_value if isinstance(k, Field) else None
                    v = Value(v, converter=converter, unpack=False)
                updates.append(NodeList((ensure_entity(k), SQL('='), v)))

        if updates:
            return NodeList((SQL('ON DUPLICATE KEY UPDATE'),
                             CommaNodeList(updates)))

    def extract_date(self, date_part, date_field):
        return fn.EXTRACT(NodeList((SQL(date_part), SQL('FROM'), date_field)))

    def truncate_date(self, date_part, date_field):
        return fn.DATE_FORMAT(date_field, __mysql_date_trunc__[date_part])

    def get_noop_select(self, ctx):
        return ctx.literal('DO 0')
