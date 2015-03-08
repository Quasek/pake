#!/usr/bin/env python

import os
import sys
import tempfile
import stat
import subprocess
import argparse
import marshal
import shutil
import threading

# local
import fsutils
import ui
import lexer
import compiler
import targets
import variables
import configurations

"""
    targets
"""
class CommonTargetParameters:
    def __init__(self, root_path, module_name, name):
        assert isinstance(module_name, str)
        assert isinstance(name, str)

        self.root_path = root_path
        self.module_name = module_name
        self.name = name
        self.artefacts = []
        self.prerequisites = []
        self.depends_on = []
        self.run_before = []
        self.run_after = []
        self.resources = []
        self.visible_in = []

class CxxParameters:
    def __init__(self):
        self.sources = []
        self.include_dirs = []
        self.compiler_flags = []
        self.built_targets = []

class Module:
    def __init__(self, target_deposit, filename):
        assert isinstance(filename, str)

        ui.debug("lexer " + filename)
        ui.push()

        self.target_deposit = target_deposit
        self.filename = filename
        self.name = self.__get_module_name(filename)
        self.lines = []
        self.base_dir = os.path.dirname(filename)

        self.tokens = lexer.parse(filename)

        self.__parse()

        variables.add(
            self.name,
            "$__path",
            lexer.Token.make_literal(os.path.dirname(self.filename)))

        variables.add_empty(
            self.name,
            "$__null")

        ui.pop()

    def __get_module_name(self, filename):
        base = os.path.basename(filename)
        (root, ext) = os.path.splitext(base)
        return root

    def __add_target(self, target):
        ui.debug("adding target: " + str(target))
        self.target_deposit.add_target(target)

    def __parse_set_or_append(self, it, append):
        token = it.next()
        if token.is_a(lexer.Token.VARIABLE):
            variable_name = token.content
        else:
            ui.parse_error(token)

        second_add = False
        while True:
            token = it.next()
            if token.is_a(lexer.Token.LITERAL) or token.is_a(lexer.Token.VARIABLE):
                if append or second_add:
                    variables.append(self.name, variable_name, token)
                else:
                    variables.add(self.name, variable_name, token)
                    second_add = True

            elif token.is_a(lexer.Token.NEWLINE):
                break
            else:
                ui.parse_error(token)

    # (something1 something2)
    def __parse_list(self, it):
        ret = []
        token = it.next()
        if token.is_a(lexer.Token.OPEN_PARENTHESIS):

            while True:
                token = it.next()
                if token.is_a(lexer.Token.LITERAL):
                    ret.append(token)
                elif token.is_a(lexer.Token.VARIABLE):
                    ret.append(token)
                elif token.is_a(lexer.Token.CLOSE_PARENTHESIS):
                    break
                else:
                    ui.parse_error(token)
        else:
            ui.parse_error(token)

        return ret

    # ($var1:$var2 something4:$var1)
    def __parse_colon_list(self, it):
        ret = []
        token = it.next()
        if token.is_a(lexer.Token.OPEN_PARENTHESIS):

            while True:
                token = it.next()

                first = None
                second = None

                if token.is_a(lexer.Token.LITERAL) or token.is_a(lexer.Token.VARIABLE):
                    first = token
                    token = it.next()
                    if token.is_a(lexer.Token.COLON):
                        token = it.next()
                        if token.is_a(lexer.Token.VARIABLE):
                            second = token
                            ret.append((first, second))
                        else:
                            ui.parse_error(token, msg="expected variable")
                    else:
                        ui.parse_error(token, msg="expected colon")
                elif token.is_a(lexer.Token.CLOSE_PARENTHESIS):
                    break
                else:
                    ui.parse_error(token)
        else:
            ui.parse_error(token)

        ui.debug("colon list: " + str(ret))
        return ret

    def __try_parse_target_common_parameters(self, common_parameters, token, it):
        if token.content == "depends_on":
            common_parameters.depends_on = self.__parse_list(it)
            return True
        elif token.content == "run_before":
            common_parameters.run_before = self.__parse_list(it)
            return True
        elif token.content == "run_after":
            common_parameters.run_after = self.__parse_list(it)
            return True
        elif token.content == "resources":
            common_parameters.resources = self.__parse_list(it)
            return True
        elif token.content == "visible_in":
            common_parameters.visible_in = self.__parse_list(it)
            return True

        return False

    def __try_parse_cxx_parameters(self, cxx_parameters, token, it):
        if token.content == "sources":
            cxx_parameters.sources = self.__parse_list(it)
            return True
        elif token.content == "include_dirs":
            cxx_parameters.include_dirs = self.__parse_list(it)
            return True
        elif token.content == "compiler_flags":
            cxx_parameters.compiler_flags = self.__parse_list(it)
            return True

        return False

    def __parse_application_target(self, target_name, it):
        link_with = []
        library_dirs = []

        common_parameters = CommonTargetParameters(
            os.path.dirname(self.filename),
            self.name,
            target_name)

        cxx_parameters = CxxParameters()

        while True:
            token = it.next()
            if token.is_a(lexer.Token.LITERAL):
                if self.__try_parse_target_common_parameters(common_parameters, token, it): pass
                elif self.__try_parse_cxx_parameters(cxx_parameters, token, it): pass
                elif token.content == "link_with": link_with = self.__parse_list(it)
                elif token.content == "library_dirs": library_dirs = self.__parse_list(it)
                else: ui.parse_error(token)
            elif token.is_a(lexer.Token.NEWLINE):
                break
            else:
                ui.parse_error(token)

        target = targets.Application(common_parameters, cxx_parameters, link_with, library_dirs)
        self.__add_target(target)

    def __parse_static_library(self, target_name, it):
        common_parameters = CommonTargetParameters(
            os.path.dirname(self.filename),
            self.name,
            target_name)

        cxx_parameters = CxxParameters()

        while True:
            token = it.next()
            if token.is_a(lexer.Token.LITERAL):
                if self.__try_parse_target_common_parameters(common_parameters, token, it): pass
                elif self.__try_parse_cxx_parameters(cxx_parameters, token, it): pass
                else: ui.parse_error(token)
            elif token.is_a(lexer.Token.NEWLINE):
                break
            else:
                ui.parse_error(token)

        target = targets.StaticLibrary(common_parameters, cxx_parameters)
        self.__add_target(target)

    def __parse_phony(self, target_name, it):
        common_parameters = CommonTargetParameters(
            os.path.dirname(self.filename),
            self.name,
            target_name)

        cxx_parameters = CxxParameters()

        while True:
            token = it.next()
            if token.is_a(lexer.Token.LITERAL):
                if self.__try_parse_target_common_parameters(common_parameters, token, it): pass
                elif token.content == "artefacts": common_parameters.artefacts = self.__parse_list(it)
                elif token.content == "prerequisites": common_parameters.prerequisites = self.__parse_list(it)
                else: ui.parse_error(token)

            elif token.is_a(lexer.Token.NEWLINE):
                break
            else:
                ui.parse_error(token)

        target = targets.Phony(common_parameters)
        self.__add_target(target)

    def __parse_target(self, it):
        token = it.next()
        if token.is_a(lexer.Token.LITERAL):
            target_type = token.content

            token = it.next()
            if token.is_a(lexer.Token.LITERAL):
                target_name = token.content
            else:
                ui.parse_error(token)
        else:
            ui.parse_error(token)

        if target_type == "application":       self.__parse_application_target(target_name, it)
        elif target_type == "static_library":  self.__parse_static_library(target_name, it)
        elif target_type == "phony":           self.__parse_phony(target_name, it)
        else: ui.parse_error(token, msg="unknown target type: " + target_type)

    def __parse_configuration(self, it):
        configuration = configurations.Configuration()

        # name
        token = it.next()
        if token.is_a(lexer.Token.LITERAL):
            configuration.name = token.content
        else:
            ui.parse_error(token)

        while True:
            token = it.next()
            if token.is_a(lexer.Token.LITERAL):
                if token.content == "compiler": configuration.compiler = self.__parse_list(it)
                elif token.content == "archiver": configuration.archiver = self.__parse_list(it)
                elif token.content == "application_suffix": configuration.application_suffix = self.__parse_list(it)
                elif token.content == "compiler_flags": configuration.compiler_flags = self.__parse_list(it)
                elif token.content == "linker_flags": configuration.linker_flags = self.__parse_list(it)
                elif token.content == "export": configuration.export = self.__parse_colon_list(it)
                else: ui.parse_error(token)

            elif token.is_a(lexer.Token.NEWLINE):
                break
            else:
                ui.parse_error(token)

        ui.debug("configuration parsed:" + str(configuration))
        configurations.add_configuration(configuration)

    def __parse_directive(self, it):
        while True:
            token = it.next()

            if token.is_a(lexer.Token.LITERAL):
                if token.content == "set" or token.content == "append": self.__parse_set_or_append(it, token.content == "append")
                elif token.content == "target":                    self.__parse_target(it)
                elif token.content == "configuration":             self.__parse_configuration(it)
                else: ui.parse_error(token, msg="expected directive")

            elif token.is_a(lexer.Token.NEWLINE):
                continue
            else:
                return False

    def __parse(self):
        it = iter(self.tokens)

        try:
            if not self.__parse_directive(it):
                ui.parse_error(msg="unknown :(")
        except StopIteration:
            ui.debug("eof")

def parse_source_tree(target_deposit):
    for filename in fsutils.pake_files:
        module = Module(target_deposit, filename)

    configuration = configurations.get_selected_configuration()
    variables.export_special_variables(configuration)

def main():
    import command_line

    target_deposit = targets.TargetDeposit()

    parse_source_tree(target_deposit)

    ui.bigstep("configuration", str(configurations.get_selected_configuration()))

    if len(command_line.args.target) > 0:
        for target in command_line.args.target:
            target_deposit.build(target)
    elif command_line.args.all:
        target_deposit.build_all()
    else:
        ui.info(ui.BOLD + "targets found in this source tree:" + ui.RESET)
        ui.info(str(target_deposit))

if __name__ == '__main__':
    main()

