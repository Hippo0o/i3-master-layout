#!/usr/bin/env python3

from i3ipc import Connection

c = Connection()

tree = c.get_tree()
focused = tree.find_focused()
workspace = focused.workspace()
target = workspace.nodes[0]

# if focused is master find target from stack
def find_last(con):
    if len(con.nodes) > 1:
        return find_last(con.nodes[-1])

    return con
if target == focused:
    target = find_last(workspace)

c.command("[con_id=%d] swap container with con_id %d" % (focused.id, target.id))

# focus master after swap
tree = c.get_tree()
workspace = tree.find_focused().workspace()
c.command("[con_id=%d] focus" % workspace.nodes[0].id)
