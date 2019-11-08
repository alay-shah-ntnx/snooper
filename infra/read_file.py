#!/bin/python
import sys
from StringIO import StringIO
import re
import argparse
import ConfigParser


def main(args):

    conditions = [
    ]
    comments = StringIO()
    config = ConfigParser.SafeConfigParser()
    config.read(args.template_input)
    v_tuple = None
    for section in config.sections():
        if section.lower() == "version":
            v_tuple = (config.get(section, "number"),
                       config.get(section, "log"))
            continue
        try:
            print ("Adding Ignore => %s" % config.get(section, "comment"))
            comments.write("#   %s\n" % config.get(section, "comment"))
        except ConfigParser.NoOptionError:
            print ("Adding Ignore => %s" % section)
            comments.write("#   %s\n" % section)
        conditions.append(config.get(section, "expr"))

    if v_tuple is None:
        raise RuntimeError("Version section is required with number and "
                           "log field")
    with open(args.template) as fp:
        file_str = fp.read()

    x = re.search(r'\n(\s+)%%EXCEPTION_LIST%%', file_str)
    extra_space = ""
    if x:
        extra_space = x.group(1)

    var = StringIO()
    for c in conditions:
        var.write("%s!(%s) &&\n" % (extra_space, c))

    var.seek(0)
    file_str = file_str.replace("%%EXCEPTION_LIST%%\n",
                                var.getvalue().lstrip())

    comments.seek(0)
    file_str = file_str.replace("%%COMMENT_LIST%%\n",
                                comments.getvalue().lstrip())

    file_str = file_str.replace("%%VERSION%%",
                                ("# Version: %s\n"
                                 "# Log: %s" % (v_tuple)))
    with open(args.output, "w") as out_f:
        out_f.write(file_str)


def get_arguments(list_of_string):
    parser = argparse.ArgumentParser(description='Tempate Change Watcher.')
    parser.add_argument('--template-input', required=True,
                        help="Input file to template")
    parser.add_argument('--template', required=True,
                        help="Template for change.")
    parser.add_argument('--output', required=True,
                        help="Output file name.")
    args = parser.parse_args(list_of_string)
    return args


if __name__ == "__main__":
    args = get_arguments(sys.argv)
    main(args)
