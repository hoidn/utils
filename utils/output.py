"""
Functions for controlling logging and other output.
"""



import os
import logging
from io import open


# Control redirection of stdout:
suppress_root_print = False
stdout_to_file = False

logfile_path = 'log.txt'

logging.basicConfig(filename = logfile_path, level = logging.DEBUG)

class conditional_decorator(object):
    """
    From http://stackoverflow.com/questions/10724854/how-to-do-a-conditional-decorator-in-python-2-6
    """
    def __init__(self, dec, condition):
        self.decorator = dec
        self.condition = condition

    def __call__(self, func):
        if not self.condition:
            # Return the function unchanged, not decorated.
            return func
        return self.decorator(func)

def isroot():
    """
    Return true if the MPI core rank is 0 and false otherwise.
    """
    if 'OMPI_COMM_WORLD_RANK' not in ' '.join(list(os.environ.keys())):
        return True
    else:
        rank = int(os.environ['OMPI_COMM_WORLD_RANK'])
        return (rank == 0)
    
def ifroot(func):
    """
    Decorator that causes the decorated function to execute only if
    the MPI core rank is 0.
    """
    def inner(*args, **kwargs):
        if isroot():
            return func(*args, **kwargs)
    return inner

def stdout_to_file(path = None):
    """
    Decorator that causes stdout to be redirected to a text file during the
    modified function's invocation.
    """
    if path is None:
        path = 'mecana.log'
    def decorator(func):
        import sys
        def new_func(*args, **kwargs):
            stdout = sys.stdout
            sys.stdout = open(path, 'w')
            result = func(*args, **kwargs)
            sys.stdout.close()
            sys.stdout = stdout
            return result
        return new_func
    return decorator

@conditional_decorator(ifroot, suppress_root_print)
def log(*args):
    def newargs():
        if stdout_to_file:
            return ('PID ', os.getpid(), ': ') + args
        else:
            return args
    logging.info(' '.join(map(str, args)))
    #print(*newargs())
