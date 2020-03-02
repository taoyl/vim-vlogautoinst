# vim:fileencoding=utf-8:noet
""" Verilog Auto Instantiation.
    Copyright (C) 2020 Yuliang Tao - All Rights Reserved.
    You may use, distribute and modify this code under the terms of the GNU General Public License
    as published by the Free Software Foundation, either version 3 of the License, or any later
    version.

    You should have received a copy of the GNU General Public License along with this file.
    If not, see <http://www.gnu.org/licenses/>.

    This package requires the following packages:
    1. Python 3.6 or later
    2. Pyverilog 1.2 or later
"""

import argparse
import glob
import os
import pprint
import re
import sys
import pyverilog.utils.version
from pyverilog.dataflow.dataflow_analyzer import VerilogDataflowAnalyzer
from pyverilog.dataflow.dataflow import DFIntConst, DFOperator
from pyverilog.vparser.parser import parse
from pyverilog.vparser.plyparser import ParseError
from pyverilog.vparser.ast import InstanceList, ParamArg, Instance, PortArg


def parse_args(args):
    """Parse vim command argements.
    """

    parser = argparse.ArgumentParser(prog='VAI', description="Verilog Auto Instantiation",
                                     usage=('VAI [-i|--inst inst_name] [-r|--regexp m_pat s_pat]'
                                            '[--reset] [-d|--declare]'))
    group1 = parser.add_mutually_exclusive_group()
    group1.add_argument('-i', '--inst', type=str, help='Specify instantiation name')
    group1.add_argument('-d', '--declare', action='store_true',
                       help='Declare instport as wires and external port')
    group2 = parser.add_mutually_exclusive_group()
    group2.add_argument('-r', '--regexp', nargs=2, type=str,
                        help='Change instport naming using python regexp')
    group2.add_argument('--reset', action='store_true',
                        help='Reset parameter value and instport name to default')
    return parser.parse_args(args)


def grep_vim_buf(vim_buf, pattern):
    """Grep lines matching the specified pattern from vim buffer.
    """

    re_pat = re.compile(rf'{pattern}')
    matched_lines = []
    for line in vim_buf:
        if re_pat.search(line):
            matched_lines.append(line.rstrip())
    return matched_lines


def find_declares_ln(vim_buf):
    """Find the line number of auto-declare: vai-auto-wire and vai-auto-port.
    """
    
    re_pat_prespace = re.compile(r'^(\s*)')
    re_pat_aws = re.compile(r'^\s*/\*\s*vai-auto-wire-begin\s*\*/')
    re_pat_awe = re.compile(r'^\s*/\*\s*vai-auto-wire-end\s*\*/')
    re_pat_aps = re.compile(r'^\s*/\*\s*vai-auto-port-begin\s*\*/')
    re_pat_ape = re.compile(r'^\s*/\*\s*vai-auto-port-end\s*\*/')
    ap_begin_ln, ap_end_ln, aw_begin_ln, aw_end_ln = (0, 0, 0, 0)
    ap_indent, aw_indent = (0, 0)
    for i, line in enumerate(vim_buf):
        if ap_begin_ln == 0 and re_pat_aps.search(line):
            ap_begin_ln = i + 1
            ap_indent = len(re_pat_prespace.search(line).group(1))
            continue
        if ap_end_ln == 0 and re_pat_ape.search(line):
            ap_end_ln = i + 1
            continue
        if aw_begin_ln == 0 and re_pat_aws.search(line):
            aw_indent = len(re_pat_prespace.search(line).group(1))
            aw_begin_ln = i + 1
            continue
        if aw_end_ln == 0 and re_pat_awe.search(line):
            aw_end_ln = i + 1
            continue
    return {'ap': (ap_begin_ln, ap_end_ln, ap_indent),
            'aw': (aw_begin_ln, aw_end_ln, aw_indent)}


def get_vai_files(vim_buf):
    """Get vai file list from vim buffer.
    """

    vai_file_lines = grep_vim_buf(vim_buf, r'^\s*//\s*vai-files:')
    vai_dir_lines = grep_vim_buf(vim_buf, r'^\s*//\s*vai-incdirs:')
    vai_vlog_files = []
    for l in vai_file_lines:
        vlog_files = l.split(':')[-1].replace(' ', '').split(',')
        vai_vlog_files += [x for x in vlog_files if os.path.exists(x)]
    # get all *.v/*.sv files in incdirs
    for l in vai_dir_lines:
        dirs = l.split(':')[-1].replace(' ', '').split(',') 
        for d in dirs:
            vai_vlog_files += glob.glob(os.path.join(d, '*.v'))
            vai_vlog_files += glob.glob(os.path.join(d, '*.sv'))
    return tuple(vai_vlog_files)


