from aioorm.const import ROW


class _ModelQueryHelper:
    default_row_type = ROW.MODEL

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self._database:
            self._database = self.model._meta.database

    def _get_cursor_wrapper(self, cursor):
        row_type = self._row_type or self.default_row_type
        if row_type == ROW.MODEL:
            return self._get_model_cursor_wrapper(cursor)
        elif row_type == ROW.DICT:
            return ModelDictCursorWrapper(cursor, self.model, self._returning)
        elif row_type == ROW.TUPLE:
            return ModelTupleCursorWrapper(cursor, self.model, self._returning)
        elif row_type == ROW.NAMED_TUPLE:
            return ModelNamedTupleCursorWrapper(cursor, self.model,
                                                self._returning)
        elif row_type == ROW.CONSTRUCTOR:
            return ModelObjectCursorWrapper(cursor, self.model,
                                            self._returning, self._constructor)
        else:
            raise ValueError('Unrecognized row type: "%s".' % row_type)

    def _get_model_cursor_wrapper(self, cursor):
        return ModelObjectCursorWrapper(cursor, self.model, [], self.model)


class _ModelWriteQueryHelper(_ModelQueryHelper):
    def __init__(self, model, *args, **kwargs):
        self.model = model
        super(_ModelWriteQueryHelper, self).__init__(model, *args, **kwargs)

    def _set_table_alias(self, ctx):
        table = self.model._meta.table
        ctx.alias_manager[table] = table.__name__
