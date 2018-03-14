import warnings
import operator
from functools import wraps, reduce
from contextlib import contextmanager
from aioorm.const import MODEL_BASE
from aioorm.ast.join import Join
from aioorm.reflect import is_model
from aioorm.model.model_alias import ModelAlias
from aioorm.query.base import Query
from aioorm.query.utils import PrefetchQuery


def __deprecated__(s):
    warnings.warn(s, DeprecationWarning)


def __scope_context__(scope):
    @contextmanager
    def inner(self, **kwargs):
        with self(scope=scope, **kwargs):
            yield self
    return inner


class _callable_context_manager:
    def __call__(self, fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            with self:
                return fn(*args, **kwargs)
        return inner


def with_metaclass(meta, base=object):
    return meta(MODEL_BASE, (base,), {})


def merge_dict(source, overrides):
    merged = source.copy()
    if overrides:
        merged.update(overrides)
    return merged


def __bind_database__(meth):
    @wraps(meth)
    def inner(self, *args, **kwargs):
        result = meth(self, *args, **kwargs)
        if self._database:
            return result.bind(self._database)
        return result
    return inner


def __join__(join_type='INNER', inverted=False):
    def method(self, other):
        if inverted:
            self, other = other, self
        return Join(self, other, join_type=join_type)
    return method


def quote(path, quote_char):
    quotes = (quote_char, quote_char)
    if len(path) == 1:
        return path[0].join(quotes)
    return '.'.join([part.join(quotes) for part in path])


def database_required(method):
    @wraps(method)
    def inner(self, database=None, *args, **kwargs):
        database = self._database if database is None else database
        if not database:
            raise Exception('Query must be bound to a database in order '
                            'to call "%s".' % method.__name__)
        return method(self, database, *args, **kwargs)
    return inner


def __pragma__(name):
    def __get__(self):
        return self.pragma(name)

    def __set__(self, value):
        return self.pragma(name, value)
    return property(__get__, __set__)


def prefetch_add_subquery(sq, subqueries):
    fixed_queries = [PrefetchQuery(sq)]
    for i, subquery in enumerate(subqueries):
        if isinstance(subquery, tuple):
            subquery, target_model = subquery
        else:
            target_model = None
        if not isinstance(subquery, Query) and is_model(subquery) or \
           isinstance(subquery, ModelAlias):
            subquery = subquery.select()
        subquery_model = subquery.model
        fks = backrefs = None
        for j in reversed(range(i + 1)):
            fixed = fixed_queries[j]
            last_query = fixed.query
            last_model = fixed.model
            rels = subquery_model._meta.model_refs.get(last_model, [])
            if rels:
                fks = [getattr(subquery_model, fk.name) for fk in rels]
                pks = [getattr(last_model, fk.rel_field.name) for fk in rels]
            else:
                backrefs = last_model._meta.model_refs.get(subquery_model, [])
            if (fks or backrefs) and ((target_model is last_model) or
                                      (target_model is None)):
                break

        if not fks and not backrefs:
            tgt_err = ' using %s' % target_model if target_model else ''
            raise AttributeError('Error: unable to find foreign key for '
                                 'query: %s%s' % (subquery, tgt_err))

        if fks:
            expr = reduce(operator.or_, [
                (fk << last_query.select(pk))
                for (fk, pk) in zip(fks, pks)])
            subquery = subquery.where(expr)
            fixed_queries.append(PrefetchQuery(subquery, fks, False))
        elif backrefs:
            expr = reduce(operator.or_, [
                (backref.rel_field << last_query.select(backref))
                for backref in backrefs])
            subquery = subquery.where(expr)
            fixed_queries.append(PrefetchQuery(subquery, backrefs, True))

    return fixed_queries


def prefetch(sq, *subqueries):
    if not subqueries:
        return sq

    fixed_queries = prefetch_add_subquery(sq, subqueries)
    deps = {}
    rel_map = {}
    for pq in reversed(fixed_queries):
        query_model = pq.model
        if pq.fields:
            for rel_model in pq.rel_models:
                rel_map.setdefault(rel_model, [])
                rel_map[rel_model].append(pq)

        deps[query_model] = {}
        id_map = deps[query_model]
        has_relations = bool(rel_map.get(query_model))

        for instance in pq.query:
            if pq.fields:
                pq.store_instance(instance, id_map)
            if has_relations:
                for rel in rel_map[query_model]:
                    rel.populate_instance(instance, deps[rel.model])

    return pq.query
