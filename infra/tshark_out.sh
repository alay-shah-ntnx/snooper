#!/bin/bash
# List filter LINE BY LINE. No exception
#   source be supermicro MAC address
#   destination IP is NOT 10.xx.xx.xx (internal network)
#   not arp
#   Not targetting DHCPv6 multicast request
#   Not DHCPv6 further communication with multicast target
#   Not DHCPv6 0c:c4:7a:08:14:a8,33:33:ff:08:14:a8 (final leg for DHCPv6)
#   Not DHCPv4 noise
#   Not LLMNR (IPv6)
#   Local subnets (224.0.0.0/24)
#   Ignore SSDP
#   Ignore LLDP
#   Ignore LLDP
#   Ignore LLDP
#   Ignore CDP
#   Ignore Cisco Shared Spanning Tree Protocol
#               -Y "(eth.src[0:3] == 0c:c4:7a || eth.dst[0:3] == 0c:c4:7a) && 
if [ $# -eq 0 ]; then file="file"; else file="$1"; fi
tshark -nr $file\
               -Y "!(ip.dst == 10.0.0.0/8) &&
                   !(arp) &&
                   !(eth.dst == 33:33:00:01:00:02 && udp.dstport == 547) &&
                   !(eth.dst[0:5] == 33:33:00:00:00) &&
                   !(eth.src[3:3] == eth.dst[3:3] && eth.dst[0:3] == 33:33:ff) &&
                   !(ip.dst == 255.255.255.255 && udp.dstport == 67) &&
                   !(eth.dst == 33:33:00:01:00:03 && udp.dstport == 5355) &&
                   !(ip.dst == 224.0.0.0/8) &&
                   !(ip.dst == 239.255.255.250 && udp.dstport == 1900) &&
                   !(eth.dst == 01:80:c2:00:00:0e) &&
                   !(eth.dst == 01:80:c2:00:00:03) &&
                   !(eth.dst == 01:80:c2:00:00:00) &&
                   !(eth.dst == 01:00:0c:cc:cc:cc) &&
		   !(eth.dst == 01:00:0c:cc:cc:cd)
                   " \
    -t ad \
    -T fields \
        -e frame.number \
        -e frame.time \
        -e eth.src \
        -e eth.dst \
        -e ip.src \
        -e ip.dst \
        -e udp.srcport \
        -e udp.dstport \
        -e tcp.srcport \
        -e tcp.dstport \
        -e _ws.col.Protocol \
        -e _ws.col.Info \
    -E header=y -E separator=, -E quote=d

    #-o 'gui.column.format:"No.","%m","Destination","%d"' \
# tshark -o 'gui.column.format:"No.","%m","Time","%t","Source","%s","Destination","%d","Protocol","%p","Length","%L","Info","%i"'
