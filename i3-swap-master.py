#!/usr/bin/env python3

from i3ipc import Connection

c = Connection()

tree = c.get_tree()
focused = tree.find_focused()
target = focused.workspace().nodes[0]

def find_last(con):
    if len(con.nodes) > 1:
        return find_last(con.nodes[-1])

    return con

if target == focused:
    target = find_last(focused.workspace());

c.command("[con_id=%d] swap container with con_id %d" % (focused.id, target.id))