def get_instances(flist, vim_buf, inst_name=None):
    """Get instance information in flie list.

    Args:
    :param tuple flist: verilog file list.
    :param list vim_buf: vim buffer
    :param str inst_name: instance name.

    Returns: instance dict with parameters and ports.
    """

    # parse verilog files
    ast, __ = parse(flist)

    # precimpiled regexp patterns
    re_pat_cmt = re.compile(r'^\s*//')
    re_pat_prespace = re.compile(r'^(\s*)')
    re_pat_semicolon = re.compile(r';')
    re_pat_port_type = re.compile(r'//([WP]?)([IO]+)')

    inst_dict = {}
    # Source->Description->ModuleDef->InstanceList->Instance
    for mod_def in ast.children()[0].children()[0].children():
        if not isinstance(mod_def, InstanceList):
            continue
        # instances = [x for x in mod_def.children() if isinstance(x, Instance)]
        for i in mod_def.instances:
            # params = [x for x in i.children() if isinstance(x, ParamArg)]
            # ports = [x for x in i.children() if isinstance(x, PortArg)]
            # get parameter list
            param_dict = {p.paramname: str(p.argname) for p in i.parameterlist}
            #  get port list
            port_dict = {}
            for p in i.portlist:
                childen = tuple(map(str, p.argname.children()))
                instp_name = childen[0] if childen else str(p.argname)
                slice_expr = f"[{':'.join(childen[1:])}]" if childen else ''
                line_num = int(p.lineno)
                # get port type: WI/O, PI/O, or I/O
                mat = re_pat_port_type.search(vim_buf[line_num-1])
                port_type = mat.group(1) if mat else ''
                direction = mat.group(2) if mat else ''
                port_dict.update({str(p.portname): dict(instp=instp_name, slice=slice_expr, type=port_type,
                                      dir=direction)})
            port_ln = [int(p.lineno) for p in i.portlist]
            max_port_ln = max(port_ln) if port_ln else (i.lineno + 1)
            min_port_ln = min(port_ln) if port_ln else (i.lineno + 1)
            # print(f'max={max_port_ln}, min={min_port_ln}')
            # validate vai-auto-inst directive.
            # vai-auto-inst directive should be between the start line and the min port line
            valid_vai_inst = False
            re_pat_inst = re.compile(rf'{i.name}\s*\(\s*/\*\s*vai-auto-inst\s*\*/')
            # minus 1 because vim buffer index starts from 1
            for line in vim_buf[(i.lineno-1):(min_port_ln-1)]:
                if re_pat_cmt.search(line):
                    continue
                if re_pat_inst.search(line):
                    valid_vai_inst = True
            # stop if current instance doesn't have vai-auto-inst directive
            if not valid_vai_inst:
                continue

            # find the end line number.
            end_ln = max_port_ln
            # minus 1 because vim buffer index starts from 1
            for idx, line in enumerate(vim_buf[(max_port_ln-1):]):
                if re_pat_cmt.search(line):
                    continue
                if re_pat_semicolon.search(line):
                    end_ln += idx
                    break
            
            # get the indent
            mat = re_pat_prespace.search(vim_buf[i.lineno - 1])
            indent = len(mat.group(1)) if mat else 0

            inst_dict.update({i.name: {
                                        'mod': i.module,
                                        'begin_ln': i.lineno, 
                                        'end_ln': end_ln,
                                        'indent': indent,
                                        'param': param_dict,
                                        'port': port_dict }})
    return inst_dict if inst_name is None else inst_dict.get(inst_name, None)


