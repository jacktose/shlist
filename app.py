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
import sys

SCHEMA: dict[str, tuple[tuple[str, ...], ...]] = {
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

con: sqlite3.Connection

def namedtuple_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    cls = namedtuple('Row', fields)
    return cls._make(row)

def initialize(schema, force=False):
    '''Create tables according to schema if they don't exist ... or even if they do, with force=True'''
    global con
    with con:
        con.execute('''PRAGMA foreign_keys = ON''')
        for table, cols in schema.items():
            if force:
                con.execute(f'DROP TABLE IF EXISTS {table}')
            colspec = ', '.join(' '.join(col) for col in cols)
            stmt = f'CREATE TABLE IF NOT EXISTS {table}({colspec})'
            con.execute(stmt)

def prepopulate_tables():
    '''Put some values into each table. For testing.'''
    list_id = add_list('breakfast')
    item_id = add_item(list_id, 'eggs')
    item_id = add_item(list_id, 'spam')
    item_id = add_item(list_id, 'ham')
    list_id = add_list('lunch')
    item_id = add_item(list_id, 'spamwich')
    list_id = add_list('supper')
    item_id = add_item(list_id, 'spamalot')

def reset(populate: bool = True):
    '''Wipe out the tables and recreate them, with test values.'''
    initialize(schema=SCHEMA, force=True)
    if populate:
        prepopulate_tables()

def add_list(name: str) -> int:
    '''Add a list to the list table. Return primary key id #.'''
    global con
    with con:
        res = con.execute('INSERT INTO list(name) VALUES(?) RETURNING id', (name,))
        id = res.fetchone()[0]
    return id

def list_id_from_name(name: str) -> int:
    '''Takes name, gives pimary key id #.'''
    global con
    with con:
        res = con.execute('SELECT id FROM list WHERE name = ?', (name,))
        id = int(res.fetchone()[0])
    return id

def add_item(list_id, name, description=None, url=None, price=None):
    '''Add item to item table. Return primary key id #.'''
    global con
    with con:
        res = con.execute('INSERT INTO item VALUES(NULL, ?, ?, ?, ?, ?) RETURNING id', (list_id, name, description, url, price))
        id = res.fetchone()[0]
    return id

def define_item_interactive(list_name: str = None, **kwargs):
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
                item[field] = select_list()[0]
        else:
            val = input(f'{field}: ')
            item[field] = None if val == '' else val
    return item

def select_list() -> tuple[int, str]:
    '''Show list names and prompt. Return id & name.'''
    global con
    list_lists()
    id = int(input('list #: '))
    with con:
        res = con.execute('SELECT name FROM list WHERE id = ?', (id, )).fetchone()
    if res is None:
        raise MenuError('invalid list #')
    return (id, res.name)

def select_item(list_id: int = None) -> tuple[int, str]:
    '''Select list (unless given) then item. Return item primary key id #.'''
    if list_id is None:
        list_id, _ = select_list()
    show_list(list_id)
    return int(input('item #: '))

def list_lists() -> None:
    '''Print list ids & names.'''
    global con
    with con:
        lists = con.execute('''SELECT * FROM list''').fetchall()
    print()
    print('Lists:')
    print(*(f'{row.id}: {row.name}' for row in lists), sep='\n')

def show_list_by_name(name: str) -> None:
    '''show_list wrapper that takes name instead of id.'''
    show_list(list_id_from_name(name))

def show_list(id: int) -> None:
    '''Print item ids & names in a list.'''
    global con
    with con:
        name = con.execute('''SELECT name FROM list WHERE id = ?''', (id, )).fetchone().name
        items = con.execute('''SELECT id, name FROM item WHERE list_id = ?''', (id, )).fetchall()
    if name is None:
        raise ValueError('invalid list #')
    print()
    print(f'{name}:')
    print(*(f'{i.id}: {i.name}' for i in items), sep='\n')

def show_item(id: int) -> None:
    '''Print all properties of an item.'''
    global con
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
    print()
    print(*(f'{k}: {v}' for k, v in item._asdict().items()), sep='\n')

def delete_item(id: int) -> None:
    '''Delete an item from the item table.'''
    global con
    with con:
        con.execute('''DELETE FROM item WHERE id = ?''', (id, ))

def delete_list(id: int) -> None:
    '''Delete a list from the list table. All its items will be deleted too.'''
    global con
    with con:
        con.execute('''DELETE FROM list WHERE id = ?''', (id, ))

class Menu:
    '''Menu options and error-handling wrappers'''
    def _list_lists(_):
        list_lists()
    def _show_list(_):
        show_list(select_list()[0])
    def _show_item(_):
        try:
            show_item(int(input('item number: ')))
        except ValueError as e:
            raise RecordError(*e.args) from e
    def _add_list(_):
        add_list(input('list name: '))
    def _add_item(_):
        add_item(**define_item_interactive())
    def _delete_item(_):
        try:
            delete_item(int(input('item number: ')))
        except ValueError as e:
            raise RecordError(*e.args) from e
    def _delete_list(_):
        delete_list(select_list()[0])
    def _reset(_):
        reset()
    def _exit(_):
        sys.exit()

    def __init__(self):
        self._actions: dict[int, tuple[str, callable]] = {i: tup for i, tup in enumerate(
            (
                ('list lists',       self._list_lists ),
                ('show list',        self._show_list  ),
                ('show item detail', self._show_item  ),
                ('create list',      self._add_list   ),
                ('create item',      self._add_item   ),
                ('delete item',      self._delete_item),
                ('delete list',      self._delete_list),
                ('reset',            self._reset      ),
                ('exit',             self._exit       ),
            ), start=1)
        }

    def run(self) -> callable:
        print()
        print(*(f'{i}: {action}'
                for i, (action, _)
                in self._actions.items()
               ), sep='\n')
        action = int(input('action: '))
        try:
            return self._actions[action][1]
        except KeyError as e:
            raise MenuError('invalid option #') from e

class MenuError(LookupError):
    '''User selected invald menu option.'''

class RecordError(LookupError):
    '''User entered non-existent item.'''


def main():
    global SCHEMA
    global con
    #os.remove('shlist.db')
    con = sqlite3.connect('shlist.db')
    #con.row_factory = sqlite3.Row
    con.row_factory = namedtuple_factory
    initialize(schema=SCHEMA)
    menu = Menu()
    try:
        while True:
            try:
                func = menu.run()
                func()
            except (MenuError, RecordError) as e:
                print(f'Error: {e}')
                continue
    #except Exception as e:
    #    print(e)
    #    raise
    finally:
        con.close()

if __name__ == '__main__':
    main()