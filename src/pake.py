#!/usr/bin/env python

import fsutils
import ui
import targets
import variables
import configurations
import parser

def parse_source_tree():
    for filename in fsutils.pake_files:
        parser.parse(filename)

    configuration = configurations.get_selected_configuration()
    variables.export_special_variables(configuration)

def main():
    import command_line

    parse_source_tree()

    configuration = configurations.get_selected_configuration()
    if configuration.name != "__default":
        ui.bigstep("configuration", str(configurations.get_selected_configuration()))

    if len(command_line.args.target) > 0:
        for target in command_line.args.target:
            targets.build(target)
    elif command_line.args.all:
        targets.build_all()
    else:
        ui.info(ui.BOLD + "targets found in this source tree:" + ui.RESET)
        ui.info(str(targets.targets))

        ui.info(ui.BOLD + "\nconfigurations:" + ui.RESET)
        ui.info(str(configurations.configurations))

if __name__ == '__main__':
    main()

