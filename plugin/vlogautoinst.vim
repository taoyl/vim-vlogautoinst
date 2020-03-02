" VlogAutoInst: Verilog auto instantiation
" Maintainer:   Yuliang Tao (nerotao@foxmail.com)
" Date:         Fri, 28 Feb 2020 16:50:49
" Version:      0.1
"
" Description:
"
" License:
" Copyright (c) 2020, Yuliang Tao
" All rights reserved.
"


" function! VlogAutoInst {{{
function! VaiDefault(...)
python3 << EOP
import os
import sys
import vim
# The following line can be removed if vlogautoinst is installed.
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append('/Users/taoyl/Github/myrepos/vim-vlogautoinst')
import vlogai.vai as vai
import vlogai.vimutils as vimutils


# parse command arguments
args = vai.parse_args(vim.eval("a:000"))
if args.inst is None and not args.declare:
    vim.command(vimutils.echo(('Usgae Error: at least one of -i/--inst and -d/--declare must be '
                               'specified')))
elif (args.reset or args.regexp) and args.inst is None:
    vim.command(vimutils.echo(('Usage Error: --reset and -r/--regexp must be specified along with'
                               ' -i/--inst')))
else:
    # parse current vlog file
    cur_buf = vim.current.buffer
    instances = vai.get_instances((cur_buf.name,), cur_buf)
    print(instances)

    # delcare wire and external ports for all valid instances
    if args.declare:
        auto_dec_info = vai.find_declares_ln(cur_buf)
        ap_begin_ln, ap_end_ln, ap_indent = auto_dec_info.get('ap', (0, 0, 0))
        aw_begin_ln, aw_end_ln, aw_indent = auto_dec_info.get('aw', (0, 0, 0)) 
        print(f'aw={aw_begin_ln}, {aw_end_ln}')
        if ap_begin_ln == 0 and aw_begin_ln == 0:
            vim.command(vimutils.echo('No auto declaration directives found'))
        else:
            code_info = vai.generate_declares(instances, pindent=ap_indent, windent=aw_indent)
            port_dec_code, pn, wire_dec_code, wn = code_info
            old_ap_num = 0
            if port_dec_code is not None:
                # delete the old port declares and insert new ones
                vimutils.delete(cur_buf, ap_begin_ln, ap_end_ln)
                old_ap_num = ap_end_ln - 1 - ap_begin_ln
                vimutils.insert(cur_buf, port_dec_code, ap_begin_ln)
            if wire_dec_code is not None:
                # delete the old wire declares and insert new ones
                # update wire declare line number
                aw_begin_ln += (pn - old_ap_num)
                aw_end_ln += (pn - old_ap_num)
                vimutils.delete(cur_buf, aw_begin_ln, aw_end_ln)
                vimutils.insert(cur_buf, wire_dec_code, aw_begin_ln)
            if wire_dec_code is None and port_dec_code is None:
                vim.command(vimutils.echo('No instports found'))
    # instantiate vlog module
    else:
        flist = vai.get_vai_files(cur_buf)
        print(flist)
        target_inst = instances.get(args.inst, None)
        print(target_inst)
        new_inst = vai.VlogAutoInst(flist, target_inst['mod'])
        # update params and instports
        regexp = args.regexp if args.regexp else None
        new_inst.update_inst(target_inst['param'], target_inst['port'], regexp)
        inst_code = new_inst.generate_inst(args.inst, target_inst['indent'])
        vimutils.delete(cur_buf, target_inst['begin_ln'], target_inst['end_ln'])
        vimutils.insert(cur_buf, inst_code, target_inst['begin_ln'])

EOP
endfunction
" }}}

" VAI command usage:
" VAI [-i|--inst inst_name] [-r|--regexp m_pat s_pat] [--reset] [-d|--declare]'
command! -nargs=+ -buffer VAI call VaiDefault(<f-args>)

" vim:set sw=2 sts=2 fdm=marker: