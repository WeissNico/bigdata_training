#!/bin/bash

## This script wraps wkhtmltopdf into a virtual xserver.
xvfb-run -a --server-args="-screen 0, 1920x1080x32" /usr/bin/wkhtmltopdf -q $* 