# vim-vlogautoinst
A vim plugin for verilog auto instantiation

# Installation
## Requirements
  This vim plugin requires vlogai python package, please install vlogai before using this plugin.
```
pip install git+https://github.com/taoyl/vlogai.git
```

  Installation can be done with plugin managers, e.g. vim-plug
  (https://github.com/junegunn/vim-plug), Vundle.vim
  (https://github.com/VundleVim/Vundle.vim), pathogen.vim 
  (https://github.com/tpope/vim-pathogen) or if you're using Vim >= 8.0, you
  can use the built-in plugin manager.

## Install with vim-plug
  Add the following to your .vimrc and run ```PlugInstall```, for vim-plug: 
```
    Plug 'taoyl/vim-vlogautoinst'
```

## Install with VundleVim
  Add the following to your .vimrc and run ```PluginInstall```, for VundleVim: 
```
    Plugin 'taoyl/vim-vlogautoinst'
```
## Install with pathogen
  With pathogen, you need to run the following in your terminal:
```
    cd ~/.vim/bundle && \
    git clone https://github.com/taoyl/vim-vlogautoinst.git
```
## Install with Vim 8 package feature (not tried by myself)
  With the package feature of Vim 8, it is a bit more involved. Run the
  following in your terminal
```
    mkdir -p ~/.vim/pack/git-plugins/start
    cd ~/.vim/pack/git-plugins/start
    git clone https://github.com/taoyl/vim-vlogautoinst.git
```
  Then, add this to your ~/.vimrc:
```
    packloadall
    silent! helptags ALL
```

# Usage
You can check the usgae of VAI command using ```:VAI -h``` or ```:help vlogautoinst.txt```
