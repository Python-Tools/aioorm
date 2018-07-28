class TableBase:
    __meta_Column__ = ["a", "b", "c"]
    __meta_Index__ = ["a"]
    __meta_PrimaryKey__ = ["b"]
    __meta_database__ = None

    @classmethod
    def _create(clz):
        pass

    @classmethod
    def _drop(clz):
        pass

    @classmethod
    def _insert(clz, **kwargs):
        pass

    @classmethod
    def _delete(clz, **kwargs):
        pass

    @classmethod
    def _select(clz, **kwargs):
        pass


class ViewBase:
    pass
