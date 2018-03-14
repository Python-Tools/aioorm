class IndexedFieldMixin:
    default_index_type = 'GiST'

    def __init__(self, index_type=None, *args, **kwargs):
        kwargs.setdefault('index', True)  # By default, use an index.
        super().__init__(*args, **kwargs)
        if self.index:
            self.index_type = index_type or self.default_index_type
        else:
            self.index_type = None
