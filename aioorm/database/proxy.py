
class Proxy:
    """代理.
    用于作为占位符,在初始化后本身没有任何功能,但为其指定一个被代理对象后就可以通过访问代理来访问对象的内容了.
    本代码来自peewee中的代理实现,个人认为非常简练好用,其意义在于:
    1. 屏蔽对对象直接的写操作,避免对象被篡改
    2. 重写__getattr__以提供一定的访问控制
    用法:
    >>> p = Proxy()
    >>> class A:
    ...     x=1
    ...     y=2
    >>> a = A()
    >>> p.attach_callback(lambda x: print(x.x**2))
    >>> p.attach_callback(lambda x: print(x.y**2))
    >>> p.initialize(a)
    1
    4
    >>> print(p.x)
    1
    protected:
        _callbacks (List[function]): 保存要在调用了`initialize`后执行的回调函数,回调函数的参数都是`initialize`的参数.
    """

    __slots__ = ('obj', '_callbacks')

    def __init__(self):
        self._callbacks = []
        self.initialize(None)

    def initialize(self, obj: Any):
        """[summary]
        Args:
            obj ([type]): [description]
        """

        self.obj = obj
        for callback in self._callbacks:
            callback(obj)

    def attach_callback(self, callback):
        self._callbacks.append(callback)

    def __getattr__(self, attr):
        if self.obj is None:
            raise AttributeError('Cannot use uninitialized Proxy.')
        return getattr(self.obj, attr)

    def __setattr__(self, attr, value):
        if attr not in self.__slots__:
            raise AttributeError('Cannot set attribute on proxy.')
        return super().__setattr__(attr, value)