def generate_declares(instances, windent=0, pindent=0):
    """Generate wire and external port declaration for inst ports.
    """
    
    # use dict to remove duplicated name
    wire_dict, port_dict = ({}, {})
    for inst in instances.values():
        len_list = [(len(v["instp"]), len(v["slice"])) for v in inst['port'].values()]
        max_instp_len, max_slice_len = tuple(map(max, list(zip(*len_list))))
        # wire declarations
        wires = {v['instp']: f'wire {v["slice"]:{max_slice_len}} {v["instp"]:{max_instp_len}};'
                 for v in inst['port'].values() if v['type'] == 'W'}
        wire_dict.update(wires)
        # port declarations 
        ports = {v['instp']:
                 (f'{"input" if v["dir"] == "I" else ("output" if v["dir"] == "O" else "inout")} '
                  f'{v["slice"]:{max_slice_len}} {v["instp"]}')
                for v in inst['port'].values() if v['type'] == 'P'}
        port_dict.update(ports)

    print(wire_dict)
    # wire declarations
    wire_declare_code = None
    if wire_dict:
        wire_indent = ' ' * windent
        wire_declare_code = f'{wire_indent}/* vai-auto-wire-begin */\n'
        wire_declare_code += f'{wire_indent}'
        wire_declare_code += f'\n{wire_indent}'.join(wire_dict.values())
        wire_declare_code += f'\n{wire_indent}/* vai-auto-wire-end */'

    # port declarations 
    port_declare_code = None
    if port_dict:
        port_indent = ' ' * pindent
        port_declare_code = f'{port_indent} /* vai-auto-port-begin */\n'
        port_declare_code += f'{port_indent},'
        port_declare_code += f'\n{port_indent},'.join(port_dict.values())
        port_declare_code += f'\n{port_indent} /* vai-auto-port-end */'

    return (port_declare_code, len(port_dict), wire_declare_code, len(wire_dict))


