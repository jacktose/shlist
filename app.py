#!/usr/bin/env python3

"""
shlist

A little wiSHLIST app. Mostly for learning DB programming.
But also, why isn't there a good wishlist webapp. Amazon, why did you nerf Universal Wishlist?!

by Jack
2024-03
"""

from collections import namedtuple
import os
from pprint import pp as pprint, pformat
import sqlite3

SCHEMA = {
    'list': (
        ('id',          'INTEGER', 'PRIMARY KEY'),
        ('name',        'TEXT'),
    ),
    'item': (
        ('id',          'INTEGER', 'PRIMARY KEY'),
        ('list_id',     'INTEGER', 'REFERENCES list(id) ON DELETE CASCADE'),
        ('name',        'TEXT'),
        ('description', 'TEXT'),
        ('url',         'TEXT'),
        ('price',       'INTEGER')
    ),
}

def namedtuple_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    cls = namedtuple('Row', fields)
    return cls._make(row)

def initialize(con, schema, force=False):
    '''Create tables according to schema if they don't exist ... or even if they do, with force=True'''
    with con:
        con.execute('''PRAGMA foreign_keys = ON''')
        for table, cols in schema.items():
            if force:
                con.execute(f'DROP TABLE IF EXISTS {table}')
            colspec = ', '.join(' '.join(col) for col in cols)
            stmt = f'CREATE TABLE IF NOT EXISTS {table}({colspec})'
            con.execute(stmt)

def prepopulate_tables(con):
    '''Put some values into each table. For testing.'''
    list_id = add_list(con, 'breakfast')
    item_id = add_item(con, list_id, 'eggs')
    item_id = add_item(con, list_id, 'spam')
    item_id = add_item(con, list_id, 'ham')
    list_id = add_list(con, 'lunch')
    item_id = add_item(con, list_id, 'spamwich')
    list_id = add_list(con, 'supper')
    item_id = add_item(con, list_id, 'spamalot')

def reset(con, populate: bool = True):
    '''Wipe out the tables and recreate them, with test values.'''
    initialize(con, schema=SCHEMA, force=True)
    if populate:
        prepopulate_tables(con)

def add_list(con, name: str) -> int:
    '''Add a list to the list table. Return primary key id #.'''
    with con:
        res = con.execute('INSERT INTO list(name) VALUES(?) RETURNING id', (name,))
        id = res.fetchone()[0]
    return id

def list_id_from_name(con, name: str) -> int:
    '''Takes name, gives pimary key id #.'''
    with con:
        res = con.execute('SELECT id FROM list WHERE name = ?', (name,))
        id = int(res.fetchone()[0])
    return id

def add_item(con, list_id, name, description=None, url=None, price=None):
    '''Add item to item table. Return primary key id #.'''
    with con:
        res = con.execute('INSERT INTO item VALUES(NULL, ?, ?, ?, ?, ?) RETURNING id', (list_id, name, description, url, price))
        id = res.fetchone()[0]
    return id

def define_item_interactive(con, list_name: str = None, **kwargs):
    '''Prompt for all item fields unless they're supplied as kwargs. Return dict.'''
    item = {}
    global SCHEMA
    for field, *_ in SCHEMA['item']:
        if field in ('id', 'rowid'):
            # Will be auto set on INSERT
            continue
        elif field in kwargs.keys():
            item[field] = kwargs[field]
        elif field == 'list_id':
            if list_name is not None:
                item[field] = list_id_from_name(list_name)
            else:
                item[field] = select_list(con)[0]
        else:
            val = input(f'{field}: ')
            item[field] = None if val == '' else val
    return item

def select_list(con) -> tuple[int, str]:
    '''Show list names and prompt. Return id & name.'''
    list_lists(con)
    id = int(input('list #: '))
    with con:
        res = con.execute('SELECT name FROM list WHERE id = ?', (id, )).fetchone()
    if res is None:
        raise ValueError('invalid list #')
    return (id, res.name)

def select_item(con, list_id: int = None) -> tuple[int, str]:
    '''Select list (unless given) then item. Return item primary key id #.'''
    if list_id is None:
        list_id, _ = select_list(con)
    show_list(con, list_id)
    return int(input('item #: '))

def list_lists(con) -> None:
    '''Print list ids & names.'''
    with con:
        lists = con.execute('''SELECT * FROM list''').fetchall()
    print('Lists:')
    print(*(f'{row.id}: {row.name}' for row in lists), sep='\n')

def show_list_by_name(con, name: str) -> None:
    '''show_list wrapper that takes name instead of id.'''
    show_list(con, list_id_from_name(name))

def show_list(con, id: int) -> None:
    '''Print item ids & names in a list.'''
    with con:
        name = con.execute('''SELECT name FROM list WHERE id = ?''', (id, )).fetchone().name
        items = con.execute('''SELECT id, name FROM item WHERE list_id = ?''', (id, )).fetchall()
    if name is None:
        raise ValueError('invalid list #')
    print(f'{name}:')
    print(*(f'{i.id}: {i.name}' for i in items), sep='\n')

def show_item(con, id: int) -> None:
    '''Print all properties of an item.'''
    with con:
        item = con.execute('''
            SELECT list.name AS list, item.*
            FROM item
            LEFT JOIN list ON item.list_id = list.id
            WHERE item.id = ?
            ''', (id, )
        ).fetchone()
    if item is None:
        raise ValueError('invalid item #')
    #pprint(item._asdict())
    print(*(f'{k}: {v}' for k, v in item._asdict().items()), sep='\n')

def delete_item(con, id: int) -> None:
    '''Delete an item from the item table.'''
    with con:
        con.execute('''DELETE FROM item WHERE id = ?''', (id, ))

def delete_list(con, id: int) -> None:
    '''Delete a list from the list table. All its items will be deleted too.'''
    with con:
        con.execute('''DELETE FROM list WHERE id = ?''', (id, ))


def main():
    global SCHEMA
    #os.remove('shlist.db')
    con = sqlite3.connect('shlist.db')
    #con.row_factory = sqlite3.Row
    con.row_factory = namedtuple_factory
    initialize(con, schema=SCHEMA)

    actions = {i: tup for i, tup in enumerate(
        (
            ('list lists',       lambda: list_lists( con                                )),
            ('show list',        lambda: show_list(  con, select_list(con)[0]           )),
            ('show item detail', lambda: show_item(  con, int(input('item number: '))   )),
            ('create list',      lambda: add_list(   con, input('list name: ')          )),
            ('create item',      lambda: add_item(   con, **define_item_interactive(con))),
            ('delete item',      lambda: delete_item(con, int(input('item number: '))   )),
            ('delete list',      lambda: delete_list(con, select_list(con)[0]           )),
            ('reset',            lambda: reset(      con                                )),
            ('exit',             'EXIT'),
        ), start=1)
    }
    while True:
        print()
        print(*(f'{i}: {action}' for i, (action, _) in actions.items()), sep='\n')
        action = int(input('action: '))
        try:
            func = actions[action][1]
        except KeyError:
            print('invalid option #')
            continue
        print()
        if func == 'EXIT':
            break
        func()
    con.close()

    pass


if __name__ == '__main__':
    main()