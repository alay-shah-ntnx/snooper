import pandas as pd
import json
import connexion
from connexion.resolver import RestyResolver
from datetime import datetime, timedelta
import re

mapping = [
('Unnamed: 0', 'index'), 
('frame.number', 'frame_number'), 
('frame.time', 'time'),
('eth.src', 'eth_src'),
('eth.dst', 'eth_dst'),
('ip.src', 'ip_src'),
('ip.dst', 'ip_dst'),
('udp.srcport', 'udp_srcport'),
('udp.dstport', 'udp_dstport'),
('tcp.srcport', 'tcp_srcport'),
('tcp.dstport', 'tcp_dstport'),
('_ws.col.Protocol', 'ws_protocol'),
('country', 'country'),
('continent', 'continent'),
('lon', 'longitude'),
('lat', 'latitude'),
('whitelisted', 'whitelisted'),
('reason', 'note')
]

def get_config(file_name='config.json'):
    try:
        with open(file_name) as f:
            j = json.load(f)
            return j
    except EnvironmentError:
        pass
    return dict()

def rename_dict(in_dict):
    for defined_map in mapping:
        in_dict[defined_map[1]] = in_dict.pop(defined_map[0])

    return in_dict

def get_uuid():
    config = get_config()
    return {"uuid" : config.get('uuid', 'Unknown')}

def read_by_time(found_in):
    in_value = found_in.upper()
    ret_list = list()
    config = get_config()
    if config:
        PAT = '(\d+)([WDHMS])'
        mapping = {
          'W': 'weeks',
          'D': 'days',
          'H': 'hours',
          'M': 'minutes',
          'S': 'seconds'
        }
        argument = dict()
        for x in re.finditer(PAT, in_value):
            x.group(1)
            argument[mapping.get(x.group(2),'S')] = int(x.group(1))

        
        d = (datetime.utcnow() - 
             timedelta(**argument) - 
             datetime(1970,1,1)).total_seconds()

        d = int(d)
        try:
            df = pd.read_csv(config.get('csv_file'))
            filtered = df.loc[df['epochtime'] >= d]
            filtered = filtered.where((pd.notnull(filtered)), None)
            for index, row in filtered.iterrows():
                d = row.to_dict()
                ret_list.append(rename_dict(d))
        except IOError:
            pass

    return ret_list

def read():
    ret_list = list()
    config = get_config()
    if config:
        try:
            df = pd.read_csv(config.get('csv_file'))
            df = df.where((pd.notnull(df)), None)
            for index, row in df.iterrows():
                d = row.to_dict()
                ret_list.append(rename_dict(d))
        except IOError:
            pass


    return ret_list


app = connexion.FlaskApp(__name__, specification_dir='./')
app.add_api('api.yaml', resolver=RestyResolver('api'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
