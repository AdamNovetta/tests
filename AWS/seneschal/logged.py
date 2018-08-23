#!/usr/bin/env python3
import json
import boto3
import logging
import time
import datetime

# Set below to False to disable logging output


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

    # create blank logging-item object with counter
    def __init__(self, program_name, version, enable_logging):
        self.state = "starting"
        self.proc = ''
        self.data = ''
        self.count = counter()
        self.program_name = program_name
        self.version = version
        self.enable_logging = enable_logging
        
    def starting(self, process):
        self.count.reset()
        self.state = "starting"
        self.proc = process
        print_log(self)

    def process(self, p, d, s):
        self.state = s
        self.proc = p
        self.data = d
        self.count.add()
        print_log(self)

    def ending(self, process):
        self.state = "ending"
        self.proc = process
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
        ## Output messaging vars  ##
        ############################
        err = " X ERROR X "
        suc = "+ - "
        header = "[ " + pn + " - " + v + " | "
        tailed = " process @ " + d + " ]"
        footer = "[ <!> ____ Processed: "
        counted = " objects during "
        footend = " tasks _____ <!> ]\n"
        ending = "\n[ <O> ____ Completed! Processed : "
        totaled = " total objects in "
        endend = " run _____ <O> ]\n"
        dash = " - "
        sp = " "
        #############################
        #############################

        if "0" in self.state:
            output = err + self.proc + dash + more_data
        if "1" in self.state:
            output = suc + self.proc + dash + more_data
        if "starting" in self.state:
            output =  header + self.state + sp + self.proc + tailed
        if "ending" in self.state:
            output = footer + count + counted + self.proc + footer
        if "finished" in self.state:
            output = ending + total + totaled + pn + endend

        return(output)

# Check if logging on/off
def print_log(logger_name):
    if logger_name.enable_logging:
        print(logger_name)
