#!/usr/bin/python
#written by Andriy P. for IMS
import ConfigParser
import io
import datetime
import re
import sys
import textwrap
import optparse
import os
import os.path

parser = optparse.OptionParser(usage="usage: %prog [options]", version="%prog 0.6")
parser.add_option('--split', dest='split',
                  help='Please create /tmp/block1 /tmp/block2 files and put servers there. 1 server per line.',
                  action='store_true', metavar='/tmp/block1 /tmp/block2', default=False)
parser.add_option('-f', '--force', dest='force', help='bypass all checks', action='store_true', default=False)
parser.add_option('--single', dest='single', help='Single block. No block files will be created.', action='store_true',
                  default=False)
parser.add_option('--test', dest='testfarm', help='Feature for Testfarm building. DEVelopment in progress.',
                  action='store_true', default=False)
parser.add_option('-d', '--distribute', dest='distribute_file',
                  help='specify custom distribute.cfg location. Default location is /usr/local/tools/src/PACSinstall/site-config/AllServers/distribute.cfg',
                  action='store', type="string",
                  default='/usr/local/tools/src/PACSinstall/site-config/AllServers/distribute.cfg', nargs=1)
parser.add_option('-c','--command', help='Show a tupical commads to run', default=False,action='store_true',dest='comhelp')

parser.add_option('--check',dest='check',help='Will check servers count only then exit. Split block config only.',action='store_true', default=False)

opts, args = parser.parse_args()
if len(sys.argv[1:]) == 0:
    parser.print_help()
    exit(-1)

if not (opts.split or opts.single or opts.check):
    print "Split or Single?"
    exit()



distribute_file = opts.distribute_file

if opts.testfarm:
   try: 
      os.path.isfile(distribute_file)
   except IOError:
      distribute_file="/tmp/distribute-testfarm.cfg"
   else: 
      distribute_file=opts.distribute_file
   print distribute_file

if not os.path.isfile(distribute_file):
    print "{0} file does not exists.".format(distribute_file)
    exit()

_screenrc = textwrap.dedent("""
    defscrollback 20000
    vbell off
    zombie kr
    logfile /tmp/screenlog.%H
    hardstatus alwayslastline "%{b kw}%H %{r}%1` %{w}| %{g}%c %{w}| %{y}%d.%m.%Y %{w}| %{g}%l %{w}| %{-b kw}%u %-Lw%{= rW}%50> %n%f %t %{-}%+Lw%<"
    termcapinfo xterm* 'is=\E[r\E[m\E[2J\E[H\E[?7h\E[?1;4;6l'
    bindkey -k k8 prev # F8 
    bindkey -k k9 next # F9 
    """
                            )

_tmuxconfig = textwrap.dedent("""
    bind r source-file ~/.tmux.conf \; display "Reloaded!"  # Reload with ctrl-r
    set -g prefix C-a         # prefix from ctrl-b to ctrl-a
    unbind C-b                # allow ctrl-b for other things
    set -sg escape-time 1     # quicker responses
    bind C-a send-prefix      # Pass on ctrl-a for other apps
    set -g base-index 1        # Numbering of windows
    setw -g pane-base-index 1  # Numbering of Panes
    bind \ split-window -h    # Split panes horizontal
    bind - split-window -v    # Split panes vertically
    bind h select-pane -L     # Switch to Pane Left
    bind j select-pane -D     # Switch to Pane Down
    bind k select-pane -U     # Switch to Pane Up
    bind l select-pane -R     # Switch to Pane Right
    bind -r C-h select-window -t :-  # Quick Pane Selection
    bind -r C-l select-window -t :+  # Quick Pane Selection
    bind -r H resize-pane -L 5       # Switch to Pane Left
    bind -r J resize-pane -D 5       # Switch to Pane Down
    bind -r K resize-pane -U 5       # Switch to Pane Up
    bind -r L resize-pane -R 5       # Switch to Pane Right
    #setw -g monitor-activity on      # Activity Alerts
    set -g visual-activity on
    set -g status-fg white           # Status line Colors
    set -g status-bg black
    setw -g window-status-fg cyan    # Window list color
    setw -g window-status-bg default
    setw -g window-status-attr dim
    setw -g window-status-current-fg white     # Active Window Color
    setw -g window-status-current-bg red
    setw -g window-status-current-attr bright
    set -g pane-border-fg green      # Pane colors
    set -g pane-border-bg black
    set -g pane-active-border-fg white
    set -g pane-active-border-bg yellow
    set -g message-fg white          # Command/Message Line.
    set -g message-bg black
    set -g message-attr bright
    set -g status-left-length 40     # Status Line, left side
    set -g status-left "#[fg=white]Session: #S #[fg=yellow]#I #[fg=cyan]#P"
    set -g status-right "-------"
    set -g status-interval 60        # frequency of status line updates
    set -g status-justify centre     # center window list
    set-window-option -g xterm-keys on
    setw -g mode-keys vi             # vi keys to move
    unbind v                         # Open panes in same directory as tmux-panes script
    unbind n
    bind-key A      command-prompt 'rename-window %%'
    #bind-key -n F7 previous-window
    #bind-key -n F8 next-window
    bind -n S-Left  previous-window
    bind -n S-Right next-window
    unbind Up                        # Maximizing and Minimizing...
    bind Up new-window -d -n tmp \; swap-pane -s tmp.1 \; select-window -t tmp
    unbind Down
    bind Down last-window \; swap-pane -s tmp.1 \; kill-window -t tmp
    bind P pipe-pane -o "cat >>~/#W.log" \; display "Toggled logging to ~/#W.log"
    set -g set-remain-on-exit on
    bind R respawnw
    """
                              )


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def check_block_files(s):
    if os.path.isfile(s) and os.access(s, os.R_OK):
        print "{0} file exists and is readable".format(s)
    else:
        print "Either file is missing or is not readable"


def key_func(s):
    return [int(x) if x.isdigit() else x for x in re.findall(r'\D+|\d+', s)]


def getServerWeight(key):
    myhost = os.uname()[1]
    mod = re.search(".*mod\d.*", key)
    mst = re.search(".*mst\d.*|.*db\d.*|.*database\d.*", key)
    depot_gw = re.search(".*depot\d.*|.*gw\d.*|.*arch\d.*|.*cache\d.*|.*rig\d.*|.*depot.\d.*|.*rpt\d.*|.*awf\d.*", key)
    if myhost == key:
        weight = "-20"
        print "Locahost will be in window 1: {0}".format(key)
    elif mst:
        weight = "-10"
    elif depot_gw:
        weight = "-5"
    elif mod:
        weight = "0"
    else:
        weight = "0"
    return weight


def show_help(block):
    if block is 'split':
      print "tmux list-windows -t Block1|cut -d: -f1|xargs -I{} tmux send-keys -t Block1:{} \"ls -l \" Enter "
      print "tmux list-windows -t Block2|cut -d: -f1|xargs -I{} tmux send-keys -t Block2:{} \"ls -l \" Enter "
      print "You can switch between sessions in tmux with Ctrl-a+s"
    if block is 'single':
      print "tmux list-windows -t FPU0|cut -d: -f1|xargs -I{} tmux send-keys -t FPU0:{} \"ls -l \" Enter "
    exit()

def getServerWeightArray(my_array):
    servers = {}
    for key in my_array:
        weight = getServerWeight(key)
        servers.update({key: weight})

    return sorted(servers.items(), key=lambda x: (float(x[1]), key_func(x[0])))


def checkServersCount(block1, block2):
    global distribute_file
    servers_in_total = block1 + block2
    with open(distribute_file) as f:
        sample_config = f.read()
        config = ConfigParser.RawConfigParser()
        config.readfp(io.BytesIO(sample_config))
        if servers_in_total != len(config.items('ServerNumberMap')):
            print "Servers count mismach. You have {0} servers in block files and {1} in distribute.cfg".format(
                servers_in_total, len(config.items('ServerNumberMap')))
            exit(-1)
        else:
            print "Servers count is fine. You have {0} servers in total".format(len(config.items('ServerNumberMap')))


def checkServersNaming(block1_list, block2_list):
    global distribute_file
    with open(distribute_file) as f:
        servers_distribute = []
        split_list = []
        split_list1 = []
        split_list2 = []
        sample_config = f.read()
        config = ConfigParser.RawConfigParser()
        config.readfp(io.BytesIO(sample_config))
        for key, val in config.items('ServerNumberMap'):
            servers_distribute.append(key.split('.')[0])
        for key, val in block1_list:
            split_list.append(key.split('.')[0])
            split_list1.append(key.split('.')[0])
        for key, val in block2_list:
            split_list.append(key.split('.')[0])
            split_list2.append(key.split('.')[0])
        if len(set(servers_distribute).symmetric_difference(split_list)) > 0:
            print "Servers names in block files not much with distribute"
            print "Check these host names:"
            print '\n'.join(set(servers_distribute).symmetric_difference(split_list))
            exit(-1)
        elif len(set(split_list2).intersection(split_list1)) > 0:
            print "You have same servers in both blocks"
            print "Check these host names:"
            print '\n'.join(set(split_list1).symmetric_difference(split_list2))
            exit(-1)
        else:
            print "Servers names are fine"


def createDistributeBlocks(split1_list, split2_list):
    distribute_block_header = "[Blocks]"
    block1_list = []
    block2_list = []
    for key, val in split1_list:
        block1_list.append(key.split('.')[0])
    for key, val in split2_list:
        block2_list.append(key.split('.')[0])
    f = open("/tmp/distribute-blocks.cfg", 'w+')
    print >> f, distribute_block_header
    print >> f, "1 = {0}".format(','.join(map(str, block1_list)))
    print >> f, "2 = {0}".format(','.join(map(str, block2_list)))


def GetFullList():
    servers = {}
    global distribute_file
    with open(distribute_file) as f:
        sample_config = f.read()
        config = ConfigParser.RawConfigParser()
        config.readfp(io.BytesIO(sample_config))
    for key, val in config.items('ServerNumberMap'):
        weight = getServerWeight(key)
        servers.update({key: weight})
    return sorted(servers.items(), key=lambda x: (float(x[1]), key_func(x[0])))


def testfarmPrep():
    global distribute_file
    with open(distribute_file) as f:
        servers_distribute = []
        sample_config = f.read()
        config = ConfigParser.RawConfigParser()
        config.readfp(io.BytesIO(sample_config))
        for key, val in config.items('ServerNumberMap'):
            servers_distribute.append(key.split(' ')[0])
        client_code = config.get('ClientInfo', 'clientCode')
        print client_code
        test_servers = []
    with open("/etc/hosts") as f2:
        for line in f2:
            if len(line.strip()) > 0:
                servername = (line.lstrip().rstrip("\n\r").split(' ')[1])
                test_servers.append(servername)
    test_farm_servers_list = set(servers_distribute).intersection(test_servers)
    print bcolors.OKBLUE + "TESTFARM files building. All checks should be bypassed" + bcolors.ENDC
    print bcolors.OKBLUE + "TESTFARM servers list are:" + bcolors.ENDC
    print '\n'.join(test_farm_servers_list)
    return servers_distribute


def get_blocks(block_file):
    split_list = []
    with open(block_file, 'r') as f:
        for line in f:
            if len(line.strip()) > 0:
                split_servername = (line.lstrip().rstrip("\n\r").split(' ')[0])
                split_list.append(split_servername)
    return split_list


if opts.check:
    print bcolors.WARNING + "Processing split block servers checks" + bcolors.ENDC
    block1_file = "/tmp/block1"
    block2_file = "/tmp/block2"
    check_block_files(block1_file)
    check_block_files(block2_file)
    split1_list_1d = get_blocks(block1_file)
    split2_list_1d = get_blocks(block2_file)
    split1_list = getServerWeightArray(split1_list_1d)
    split2_list = getServerWeightArray(split2_list_1d)
    print "Block 1 has {0} servers".format(len(split1_list))
    print "Block 2 has {0} servers".format(len(split2_list))
    checkServersCount(len(split1_list), len(split2_list))
    checkServersNaming(split1_list, split2_list)
    exit()

if opts.comhelp:
   if opts.split:
    show_help('split')
   elif opts.single:
    show_help('single')
   exit()

today = datetime.date.today().strftime("%Y%m%d")
print bcolors.WARNING + "Please , install tmux manually on this host." + bcolors.ENDC

if opts.split:
    print bcolors.WARNING + "Processing split block" + bcolors.ENDC
    block1_file = "/tmp/block1"
    block2_file = "/tmp/block2"
    check_block_files(block1_file)
    check_block_files(block2_file)
    split1_list_1d = get_blocks(block1_file)
    split2_list_1d = get_blocks(block2_file)
    if opts.testfarm:
        servers_distribute = testfarmPrep()
        split1_list_1d = set(servers_distribute).intersection(split1_list_1d)
        split2_list_1d = set(servers_distribute).intersection(split2_list_1d)

    split1_list = getServerWeightArray(split1_list_1d)
    split2_list = getServerWeightArray(split2_list_1d)
    print "Block 1 has {0} servers".format(len(split1_list))
    print "Block 2 has {0} servers".format(len(split2_list))

    if not opts.force:
        checkServersCount(len(split1_list), len(split2_list))
        checkServersNaming(split1_list, split2_list)
    createDistributeBlocks(split1_list, split2_list)

