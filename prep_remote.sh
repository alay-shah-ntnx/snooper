#!/bin/bash

scp get-pipe.py \
    setmeup.sh \
    v1.1.0.tar.gz \
    snooper.tar.gz \
    wireshark-2.6.3-1.x86_64.rpm \
    wireshark-qt-2.6.3-1.x86_64.rpm \
    root@$1:~/
