#!/bin/sh
# Gowin Programmer GUI launcher
cd /opt/gowin-eda-programmer/bin
export PATH=/opt/gowin-eda-programmer/fake-bin:$PATH
exec /opt/gowin-eda-programmer/bin/programmer "$@"
