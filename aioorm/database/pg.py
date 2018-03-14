class PostgresqlDatabase(Database):
    field_types = {
        'AUTO': 'SERIAL',
        'BIGAUTO': 'BIGSERIAL',
        'BLOB': 'BYTEA',
        'BOOL': 'BOOLEAN',
        'DATETIME': 'TIMESTAMP',
        'DECIMAL': 'NUMERIC',
        'DOUBLE': 'DOUBLE PRECISION',
        'UUID': 'UUID'}
    operations = {'REGEXP': '~'}
    param = '%s'

    commit_select = True
    compound_select_parentheses = True
    for_update = True
    returning_clause = True
    safe_create_index = False
    sequences = True

    def init(self, database, register_unicode=True, encoding=None, **kwargs):
        self._register_unicode = register_unicode
        self._encoding = encoding
        self._need_server_version = True
        super(PostgresqlDatabase, self).init(database, **kwargs)

    def _connect(self):
        if psycopg2 is None:
            raise ImproperlyConfigured('Postgres driver not installed!')
        conn = psycopg2.connect(database=self.database, **self.connect_params)
        if self._register_unicode:
            pg_extensions.register_type(pg_extensions.UNICODE, conn)
            pg_extensions.register_type(pg_extensions.UNICODEARRAY, conn)
        if self._encoding:
            conn.set_client_encoding(self._encoding)
        if self._need_server_version:
            self.set_server_version(conn.server_version)
            self._need_server_version = False
        return conn

    def set_server_version(self, version):
        if version >= 90600:
            self.safe_create_index = True

    def last_insert_id(self, cursor, query_type=None):
        try:
            return cursor if query_type else cursor[0][0]
        except (IndexError, KeyError, TypeError):
            pass

    def get_tables(self, schema=None):
        query = ('SELECT tablename FROM pg_catalog.pg_tables '
                 'WHERE schemaname = %s ORDER BY tablename')
        cursor = self.execute_sql(query, (schema or 'public',))
        return [table for table, in cursor.fetchall()]

    def get_indexes(self, table, schema=None):
        query = """
            SELECT
                i.relname, idxs.indexdef, idx.indisunique,
                array_to_string(array_agg(cols.attname), ',')
            FROM pg_catalog.pg_class AS t
            INNER JOIN pg_catalog.pg_index AS idx ON t.oid = idx.indrelid
            INNER JOIN pg_catalog.pg_class AS i ON idx.indexrelid = i.oid
            INNER JOIN pg_catalog.pg_indexes AS idxs ON
                (idxs.tablename = t.relname AND idxs.indexname = i.relname)
            LEFT OUTER JOIN pg_catalog.pg_attribute AS cols ON
                (cols.attrelid = t.oid AND cols.attnum = ANY(idx.indkey))
            WHERE t.relname = %s AND t.relkind = %s AND idxs.schemaname = %s
            GROUP BY i.relname, idxs.indexdef, idx.indisunique
            ORDER BY idx.indisunique DESC, i.relname;"""
        cursor = self.execute_sql(query, (table, 'r', schema or 'public'))
        return [IndexMetadata(row[0], row[1], row[3].split(','), row[2], table)
                for row in cursor.fetchall()]

    def get_columns(self, table, schema=None):
        query = """
            SELECT column_name, is_nullable, data_type
            FROM information_schema.columns
            WHERE table_name = %s AND table_schema = %s
            ORDER BY ordinal_position"""
        cursor = self.execute_sql(query, (table, schema or 'public'))
        pks = set(self.get_primary_keys(table, schema))
        return [ColumnMetadata(name, dt, null == 'YES', name in pks, table)
                for name, null, dt in cursor.fetchall()]

    def get_primary_keys(self, table, schema=None):
        query = """
            SELECT kc.column_name
            FROM information_schema.table_constraints AS tc
            INNER JOIN information_schema.key_column_usage AS kc ON (
                tc.table_name = kc.table_name AND
                tc.table_schema = kc.table_schema AND
                tc.constraint_name = kc.constraint_name)
            WHERE
                tc.constraint_type = %s AND
                tc.table_name = %s AND
                tc.table_schema = %s"""
        ctype = 'PRIMARY KEY'
        cursor = self.execute_sql(query, (ctype, table, schema or 'public'))
        return [pk for pk, in cursor.fetchall()]

    def get_foreign_keys(self, table, schema=None):
        sql = """
            SELECT
                kcu.column_name, ccu.table_name, ccu.column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON (tc.constraint_name = kcu.constraint_name AND
                    tc.constraint_schema = kcu.constraint_schema)
            JOIN information_schema.constraint_column_usage AS ccu
                ON (ccu.constraint_name = tc.constraint_name AND
                    ccu.constraint_schema = tc.constraint_schema)
            WHERE
                tc.constraint_type = 'FOREIGN KEY' AND
                tc.table_name = %s AND
                tc.table_schema = %s"""
        cursor = self.execute_sql(sql, (table, schema or 'public'))
        return [ForeignKeyMetadata(row[0], row[1], row[2], table)
                for row in cursor.fetchall()]

    def sequence_exists(self, sequence):
        res = self.execute_sql("""
            SELECT COUNT(*) FROM pg_class, pg_namespace
            WHERE relkind='S'
                AND pg_class.relnamespace = pg_namespace.oid
                AND relname=%s""", (sequence,))
        return bool(res.fetchone()[0])

    def get_binary_type(self):
        return psycopg2.Binary

    def conflict_statement(self, on_conflict):
        return

    def conflict_update(self, on_conflict):
        action = on_conflict._action.lower() if on_conflict._action else ''
        if action in ('ignore', 'nothing'):
            return SQL('ON CONFLICT DO NOTHING')
        elif action and action != 'update':
            raise ValueError('The only supported actions for conflict '
                             'resolution with Postgresql are "ignore" or '
                             '"update".')
        elif not on_conflict._update and not on_conflict._preserve:
            raise ValueError('If you are not performing any updates (or '
                             'preserving any INSERTed values), then the '
                             'conflict resolution action should be set to '
                             '"IGNORE".')
        elif not on_conflict._conflict_target:
            raise ValueError('Postgres requires that a conflict target be '
                             'specified when doing an upsert.')

        target = EnclosedNodeList([
            Entity(col) if isinstance(col, basestring) else col
            for col in on_conflict._conflict_target])

        updates = []
        if on_conflict._preserve:
            for column in on_conflict._preserve:
                excluded = NodeList((SQL('EXCLUDED'), ensure_entity(column)),
                                    glue='.')
                expression = NodeList((ensure_entity(column), SQL('='),
                                       excluded))
                updates.append(expression)

        if on_conflict._update:
            for k, v in on_conflict._update.items():
                if not isinstance(v, Node):
                    converter = k.db_value if isinstance(k, Field) else None
                    v = Value(v, converter=converter, unpack=False)
                else:
                    v = QualifiedNames(v)
                updates.append(NodeList((ensure_entity(k), SQL('='), v)))

        parts = [SQL('ON CONFLICT'),
                 target,
                 SQL('DO UPDATE SET'),
                 CommaNodeList(updates)]
        if on_conflict._where:
            parts.extend((SQL('WHERE'), QualifiedNames(on_conflict._where)))

        return NodeList(parts)

    def extract_date(self, date_part, date_field):
        return fn.EXTRACT(NodeList((date_part, SQL('FROM'), date_field)))

    def truncate_date(self, date_part, date_field):
        return fn.DATE_TRUNC(date_part, date_field)

    def get_noop_select(self, ctx):
        return ctx.sql(Select().columns(SQL('0')).where(SQL('false')))
