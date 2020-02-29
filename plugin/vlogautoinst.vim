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
python3 << EOF
import sys
import vim
# The following line can be removed if vlogautoinst is installed.
sys.path.append('/Users/taoyl/Github/myrepos/vim-vlogautoinst')
import pyvai.vai as vai

cur_buf = vim.current.buffer
flist = vai.get_vai_files(cur_buf)
print(f'args={vim.eval("a:000")}')
print(flist)
instances = vai.get_instances((cur_buf.name,), cur_buf)
print(instances)

EOF
endfunction
" }}}

command! -nargs=+ -buffer VAI call VaiDefault(<f-args>)

" vim:set sw=2 sts=2 fdm=marker: