#from geoip import geolite2
from __future__ import print_function

import requests
import json
import sys
import os
import stat
import pandas as pd
import matplotlib
import argparse
import subprocess
import read_exception
matplotlib.use('Agg')

from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt
import numpy as np
from StringIO import StringIO
import shlex
from time import gmtime, strftime
import time
from collections import deque
import signal
import re
import fcntl
from datetime import datetime
import read_file

import warnings
import matplotlib.cbook
warnings.filterwarnings("ignore",
                        category=matplotlib.cbook.mplDeprecation)
# Alay's key!
KEY = '85cd2b619c064950812c3ba75b5ea4f4'
work_dir = 'work'
saved_query = 0
charged_query = 0


class GracefulInterruptHandler(object):

    def __init__(self, sig=signal.SIGINT):
        self.sig = sig
        self.last_int = 0

    def __enter__(self):

        self.interrupted = False
        self.released = False
        self.stop_req = False

        self.original_handler = signal.getsignal(self.sig)

        def handler(signum, frame):
            self.interrupted = True
            cur_int = int(time.time())
            if self.last_int > 0 and (cur_int - self.last_int) <= 1:
                self.stop_req = True
                self.release()
            else:
                print("Pressed Ctrl-C. Press again in a second to stop.")
                print("Will print stats soon!")
            self.last_int = cur_int

        signal.signal(self.sig, handler)

        return self

    def __exit__(self, type, value, tb):
        self.release()

    def release(self):

        print("In release")
        if self.released:
            return False

        signal.signal(self.sig, self.original_handler)

        self.released = True

        return True

    def serviced(self):
        self.interrupted = False


class _FilePtr(object):
    def __init__(self):
        self.pre_time = None
        self.cur_time = None

    def new_inode(self, file_pointer):
        if file_pointer is not None:
            valid_file = (os.path.exists(file_pointer) and
                          os.path.isfile(file_pointer))
            if not valid_file:
                return
            self.cur_time = os.stat(file_pointer)[stat.ST_INO]

    def is_changed(self, update_time=False):
        ret_status = False
        if self.cur_time is None:
            return False
        if self.pre_time is None:
            ret_status = True
        else:
            if self.cur_time != self.pre_time:
                ret_status = True

        if ret_status and update_time:
            self.pre_time = self.cur_time

        return ret_status

    def get_cur_time(self):
        return self.cur_time



def run_subscribe(cmd):
    p = subprocess.Popen(shlex.split(cmd),
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT,
                         universal_newlines=True,
                         preexec_fn=os.setpgrp)
    for stdout_line in iter(p.stdout.readline, ""):
        yield stdout_line
    return_code = p.wait()
    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, cmd)


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def run(cmd, err_is_fatal=True):
    if type(cmd) is str:
        cmd_list = shlex.split(cmd)
    else:
        cmd_list = cmd[:]

    p = subprocess.Popen(cmd_list,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)

    while p.poll():
        time.sleep(0.5)

    o, e = p.communicate()

    if err_is_fatal:
        if p.returncode == 0:
            return o
        else:
            raise Exception("%s ended with error.\nSTDERR:%s\nSTDOUT:%s"
                            "\nEXIT:%d" % (cmd, e, o, p.returncode))
    else:
        return (o, e, p.returncode)


def get_continent_name(name):
    mapping = dict()
    mapping['NA'] = 'North America'
    mapping['SA'] = 'South America'
    mapping['AF'] = 'Africa'
    mapping['AS'] = 'Asia'
    mapping['EU'] = 'Europe'
    mapping['OC'] = 'Oceania'

    return mapping.get(name, "Unknown")


def _get_data(ip):
    global charged_query
    global saved_query
    ts = strftime("%d_%b_%Y", gmtime())
    directory = os.path.join(work_dir, "ipinfo", ts)
    file_name = os.path.join(directory, '%s.json' % ip)
    if os.path.exists(file_name):
        with open(file_name) as f:
            saved_query += 1
            return json.load(f)

    if not os.path.exists(directory):
        os.makedirs(directory)

    URL = 'https://api.ipgeolocation.io/ipgeo?apiKey=%s' % (KEY)
    req = URL + "&ip=%s" % ip
    charged_query += 1
    response = requests.get(req)
    if (response.ok):
        jData = json.loads(response.content)
    else:
        jData = dict()
        jData['country_name'] = 'Unknown'
        jData['country_name'] = 'Unknown'
        jData['longitude'] = 0
        jData['latitude'] = 0
        jData['organization'] = 'Unknown'

    with open(file_name, 'w') as f:
        json.dump(jData, f)

    return jData


def write_loc_info(fp, ip, count, args):
    if args.geo_tagging:
        jData = _get_data(ip)
    else:
        jData = dict()
    fp.write("\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\"\n" % (ip,
                                       jData.get('country_name', "Unknown"),
                                       get_continent_name(jData.get('continent_code')),
                                       jData.get('longitude', 0),
                                       jData.get('latitude', 0),
                                       count,
                                       jData.get('organization', 'Unknown')
                 ))


def group_data(pd_df, args):
    if ((type(pd_df) is not pd.DataFrame) and
       os.path.isfile(pd_df)):
        pd_df = pd.read_csv(pd_df)

    myFile = StringIO()
    myFile.write("ipaddress,country,continent,lon,lat,n,org\n")
    headers = list(pd_df.columns.values)
    unique_dst = pd_df['ip.dst'].unique()
    grouped = pd_df.groupby('ip.dst').count()
    filtered_unique = list(grouped.index)
    for ip in filtered_unique:
        count = grouped.loc[ip, 'frame.number']
        write_loc_info(myFile, ip, count, args)
    myFile.seek(0)
    return myFile


def is_site_reachable(site):
    try:
        r = requests.get(site)
        return True
    except requests.exceptions.RequestException as e:
        return False


class IPException(object):
    def __init__(self, file_name):
        self.file_name = file_name
        self._last_ip = ''
        self._last_text = ''
        self._last_action = None

    def _get_response(self, ip):
        if self._last_ip != ip:
            self._last_ip = ip
            self._last_action, self._last_text = \
                read_exception.is_whitelisted(self.file_name, ip)

    def is_exception(self, ip):
        self._get_response(ip)
        return self._last_action

    def exception_msg(self, ip):
        self._get_response(ip)
        return self._last_text


