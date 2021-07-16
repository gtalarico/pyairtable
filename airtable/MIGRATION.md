
# Migration

```
table = Airtable() ->
table = Table()
or
base = Base()


table.get_iter() ->
1. table.iterate()

table.get_all() ->
1. table.all() - weird if filted
3. table.list() - ?
2. table.filter() - weird if not filtered?


table.insert() ->
table.create

table.replace() ->
table.update(replace=True)

table.search -> use table.all(formula=)


table.match -> use table.first(formula=)
```
