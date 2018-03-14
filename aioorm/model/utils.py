def sort_models(models):
    models = set(models)
    seen = set()
    ordering = []

    def dfs(model):
        if model in models and model not in seen:
            seen.add(model)
            for rel_model in model._meta.refs.values():
                dfs(rel_model)
            if model._meta.depends_on:
                for dependency in model._meta.depends_on:
                    dfs(dependency)
            ordering.append(model)

    def names(m): return (m._meta.name, m._meta.table_name)
    for m in sorted(models, key=names):
        dfs(m)
    return ordering
