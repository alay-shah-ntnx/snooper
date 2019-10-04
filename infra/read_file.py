#!/bin/python
from StringIO import StringIO
import re
import argparse
import ConfigParser


def main(args):

    conditions = [
    ]
    comments = StringIO()
    config = ConfigParser.ConfigParser()
    config.read(args.template_input)
    for section in config.sections():
        print ("Adding Ignore => %s" % config.get(section, "comment"))
        comments.write("# %s\n" % config.get(section, "comment"))
        conditions.append(config.get(section, "expr"))

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

    with open(args.output, "w") as out_f:
        out_f.write(file_str)
        out_f.write(comments.getvalue())


def get_arguments():
    parser = argparse.ArgumentParser(description='Tempate Change Watcher.')
    parser.add_argument('--template-input', required=True,
                        help="Input file to template")
    parser.add_argument('--template', required=True,
                        help="Template for change.")
    parser.add_argument('--output', required=True,
                        help="Output file name.")
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = get_arguments()
    main(args)
