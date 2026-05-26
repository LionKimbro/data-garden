import lionscliapp as app

from data_garden import wiring
from data_garden import runtime


def run_default():
    wiring.wire()
    runtime.main()


def declare_cli():
    app.declare_app('datagarden', '0.1')
    app.describe_app('Interactive CIRA data garden workspace')
    app.describe_app(
        'Data Garden is a Tkinter workspace for arranging linked note nodes on a CIRA-shaped interaction runtime.',
        'l',
    )
    app.declare_projectdir('.datagarden')
    app.set_flag('search_upwards_for_project_dir', True)
    app.declare_cmd('', run_default)
    app.describe_cmd('', 'Launch the Data Garden GUI')


def main():
    declare_cli()
    app.main()


if __name__ == '__main__':
    main()