def convert_pcap_to_csv(args, pcap, out="now.csv", header=False, f_ptr=None):
    generic_file_name = out

    exception = IPException('exception.txt')
    created = False
    file_name = os.path.splitext(pcap)[0]
    raw_name = file_name + '_raw.csv'
    filtered_name = file_name + '_filtered.csv'
    if f_ptr is None:
        pass
    else:
        f_ptr.new_inode(args.capture_exception)
        if f_ptr.is_changed(update_time=True):
            template_args = []
            template_args.append("--template-input")
            template_args.append(args.capture_exception)
            template_args.append("--template")
            template_args.append("tshark_out.sh.template")
            template_args.append("--output")
            template_args.append("./tshark_out.sh")
            read_file.main(read_file.get_arguments(template_args))

    outf = StringIO(run("./tshark_out.sh %s" % pcap))
    outf.seek(0)
    in_data = pd.read_csv(outf)
    pd.set_option('mode.chained_assignment', None)
    in_data['ip.dst'][pd.isnull(in_data['ip.dst'])] = '0.0.0.0'
    pd.reset_option('mode.chained_assignment')
    myFile = group_data(in_data, args)

    data = pd.read_csv(myFile, dtype={'ipaddress':np.unicode_})

    if data['n'].sum() != len(in_data.index):
        eprint("Constrained entries are not same as input. Please watchout")
        eprint("%s file parsing had error." % pcap)
        in_data.to_csv(raw_name)
        data.to_csv(filtered_name)
        created=True
    else:
        if len(in_data.index) > 0:
            d_ip = data.set_index('ipaddress').T.to_dict()
            lambdafunc = lambda x: pd.Series([d_ip.get(x['ip.dst'],dict()).get('country', 'Unknwon'),
                                              d_ip.get(x['ip.dst'],dict()).get('continent', 'Unknwon'),
                                              d_ip.get(x['ip.dst'],dict()).get('lon', 0),
                                              d_ip.get(x['ip.dst'],dict()).get('lat', 0),
                                              exception.is_exception(x['ip.dst']),
                                              exception.exception_msg(x['ip.dst']),
                                              get_epochtime(x['frame.time'])[0],
                                              get_epochtime(x['frame.time'])[1]
                                              ])
            in_data[['country', 'continent', 'lon','lat', 'whitelisted', 'reason', 'epochtime', 'nanosecond']] = in_data.apply(lambdafunc, axis=1)
            headers = list(in_data.columns.values)
            interest_headers = [h for h in headers if h not in ['_ws.col.Info']]
            #interest_headers.extend(['country', 'continent', 'lon','lat', 'whitelisted', 'reason'])
            if header:
                mode='w'
            else:
                mode='a'
            created = True
            trial_count = 5
            current_trial = 0
            while current_trial < trial_count:
                try:
                    with open(generic_file_name, mode=mode) as f_obj:
                        fcntl.flock(f_obj, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        in_data.to_csv(f_obj, mode=mode, columns=interest_headers, header=header)
                        fcntl.flock(f_obj, fcntl.LOCK_UN)
                    break
                except BlockingIOError:
                    current_trial += 1
                    time.sleep(0.1)

    return generic_file_name, created




def create_plot(csv_file, args):
    file_name = os.path.splitext(csv_file)[0]
    png_name = file_name + ".png"
    report_name = file_name + '_report.csv'
    in_data = pd.read_csv(csv_file)
    myFile = group_data(in_data, args)
    data = pd.read_csv(myFile, dtype={'ip':np.unicode_})
    my_dpi=300
    plt.figure(figsize=(2600/my_dpi, 1800/my_dpi), dpi=my_dpi)

    m=Basemap(llcrnrlon=-180, llcrnrlat=-65,urcrnrlon=180,urcrnrlat=80)
    m.drawmapboundary(fill_color='#A6CAE0', linewidth=0)
    m.fillcontinents(color='grey', alpha=0.3)
    m.drawcoastlines(linewidth=0.1, color="white")


    count = in_data.count()['frame.number']
    if count > 1:
        start, end = in_data.iloc[[0,-1]]['frame.time'].tolist()

    # prepare a color for each point depending on the continent.
    data['labels_enc'] = pd.factorize(data['country'])[0]
    m.scatter(data['lon'], data['lat'], s=data['n']/6, alpha=0.7, c=data['labels_enc'], cmap="Set1")
    if count > 1:
      plt.text( -170, -58,'%d records collected between\n%s and %s' % (count, start, end),
                ha='left', va='bottom', size=6, color='#555555')
    plt.savefig(png_name, bbox_inches='tight')
    plt.close()
    data.to_csv(report_name)

def make_dirs(lst):
    for d in lst:
        if not os.path.exists(d):
            os.makedirs(d)

def get_links():
    out = run("dumpcap -D")
    out_list=[]
    for line in out.splitlines():
        index, name = line.split(' ', 1)
        index = index[:-1]
        path = '/sys/class/net/%s' % name
        if os.path.islink(path):
            real_path = os.readlink(path)
            if '/pci' in real_path:
                out_list.append((index, name))

    return(out_list)

def get_epochtime(d):
    fmt = '%b %d, %Y %H:%M:%S %Z'
    PAT = '\.(\d+)'
    us_value = 0
    y = re.sub('\.\d+', '', d)
    s = re.match('.*' + PAT, d)
    if s:
        us_value = int(s.group(1))

    x = datetime.strptime(y, fmt)
    return (int(x.strftime('%s')), us_value)

class LoadFromFile (argparse.Action):
    def __call__ (self, parser, namespace, values, option_string = None):
        with values as f:
            parser.parse_args(f.read().split(), namespace)


def parse_arguments():
    parser = argparse.ArgumentParser(
                 description='Snooper Process.',
                 epilog=('Listing ports and capturing interface is mutually'
                         ' exclusive'))
    parser.add_argument('-g', '--with-graph',
                        action='store_true',
                        help=('Should produce graph as well '
                              '(api.ipgeolocation.io key is required'))
    parser.add_argument('-k', '--key', default=KEY, 
                        help='ipgeolocation.io key for geo location lookup')
    parser.add_argument('-p', '--api-port', default='8080', 
                        help='API port (Default 8080)')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-l', '--list-ports', action='store_true',
                        help='List available ports to capture and exit.')
    group.add_argument('-i', '--capture-interfaces', action='append', 
                        default=[],
                        help=('Interface indexes to capture data from.'
                              '  **NOTE: Must be physical port.'))
    parser.add_argument('-e', '--capture-exception',
                       help=('Config file to pass on exception.'
                             'File content can be modified runtime.'))
    parser.add_argument('-d', '--duration', type=int, default=10,
                        help=('Minimum granularity for continious capture '
                              '(min 5) in seconds. (Default = 10)'))

    parser.add_argument('-w', '--work-dir', default='work',
                        help='Work directory name.')
    parser.add_argument('-f', '--option-file', type=open, action=LoadFromFile,
                        help=('Option file inputs with just space seperated'
                              ' in single line. Note that any options from'
                              ' command line are set as they appear.'))

    args = parser.parse_args()

    if len(args.capture_interfaces) == 0 and not args.list_ports:
        eprint("\n\n-l (list port) or -i (capture port) is required.\n\n")
        parser.print_help()
        sys.exit(-1)

    if args.with_graph and args.key is None:
        eprint("With graph requires access key for api.ipgeolocation.io")
        sys.exit(-1)

    if args.key == KEY:
        eprint("Using default key. It may not work all the time!")

    return args

