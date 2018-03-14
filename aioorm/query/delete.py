from .write import _WriteQuery


class Delete(_WriteQuery):
    def __sql__(self, ctx):
        super().__sql__(ctx)

        with ctx.scope_values(subquery=True):
            ctx.literal('DELETE FROM ').sql(self.table)
            if self._where is not None:
                ctx.literal(' WHERE ').sql(self._where)

            self._apply_ordering(ctx)
            return self.apply_returning(ctx)
