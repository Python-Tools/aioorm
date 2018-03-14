class AliasManager:
    def __init__(self):
        # A list of dictionaries containing mappings at various depths.
        self._counter = 0
        self._current_index = 0
        self._mapping = []
        self.push()

    @property
    def mapping(self):
        return self._mapping[self._current_index - 1]

    def add(self, source):
        if source not in self.mapping:
            self._counter += 1
            self[source] = 't%d' % self._counter
        return self.mapping[source]

    def get(self, source, any_depth=False):
        if any_depth:
            for idx in reversed(range(self._current_index)):
                if source in self._mapping[idx]:
                    return self._mapping[idx][source]
        return self.add(source)

    def __getitem__(self, source):
        return self.get(source)

    def __setitem__(self, source, alias):
        self.mapping[source] = alias

    def push(self):
        self._current_index += 1
        if self._current_index > len(self._mapping):
            self._mapping.append({})

    def pop(self):
        if self._current_index == 1:
            raise ValueError('Cannot pop() from empty alias manager.')
        self._current_index -= 1