elif opts.single:
    print bcolors.WARNING + "Processing single block" + bcolors.ENDC

tmuxsh = open("/tmp/startME.sh", 'w+')
screen_config = open("/home/admin/screenrc", 'w+')
tmux_config = open("/home/admin/.tmux.conf", 'w+')
print >> tmuxsh, "#/bin/sh"
print >> tmuxsh, "function tmux_connect() {"
if opts.single:
    print >> tmuxsh, "  tmux new-window -k -t FPU0:$3 -n $1  \"rsync /home/admin/screenrc $2:/home/admin/screenrc ; ssh $2 -t screen -d -R FPU0 -c /home/admin/screenrc \" "
if opts.split:
    print >> tmuxsh, "  tmux new-window -k -t Block$4:$3 -n $1  \"rsync /home/admin/screenrc $2:/home/admin/screenrc ; ssh $2 -t screen -d -R FPU0 -c /home/admin/screenrc \" "

print >> tmuxsh, "}"
if opts.split:
    print >> tmuxsh, "tmux start-server"
if opts.single:
    print >> tmuxsh, "tmux new-session -s FPU0 -n main -d"
if opts.split:
    print >> tmuxsh, "tmux new-session -s Block1 -n main -d"
    print >> tmuxsh, "tmux new-session -s Block2 -n main -d"

screen_counter_block1 = 0
screen_counter_block2 = 0

if opts.single:
    global_list = GetFullList()
    split1_list = global_list

for key, val in split1_list:
    screen_counter_block1 = screen_counter_block1 + 1
    print >> tmuxsh, "tmux_connect {0} {1} {2} 1".format(key.split(".")[0], key, screen_counter_block1)

if opts.split:
    for key, val in split2_list:
        screen_counter_block2 = screen_counter_block2 + 1
        print >> tmuxsh, "tmux_connect {0} {1} {2} 2".format(key.split(".")[0], key, screen_counter_block2)

if opts.single:
    print >> tmuxsh, "tmux a -t FPU0"
if opts.split:
    print >> tmuxsh, "tmux a -t Block1"

print "to run something in all your screens you could use:"
if opts.single:
    naming = "FPU0"
    print "tmux list-windows -t FPU0|cut -d: -f1|xargs -I{} tmux send-keys -t FPU0:{} \"ls -l \" Enter "
if opts.split:
    naming = "Block1"
    print "tmux list-windows -t Block1|cut -d: -f1|xargs -I{} tmux send-keys -t Block1:{} \"ls -l \" Enter "
    print "tmux list-windows -t Block2|cut -d: -f1|xargs -I{} tmux send-keys -t Block2:{} \"ls -l \" Enter "
    print "You can switch between sessions in tmux with Ctrl-a+s"

print "or"
print "for i in `seq 1 {0}`; do tmux send-keys -t {1}:$i \"ls -l\" Enter; done ".format(screen_counter_block1, naming)
print "for i in `seq 1 {0}`; do tmux send-keys -t {1}:$i \"sudo su -\" Enter; done ".format(screen_counter_block1,
                                                                                            naming)
print "for i in `seq 1 {0}`; do tmux send-keys -t {1}:$i \'if [ $(lsb_release -rs | cut -f1 -d.) -lt 7 ]; then /usr/sbin/depstart -va --upgrade ; /usr/sbin/depstart --upgrade ; fi\' Enter; done ".format(
    screen_counter_block1, naming)

if opts.split:
    print "for i in `seq 1 {0}`; do tmux send-keys -t {1}:$i \"ls -l\" Enter; done ".format(screen_counter_block2,
                                                                                            naming)
    print bcolors.WARNING + "Please be noticed that you have 2 active tmux sessions named Block1 and Block2" + bcolors.ENDC

print "please open another ssh session and run these commands not from tmux session."

print "start your TMUX session(s) with:"
print "sh /tmp/startME.sh"
print >> tmux_config, (_tmuxconfig)
print >> screen_config, (_screenrc)
