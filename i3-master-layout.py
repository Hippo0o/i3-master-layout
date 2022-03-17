#!/usr/bin/env python3

from i3ipc import Event, Connection
from optparse import OptionParser


def get_comma_separated_args(option, opt, value, parser):
    setattr(parser.values, option.dest, value.split(","))


parser = OptionParser()
parser.add_option("-e",
                  "--exclude-workspaces",
                  dest="excludes",
                  type="string",
                  action="callback",
                  callback=get_comma_separated_args,
                  metavar="ws1,ws2,.. ",
                  help="List of workspaces that should be ignored.")
parser.add_option("-o",
                  "--outputs",
                  dest="outputs",
                  type="string",
                  action="callback",
                  callback=get_comma_separated_args,
                  metavar="HDMI-0,DP-0,.. ",
                  help="List of outputs that should be used instead of all.")
parser.add_option("-n",
                  "--nested",
                  dest="move_nested",
                  action="store_true",
                  help="Also move new windows which are created in nested containers.")
parser.add_option("-l",
                  "--stack-layout",
                  dest="stack_layout",
                  action="store",
                  metavar="LAYOUT",
                  help='The stack layout. ("tabbed", "stacked", "splitv") default: splitv',
                  choices=["tabbed", "stacked", "splitv"])  # splith not yet supported
parser.add_option("--disable-rearrange",
                  dest="disable_rearrange",
                  action="store_true",
                  help="Disable the rearrangement of windows when the master window disappears.")
(options, args) = parser.parse_args()


def is_excluded(window):
    if window is None:
        return True

    if window.type != "con":
        return True

    if window.workspace() is None:
        return True

    if window.floating is not None and "on" in window.floating:
        return True

    if options.excludes and window.workspace().name in options.excludes:
        return True

    if options.outputs and window.ipc_data["output"] not in options.outputs:
        return True

    return False


def grab_focused(c):
    tree = c.get_tree()
    focused_window = tree.find_focused()

    if is_excluded(focused_window):
        return None

    return focused_window


def find_last(con):
    if len(con.nodes) > 1:
        return find_last(con.nodes[-1])

    return con


def move_window(c, subject, target):
    c.command("[con_id=%d] mark --add move_target" % target.id)
    c.command("[con_id=%d] move container to mark move_target" % subject.id)
    c.command("[con_id=%d] unmark move_target" % target.id)


def get_workspace_container(c, focused_window):
    workspace = focused_window.workspace()
    sway_workaround(c, focused_window)
    if (len(workspace.nodes) == 1):
        return workspace.nodes[0]

    return workspace


def sway_workaround(c, focused_window):
    workspace = focused_window.workspace()
    if (len(workspace.nodes) <= 1):
        return

    c.command("[con_id=%d] focus" % workspace.nodes[0].id)
    c.command("focus parent; move container to workspace current")
    c.command("[con_id=%d] focus" % focused_window.id)


def set_stack_layout(c, workspace_container):
    if len(workspace_container.nodes) < 2:
        return

    layout = options.stack_layout or "splitv"

    last = find_last(workspace_container)

    # last window is also 2nd window
    # splith is not supported yet. idk how to differentiate between splith and nested splith.
    if last == workspace_container.nodes[1] and (last.layout != layout):
        c.command("[con_id=%d] split vertical" % last.id)
        c.command("[con_id=%d] layout %s" % (last.id, layout))


def on_window_new(c, e):
    new_window = grab_focused(c)

    if new_window is None:
        return

    workspace_container = get_workspace_container(c, new_window)

    # only windows created on workspace_container level get moved if nested option isn't enabled
    if options.move_nested is not True and new_window.parent != workspace_container:
        return

    # new window gets moved behind last window found
    move_window(c, new_window, find_last(workspace_container))

    set_stack_layout(c, workspace_container)


def on_window_focus(c, e):
    focused_window = grab_focused(c)

    if focused_window is None:
        return

    workspace_container = get_workspace_container(c, focused_window)

    if options.disable_rearrange is not True:
        # master window disappears and only stack container left
        if len(workspace_container.nodes) == 1:
            c.command("[con_id=%d] layout splith" % workspace_container.id)
            # move focused window (usually last focused window of stack) back to workspace_container level
            move_window(c, focused_window, workspace_container)
            # now the stack if it exists is first node and gets moved to the end of workspace_container
            move_window(c, workspace_container.nodes[0], workspace_container)

            # set_stack_layout(c, workspace_container)


def on_workspace_focus(c, e):
    focused_window = grab_focused(c)
    sway_workaround(c, focused_window)


def main():
    c = Connection()
    c.on(Event.WINDOW_FOCUS, on_window_focus)
    c.on(Event.WINDOW_NEW, on_window_new)
    c.on(Event.WORKSPACE_FOCUS, on_workspace_focus)

    try:
        c.main()
    except BaseException as e:
        print("restarting after exception:")
        print(e)
        main()


main()