class VlogAutoInst:
    """Verilog Auto Instantiation.

    Args:
    :param tuple flist: verilog file list. If macros defined, put macro files prior to design file.
    :param str top_mod: top module.
    """

    def __init__(self, flist, top_mod):
        self.mod = top_mod 
        self.flist = flist
        self.analyzer = VerilogDataflowAnalyzer(flist, top_mod)
        try:
            self.analyzer.generate()
        except ParseError as pe:
            print(pe)

        # get params
        self.param_dict = self._get_params()
        # for k, v in self.param_dict.items():
        #     print(f'type_k={type(k)}, type_v={type(v)}, type_v.value={type(v.value)}')
        #     print(f'{k}={v}')
        # get port_dict
        self.port_dict = self._get_ports()

    def _get_param_value(self, param_list):
        param_dict = {}
        for k, v in self.analyzer.getBinddict().items():
            if k in param_list:
                if isinstance(v[0].tree, DFIntConst):
                    param_dict.update({str(k): v[0].tree})
                else:
                    print('Error: paramater tree is not a constant')
        return param_dict

    def _get_xsb_value(self, node):
        """Get the msb and lsb value of an terms.
        """

        node_val = None
        if isinstance(node, DFIntConst):
            node_val = node.eval()
        elif isinstance(node, DFOperator):
            node_val = int(eval(self._expr_map(node.tocode())))
        else:
            print(f'Invalid node format: {type(node)}:{node.tostr()}')
        return node_val

    def _expr_map(self, expr):
        """Replace parameters in expression with values.
        """

        new_expr = expr
        for k, v in self.param_dict.items():
            # change . to _
            name = str(k).replace('.', '_')
            new_expr = str(new_expr).replace(name, f'{v.eval()}')
        # print(f'expr={expr}, new_expr={new_expr}')
        return new_expr

    def _get_params(self):
        param_list = []
        for k, v in self.analyzer.getTerms().items():
            if 'Parameter' in v.termtype:
                param_list.append(v.name)
        return self._get_param_value(param_list)

    def _get_ports(self):
        port_dict = {}
        for k, v in self.analyzer.getTerms().items():
            port_dir = list({'Input', 'Output', 'Inout'} & v.termtype)
            if port_dir:
                msb_v, lsb_v = (None, None)
                direction = 'I' if port_dir[0] == 'Input' else \
                            ('O' if port_dir[0] == 'Output' else 'IO')
                msb_v = self._get_xsb_value(v.msb)
                lsb_v = self._get_xsb_value(v.lsb)
                port_dict.update({str(k).split('.')[-1]: {'dir': direction,
                                      'slice': f'[{msb_v}:{lsb_v}]' if msb_v != lsb_v else '',
                                      'instp': str(k).split('.')[-1],
                                      'type': 'W'
                                     }})
        return port_dict

    def update_inst(self, param_dict=None, port_dict=None, port_regexp=None):
        """Update parameter value and port based on custom changes.

        Args:
        :param dict param_dict: parameter dict {param: 'value'}
        :param dict port_dict: port dict {port_name: instport_name}
        :param tuple port_regexp: regexp for changing instport name, (pattern, sub_pattern)
        """

        # Update parameters' value
        if param_dict:
            # Convert str to DFIntConst first
            new_param_dict = {f'{self.mod}.{k}':DFIntConst(v) for k, v in param_dict.items()}
            self.param_dict.update(new_param_dict)
            # update port width
            self.port_dict = self._get_ports()

        # not necessary to update port dict if both port_dict and port_regexp are empty
        if not port_dict and not port_regexp:
            return

        # update instport name according to regexp and user's manual changes.
        sel_port_dict = port_dict if port_dict else self.port_dict
        if port_regexp:
            re_pat = re.compile(rf'{port_regexp[0]}')
            for k, v in sel_port_dict.items():
                sel_port_dict[k]['instp'] = re_pat.sub(rf'{port_regexp[1]}', v['instp'])
        for k, v in sel_port_dict.items():
            if k in self.port_dict:
                self.port_dict[k]['instp'] = v['instp']
                self.port_dict[k]['type'] = v['type']

    def reinst(self, flist=None):
        """Re-instantiate the whole design.

        Args:
        :param tuple flist: new file list for parse. If set to None, use the old flist.
        """

        new_flist = self.flist if flist is None else flist
        self.analyzer = VerilogDataflowAnalyzer(new_flist, self.mod)
        self.analyzer.generate()
        # get params
        self.param_dict = self._get_params()
        # get port_dict
        self.port_dict = self._get_ports()

    def generate_inst(self, inst_name, indent=0):
        """Generate instantiation code.
        """

        indent_lvl0 = ' ' * indent
        indent_lvl1 = f'{indent_lvl0}    '

        code = f'{indent_lvl0}{self.mod} '
        if self.param_dict:
            code += f'#(\n{indent_lvl1} .'
            # find the max length of parameter length
            max_k_len = max([len(str(k).split(".")[-1]) for k in self.param_dict.keys()])
            max_v_len = max([len(v.value) for v in self.param_dict.values()])
            param_list = [f'{str(k).split(".")[-1]:{max_k_len}} ({v.value:{max_v_len}})'
                          for k, v in self.param_dict.items()]
            code += f'\n{indent_lvl1},.'.join(param_list)
            code += f'\n{indent_lvl0}) '

        code += f'{inst_name} ( /* vai-auto-inst */\n{indent_lvl1} .'
        # find the max length of port length
        len_list = [(len(k), len(f'{v["instp"]}{v["slice"]}')) for k, v in self.port_dict.items()]
        max_k_len, max_v_len = tuple(map(max, list(zip(*len_list))))
        # print(f'max_k={max_k_len}, max_v={max_v_len}')
        ports = [f'{k:{max_k_len}} ({v["instp"]+v["slice"]:{max_v_len}}) //{v["type"]}{v["dir"]}'
                 for k, v in self.port_dict.items()]
        code += f'\n{indent_lvl1},.'.join(ports)
        code += f'\n{indent_lvl0}); // end of {inst_name}'

        return code

    def generate_wire_declare(self, indent=0):
        """Generate wire declaration.
        """

        indent_lvl0 = ' ' * indent
        code = f'{indent_lvl0}'

        # find the max length of port width slice
        len_list = [(len(v["instp"]), len(v["slice"])) for v in self.port_dict.values()]
        max_instp_len, max_slice_len = tuple(map(max, list(zip(*len_list))))
        ports = [f'wire {v["slice"]:{max_slice_len}} {v["instp"]:{max_instp_len}};'
                 for v in self.port_dict.values() if v['type'] == 'W']
        code += f'\n{indent_lvl0}'.join(ports)
        return code


    def generate_port_declare(self, indent=0):
        """Generate external port declaration.
        """

        indent_lvl0 = ' ' * indent
        code = f'{indent_lvl0}'

        # find the max length of port width slice
        max_slice_len = max([len(v["slice"]) for v in self.port_dict.values()])
        ports = [(f'{"input" if v["dir"] == "I" else ("output" if v["dir"] == "O" else "inout")} '
                 f'{v["slice"]:{max_slice_len}} {v["instp"]}')
                 for v in self.port_dict.values() if v['type'] == 'P']
        code += f'\n{indent_lvl0},'.join(ports)
        return code


if __name__ == '__main__':
    lines = None
    with open('top.v', 'r') as f:
        lines = f.readlines()
    
    instances = get_instances(('top.v', ), lines)
    pprint.pprint(instances)

    vai = VlogAutoInst(('macros.v', 'led.v'), 'led')
    print(vai.generate_inst('u_led', 2))
    # # update params
    # new_params = {'STEP': '4', 'LEN': "8'hf", 'WIDTH': "4'hc"}
    # new_ports = {'din': 'led_din', 'addr1': 'led_addr1'}
    regexp = (r'^', r'u_LED_')
    vai.update_inst(instances['u_my_led']['param'], instances['u_my_led']['port'], regexp)
    print(vai.generate_inst('u_led', 2))

    vai.reinst()
    vai.update_inst(None, None, regexp)
    print(vai.generate_inst('u_led', 2))

    get_vai_files(lines)