if __name__ == "__main__":
    config = dict()
    available_files = deque()
    pcap_file = 'file_del.pcap'
    csv_file = "now_v2.csv"
    check_site_url = 'https://api.ipgeolocation.io'
    link_tup = get_links()
    site_reachable = is_site_reachable(check_site_url)

    args = parse_arguments()
    if args.list_ports:
        for tup in link_tup:
            print("%s  -->  %s" % (tup[0], tup[1]))
        sys.exit(0)

    for interface in args.capture_interfaces:
        dictionary = dict(link_tup)
        if interface in dictionary.keys() or interface in dictionary.values():
            continue
        else:
            eprint("Interface %s not found." % interface)
            eprint("Valid interfaces are\n"
                   "%s" % '\n'.join(['%s  -->  %s' % (t[0], t[1]) for t in link_tup]))
            sys.exit(-1)

    if site_reachable is False:
        if args.with_graph:
            eprint("Can't reach to %s. Aborting." % check_site_url)
            sys.exit(-2)

    if args.key is not None:
        if site_reachable:
            args.geo_tagging = True
        else:
            eprint("Can't do geo tagging since "
                   "%s unreachable" % check_site_url)
            args.geo_tagging = False

    work_dir = args.work_dir
    interface = ['-i'] * (2*len(args.capture_interfaces))
    interface[1::2] = args.capture_interfaces

    directory = os.path.join(work_dir, 'pcaps')
    pcap_full_file = os.path.join(directory, pcap_file)
    _csv_file = os.path.join(work_dir, csv_file)
    config['csv_file'] = _csv_file

    make_dirs([work_dir, directory])
    cmd = ("dumpcap  --time-stamp-type host "
           "%s  -b duration:%d -q -w %s" % (' '.join(interface),
                                            args.duration,
                                            pcap_full_file))
    dmi_1 = run('dmidecode -t 1')
    UUID_RE = r"UUID:\s+(.*)\s"

    uuid = re.search(UUID_RE, dmi_1)

    if uuid:
        config['uuid'] = uuid.group(1)
    else:
        config['uuid'] = 'Unknown'

    file_Created = os.path.isfile(_csv_file)
    with open('config.json', 'wb') as w:
        json.dump(config, w)

    with GracefulInterruptHandler() as h:
        f_ptr = _FilePtr()
        for index, out in enumerate(run_subscribe(cmd)):
            if h.interrupted:
                h.serviced()
                print("Saved GEO Query: %d" % saved_query)
                print("Charged GEO Query: %d" % charged_query)
                try:
                    print("Savings: %.2f%%" % (100.0*saved_query/(1.0*(saved_query+charged_query))))
                except ZeroDivisionError:
                    print("Savings: NA")

            if h.stop_req:
                break
            # File: file_del_00001_20181013153113.pcap
            sp = out.strip().split(':')
            last_line = out.strip().startswith('Packets received')
            if sp[0] != 'File' and not last_line:
                continue
            file_gen = sp[-1].strip()
            if not last_line:
                print("File being generated... %s" % file_gen)
                available_files.append(file_gen)
            if ((len(available_files) > 1) or
               (last_line and len(available_files) > 0)):
                process_file = available_files.popleft()
                print("Process %s" % process_file)
                csv_name, new_entry = convert_pcap_to_csv(args,
                                                          pcap=process_file,
                                                          out=_csv_file,
                                                          header=not file_Created,
                                                          f_ptr=f_ptr
                                                          )
                if new_entry:
                    file_Created = True
                    print("\t*** WARNING: Suspect found!")
                    if args.with_graph:
                        create_plot(csv_name, args)
                else:
                    os.remove(process_file)

    sys.exit(0)
