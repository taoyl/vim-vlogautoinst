# vim:fileencoding=utf-8:noet
""" Vim Utils.
    Copyright (C) 2020 Yuliang Tao - All Rights Reserved.
    You may use, distribute and modify this code under the terms of the GNU General Public License
    as published by the Free Software Foundation, either version 3 of the License, or any later
    version.

    You should have received a copy of the GNU General Public License along with this file.
    If not, see <http://www.gnu.org/licenses/>.

    This package requires the following packages:
    1. Python 3.7 or later
    2. Pyverilog 1.2 or later
"""

import re

def echo(msg, severity='Warning'):
    return f'echohl {severity}Msg | echo "{msg}" | echohl None'


def insert(buf, lines, ln):
    buf.append(lines.split('\n'), ln - 1)


def delete(buf, start_ln, end_ln):
    del buf[(start_ln-1):end_ln]


def replace(buf, lines, start_ln, end_ln):
    delete(buf, start_ln, end_ln)
    insert(buf, lines, start_ln)