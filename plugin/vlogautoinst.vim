" VlogAutoInst: Verilog auto instantiation
" Maintainer:   Yuliang Tao (nerotao@foxmail.com)
" Date:         Fri, 28 Feb 2020 16:50:49
" Version:      1.0
"
" Description:
" A vim plugin for verilog auto instantiation.
" 
" License:
" Copyright (c) 2020, Yuliang Tao
" All rights reserved.
"

" function! VlogAutoInst {{{
function! VaiAutoInst(...)
python3 << EOP
import os
import sys
import vim
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
    if instances is None:
        vim.command(vimutils.echo('Syntax errors found in current file', severity='Error'))
    elif not instances:
        vim.command(vimutils.echo('No vai-auto instances found in current file'))
    else:
        # delcare wire and external ports for all valid instances
        if args.declare:
            auto_dec_info = vai.find_declares_ln(cur_buf)
            ap_begin_ln, ap_end_ln, ap_indent = auto_dec_info.get('ap', (0, 0, 0))
            aw_begin_ln, aw_end_ln, aw_indent = auto_dec_info.get('aw', (0, 0, 0)) 
            if ap_begin_ln == 0 and aw_begin_ln == 0:
                vim.command(vimutils.echo('No auto declaration directives found'))
            else:
                # If auto-port declaration is before all other ports, no precomma
                min_ln = list(instances.values())[0]['parent_port_ln'][0]
                precomma = False if (min_ln > ap_begin_ln) else True
                code_info = vai.generate_declares(instances, pindent=ap_indent, windent=aw_indent,
                                                precomma=precomma)
                port_dec_code, pn, wire_dec_code, wn = code_info
                ln_change = 0
                if port_dec_code is not None:
                    # delete the old port declares and insert new ones
                    vimutils.delete(cur_buf, ap_begin_ln, ap_end_ln)
                    vimutils.insert(cur_buf, port_dec_code, ap_begin_ln)
                    # line number changes
                    ln_change = pn - (ap_end_ln - 1 - ap_begin_ln)
                elif not args.keep and ap_begin_ln + 1 != ap_end_ln:
                    # clear the old port declares
                    vimutils.delete(cur_buf, ap_begin_ln + 1, ap_end_ln - 1)
                    # line number changes
                    ln_change = 0 - (ap_end_ln - 1 - ap_begin_ln)
                    
                # update wire declare line number
                aw_begin_ln += ln_change
                aw_end_ln += ln_change
                if wire_dec_code is not None:
                    # delete the old wire declares and insert new ones
                    vimutils.delete(cur_buf, aw_begin_ln, aw_end_ln)
                    vimutils.insert(cur_buf, wire_dec_code, aw_begin_ln)
                elif not args.keep and aw_begin_ln + 1 != aw_end_ln:
                    # clear the old wire declares
                    vimutils.delete(cur_buf, aw_begin_ln + 1, aw_end_ln - 1)
                    
                if wire_dec_code is None and port_dec_code is None:
                    vim.command(vimutils.echo('No instports found'))
        # instantiate vlog module
        else:
            flist = vai.get_vai_files(cur_buf)
            target_inst = instances.get(args.inst, None)
            if target_inst is None:
                vim.command(vimutils.echo(f'Instance {args.inst} not found'))
            else:
                new_inst = vai.VlogAutoInst(flist, target_inst['mod'])
                if new_inst.error == 1:
                    vim.command(vimutils.echo((f'Definition of module {target_inst["mod"]} not '
                                            'found in vlog files')))
                elif new_inst.error == 2:
                    vim.command(vimutils.echo(f'Syntax errors found in vlog files'))
                else:
                    # update params and instports
                    regexp = args.regexp if args.regexp else None
                    params = None if args.reset else target_inst['param']
                    ports = None if args.reset else target_inst['port']
                    new_inst.update(param_dict=params, port_dict=ports, port_regexp=regexp)
                    inst_code = new_inst.generate_code(args.inst, target_inst['indent'])
                    vimutils.delete(cur_buf, target_inst['begin_ln'], target_inst['end_ln'])
                    vimutils.insert(cur_buf, inst_code, target_inst['begin_ln'])

EOP
endfunction
" }}}

" VAI command usage:
" VAI [-i|--inst inst_name] [-r|--regexp m_pat s_pat] [--reset] [-d|--declare]'
" Must save the current buffer before calling VaiAutoInst, otherwise vim.current.buffer is not valid.
command! -nargs=+ -buffer VAI write | call VaiAutoInst(<f-args>)

" vim:set sw=2 sts=2 fdm=marker:
