#!/usr/bin/env python3.9

import matplotlib.pyplot as plt
import pandas as pd
import subprocess
import copy
import re
import time
import argparse
import sys

class Log:
    date=None
    add_lines=0
    del_lines=0
    def reset(self):
        self.date=None
        self.add_lines=0
        self.del_lines=0

    def commit(self, logArray):
        if self.date is not None:
            # print(f'{log.add_lines} {log.del_lines} {log.date}')
            logArray.append( copy.deepcopy(self) )
            self.reset()


def fetch_git_log(workdir):
    logArray = []
    #pattern_space = re.compile('[:space:]+')
    pattern_int = re.compile('^[0-9]+$')
    try:
        proc = subprocess.Popen(['git',
                                 'log', '--numstat',
                                 '--date', 'format:%s'],
                                cwd=workdir,
                                stdout = subprocess.PIPE)

        logArray = []
        log = Log()
        for line in proc.stdout:
            line = line.decode('utf-8')
            line = line.rstrip()

            col=line.split()
            if len(col)==0:
                continue

            if col[0] == "Date:":
                log.reset()
                log.date=int(col[1])

            if len(col)>2 and pattern_int.match(col[0]) and pattern_int.match(col[1]):
                log.add_lines += int(col[0])
                log.del_lines -= int(col[1])

            if col[0] == "commit":
                log.commit(logArray)

        log.commit(logArray)

    except subprocess.CalledProcessError as err:
        print('ERROR:', err.output)

    # Reverse!
    return logArray[::-1]


def create_dataframe_from_logarray(logarray):
    total_line=0
    data=[]
    for e in logarray:
        total_line += e.add_lines + e.del_lines
        # print(f"{e.date}  {e.add_lines} {e.del_lines} {total_line}")
        data.append([e.date, e.add_lines,  e.del_lines, total_line])

    df = pd.DataFrame(data,
                      columns=["date",
                               "add_lines", "del_lines", "total_line"])

    df["ts"] = pd.to_datetime(df["date"].astype(int), unit='s')

    return df


def plot_simple(df):
    fig, ax = plt.subplots(1,1)
    ax.plot(df["ts"], df["total_line"])

    for tick in ax.get_xticklabels():
        tick.set_rotation(15)

    ax.set_ylabel("Lines of source code")
    ax.set_title(args.title)

    ax.grid()

    return fig, ax

def plot_detailed(df):
    fig, ax = plt.subplots(2,1, sharex=True)
    ax[0].plot(df["ts"], df["total_line"])


    ax[0].set_ylabel("Lines of source code")
    ax[0].grid()

    ax[1].vlines(df["ts"], 0, df["add_lines"],
                 color="b", label="Added")
    ax[1].vlines(df["ts"], 0, df["del_lines"],
                 color="r", label="Deleted")

    #ymax=df["add_lines"].max()
    #ymin=df["del_lines"].min()
    ymax=df["add_lines"].quantile(q=.99)
    ymin=df["del_lines"].quantile(q=.01)
    ax[1].set_ylim([ymin,ymax])
    ax[1].grid()
    ax[1].legend()

    for tick in ax[1].get_xticklabels():
        tick.set_rotation(15)

    # ax[1].set_ylabel("Changed lines")

    ax[0].set_title(args.title)

    return fig, ax

# ---------------------------

parser = argparse.ArgumentParser(description='Plot lines of source codes in a git project')

parser.add_argument('workdir', type=str, default=".", nargs='?')
parser.add_argument('--save', type=str, metavar='filename', help="save figure as file")
parser.add_argument('--dump', type=str, metavar='filename',help="dump data into csv file")
parser.add_argument('--restore', type=str, metavar='filename',help="load data from csv file")
parser.add_argument('--simple',  action='store_true', help="plot simple graph")
parser.add_argument('--today',  action='store_true')
parser.add_argument('--title', type=str, help="set title ")

args = parser.parse_args()

df = None
if args.restore:
    df = pd.read_csv(args.restore, index_col=False)
    df["ts"] = pd.to_datetime(df["date"].astype(int), unit='s')
else:
    logarray = fetch_git_log(args.workdir)
    df = create_dataframe_from_logarray(logarray)

if args.dump:
    df.drop(["ts"], axis=1).to_csv(args.dump, index=False)

if df.shape[0] == 0:
    print("No commit exits.")
    sys.exit(0)

if args.today:
    total_line=df.tail(1)["total_line"]
    date=time.time()
    today=pd.to_datetime(date, unit='s')
    df=df.append({'date': date, 'ts': today, 'add_lines':0, 'del_lines':0, 'total_line':total_line}, ignore_index=True)

if args.simple:
    fig, ax  = plot_simple(df)
else:
    fig, ax  = plot_detailed(df)

if args.save:
    plt.savefig(args.save)
else:
    plt.show()
