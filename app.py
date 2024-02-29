#!/usr/bin/env python3

"""
shlist
"""

import os
from pprint import pprint
import sqlite3

SCHEMA = {
    'lists': (
        ('name',        'TEXT'),
    ),
    'items': (
        ('list_id',     'INTEGER'),
        ('name',        'TEXT'),
        ('description', 'TEXT'),
        ('url',         'TEXT'),
        ('price',       'INTEGER')
    ),
}

def initialize(con, schema, force=False):
    ''''''
    # TODO: check for existence
    with con:
        for table, cols in schema.items():
            if force:
                con.execute(f'DROP TABLE IF EXISTS {table}')
            colspec = ', '.join(' '.join(col) for col in cols)
            stmt = f'CREATE TABLE IF NOT EXISTS {table}({colspec})'
            con.execute(stmt)

def add_list(con, name: str):
    ''''''
    with con:
        res = con.execute('INSERT INTO lists VALUES(?) RETURNING rowid', (name,))
        rowid = res.fetchone()[0]
    return rowid

def list_id_from_name(con, name: str) -> int:
    with con:
        id = con.execute('SELECT rowid FROM lists WHERE name = ?', (name,)).fetchone()[0]
    return int(id)

def add_item(con, list_id, name, description=None, url=None, price=None):
    ''''''
    with con:
        res = con.execute('INSERT INTO items VALUES(?, ?, ?, ?, ?) RETURNING rowid', (list_id, name, description, url, price))
        rowid = res.fetchone()[0]
    return rowid

def define_item_interactive(con):
    ''''''
    item = {}
    global SCHEMA
    for field in SCHEMA['items']:
        if field == 'list_id':
            item[field] = select_list(con)[0]
        else:
            val = input(f'{field}: ')
            item[field] = None if val == '' else val
    return item

def select_list(con) -> tuple[int, str]:
    ''''''
    list_lists(con)
    id = int(input('list id: '))
    print()
    with con:
        res = con.execute('SELECT name FROM lists WHERE rowid = ?', (id, )).fetchone()
    return (id, res['name'])

def select_item(con, list_id=None) -> tuple[int, str]:
    ''''''
    if list_id is None:
        list_id, _ = select_list(con)
    show_list(con, list_id)
    return int(input('item #: '))

def list_lists(con) -> None:
    ''''''
    with con:
        lists = con.execute('SELECT rowid AS id, * FROM lists').fetchall()
    print('Lists:')
    print(*(f"{row['id']}: {row['name']}" for row in lists), sep='\n')

def show_list_by_name(con, name: str) -> None:
    show_list(con, list_id_from_name(name))

def show_list(con, id: int) -> None:
    ''''''
    with con:
        items = con.execute('''
            SELECT rowid AS id, name
            FROM items
            WHERE list_id = ?
            ''',
            (id, )
        ).fetchall()
    #pprint([dict(**i) for i in items])
    print(*(f"{i['id']}: {i['name']}" for i in items), sep='\n')

def show_item(con, id: int) -> None:
    ''''''
    with con:
        item = con.execute('''
            SELECT items.rowid AS id, items.*, lists.name AS list
            FROM items
            LEFT JOIN lists ON items.list_id = lists.rowid
            WHERE items.rowid = ?
        ''', (id, )).fetchone()
    pprint(dict(**item))

def main():
    global SCHEMA
    #os.remove('shlist.db')
    con = sqlite3.connect('shlist.db')
    con.row_factory = sqlite3.Row
    initialize(con, schema=SCHEMA)

    #list_id = add_list(con, 'breakfast')
    #item_id = add_item(con, list_id_from_name(con, 'breakfast'), 'eggs')

    actions = {i: tup for i, tup in enumerate(
        (
            ('list lists',       lambda: list_lists(con)),
            ('show list',        lambda: show_list(con, select_list(con)[0])),
            ('show item detail', lambda: show_item(con, int(input('item number: ')))),
            ('create list',      lambda: add_list(con, input('list name: '))),
            ('create item',      lambda: add_item(con, **define_item_interactive(con))),
            ('reset',            lambda: initialize(con, schema=SCHEMA, force=True)),
            ('exit',             'EXIT'),
        ), start=1)
    }
    while True:
        print()
        print(*(f'{i}: {action}' for i, (action, _) in actions.items()), sep='\n')
        action = int(input('action: '))
        print()
        try:
            func = actions[action][1]
        except IndexError:
            print('invalid option')
            continue
        if func == 'EXIT':
            break
        func()
    con.close()

    pass


if __name__ == '__main__':
    main()