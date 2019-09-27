from netaddr import IPNetwork, IPAddress
import os.path

def is_whitelisted(file_name, check_ip):
    if os.path.isfile(file_name) is False:
        return (False, "")
    with open(file_name) as f:
      lines = f.readlines()
      for line  in lines:
          if line.startswith('#'):
              continue
          chops = line.split(':',1)
          cleanup_string = lambda l: [x.strip() for x in l]
          ip_range, text = cleanup_string(chops)
          if IPAddress(check_ip) in IPNetwork(ip_range):
              return (True, text)

    return (False,"")



