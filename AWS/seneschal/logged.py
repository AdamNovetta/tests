#!/usr/bin/env python3
import logging
import time
import datetime


# Iteration counter for naming passes / debugging
class counter:
        def __init__(self):
                self.number = 0
                self.total = 0

        def add(self):
                self.number += 1
                self.total += 1

        def reset(self):
                self.number = 0


# logging output class
class log_data:

    # init blank logging-item object with counter
    def __init__(self, program_name, version, enable_logging):
        self.state = "starting"
        self.proc = ''
        self.data = ''
        self.count = counter()
        self.program_name = program_name
        self.version = version
        self.enable_logging = enable_logging

    def starting(self, p):
        self.count.reset()
        self.state = "starting"
        self.proc = p
        print_log(self)

    def process(self, p, s, d=''):
        self.state = s
        self.proc = p
        self.data = d
        self.count.add()
        print_log(self)

    def subroutine(self, p, d=''):
        self.state = "sub"
        self.proc = p
        self.data = d
        self.count.add()
        print_log(self)

    def info(self, s, d):
        self.state = s
        self.data = d
        print_log(self)

    def ending(self, p):
        self.state = "ending"
        self.proc = p
        print_log(self)

    def finished(self):
        self.state = "finished"
        print_log(self)

    # log print output
    def __str__(self):
        output = d = more_data = ''
        logger = logging.getLogger()
        # set below to DEBUG or INFO to see more errors in event log/console
        logger.setLevel(logging.WARNING)

        count = str(self.count.number)
        total = str(self.count.total)
        pn = self.program_name
        v = self.version
        if self.data:
            more_data = str(self.data)

        d = str(datetime.datetime.now())

        ############################
        # Output messaging vars    #
        ############################
        err = " X ERROR X "
        suc = "+ - "
        subr = ">  "
        dash = " - "
        sp = " "
        lb = "\n[ "
        rb = " ]\n"
        pipe = " | "
        header = lb + pn + dash + v + pipe
        tailed = " process @ " + d + rb
        footer = lb + " <!> ____ Processed: "
        counted = " items during "
        footend = " routine _____ <!>" + rb
        ending = lb + "<> ____ Completed! Processed: "
        totaled = " total objects in "
        endend = " run _____ <>" + rb

        #############################
        # outputs. based on 'state' #
        #############################

        if "0" in self.state:
            output = err + self.proc + dash + more_data
        elif "1" in self.state:
            output = suc + self.proc + dash + more_data
        elif "sub" in self.state:
            output = subr + self.proc + sp + more_data
        elif "info" in self.state:
            output = subr + dash + self.data
        elif "starting" in self.state:
            output = header + self.state + sp + self.proc + tailed
        elif "ending" in self.state:
            output = footer + count + counted + self.proc + footend
        elif "finished" in self.state:
            output = ending + total + totaled + pn + endend
        else:
            output = " uknown IO directive to log fucntion via self.state..."

        return(output)


# Check if logging on/off
def print_log(logger_name):
    if logger_name.enable_logging:
        print(logger_name)
