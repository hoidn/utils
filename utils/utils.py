# Author: O. Hoidn
import numpy as np
import copy
import os
#import dill
import pkg_resources
from time import time
import pdb
import hashlib
import itertools
import random
import operator
from .output import log
from .output import conditional_decorator
from functools import reduce


from io import open
PKG_NAME = __name__.split('.')[0]

# from https://gist.github.com/rossdylan/3287138
# TODO: how about this?:
# def compose(*funcs): return lambda x: reduce(lambda v, f: f(v), reversed(funcs), x)
# TODO: test caching decorators on functions that return None.
from functools import partial
def _composed(f, g, *args, **kwargs):
    return f(g(*args, **kwargs))

def compose(*a):
    try:
        return partial(_composed, a[0], compose(*a[1:]))
    except:
        return a[0]

def conserve_type(func):
    """
    Decorator: for a function whose positional arguments are all either
    lists or np.ndarrays and returns the same number of iterables, convert
    each returned object to the same type (i.e. list or np.ndarray) as the
    corresponding input.
    """
    import collections
    def newfunc(*args, **kwargs):
        def eval_if_iterator(obj):
            if isinstance(obj, collections.Iterator):
                return list(obj)
            else:
                return obj

        def convert(arg, output):
            arg = eval_if_iterator(arg)
            if type(arg) == list:
                return list(output)
            elif type(arg) == np.ndarray:
                return np.array(output)
            elif type(arg) == tuple:
                return tuple(output)
            else:
                return output

        result = list(func(*args, **kwargs))
        converted = list(map(convert, args, result))
        return convert(result, converted)
    return newfunc

def all_isinstance(iterable, obj_type):
    """
    Return True if all elements of iterable are of type obj_type.
    """
    return all(isinstance(r, obj_type) for r in iterable)

def identity(x, **kwargs):
    return x

def square(x, **kwargs):
    return np.sum(x)**2

def usum(x, **kwargs):
    return np.sum(x)


def random_float():
    from datetime import datetime
    random.seed(datetime.now())
    return random.uniform(0., 1.)

#def resample(x, y, smoothing = 0, relative_sample_interval = 1.):
#    from scipy.interpolate import interp1d
#    from scipy.ndimage.filters import gaussian_filter
#    intermediate_sample_relative_density = 2.
#    def regrid(x, y, gridratio):
#        x, y = x[np.argsort(x)], y[np.argsort(x)]
#        interpolated = interp1d(x, y, fill_value = 0.)
#        dx = np.min(np.abs(np.diff(x)))/gridratio
#        npoints = int((interpolated.x[-1] - interpolated.x[0]) / dx)
#        regridded_x = np.linspace(interpolated.x[0], interpolated.x[1], num = npoints)
#        regridded_y = interpolated(regridded_x)
#        return regridded_x, regridded_y, regridded_x[1] - regridded_x[0]
#    # sort the arrays
#    finex, finey, dx = regrid(x, y, intermediate_sample_relative_density)
#    finey = gaussian_filter(oversampled_y, smoothing / dx)
#
#    finalx, finaly, _ = regrid(finex, finey, relative_sample_interval / intermediate_sample_relative_density

def angles_to_q(angles, e0):
    hbarc = 1973. # in eV * Angstrom
    def _angle_to_q(angle):
        return 2 * e0 * np.sin(np.deg2rad(angle)/2)/hbarc
    return list(map(_angle_to_q, angles))

def dict_leaf_mean(d):
    """
    Return the average value of the values of the 'leaf' values
    in a (nested) dictionary.
    """    
    def _gather(d):
        leaf_list = []
        for k, v in list(d.items()):
            if isinstance(v, dict):
                leaf_list += _gather(v)
            else:
                leaf_list += [v]
        return leaf_list
    leaf_values = _gather(d)
    return reduce(lambda x, y: x + y, leaf_values) / len(leaf_values)


def merge_lists(*args):
    """
    Merge a nested structure of tuples and/or lists and/or
    np.ndarrays by horizontal stacking along the innermost
    possible axis.
    """
    assert len(args) > 0
    if len(args) == 1:
        return args[0]
    a, b = args[:2]
    #assert np.shape(a) == np.shape(b)
    assert type(a) == type(b)
    l_type = type(a) # list, tuple or ndarray
    assert l_type in [list, tuple, np.ndarray]
    if l_type in [list, tuple]:
        op = operator.add
        l_make = l_type
    else:
        op = lambda x, y: np.hstack((x, y))
        l_make = np.array
    if len(np.shape(a)) == 1:
        return reduce(op, args)
    else:
        return l_make(list(map(merge_lists, *args)))
        

def merge_dicts(*args):
    final = {}
    for d in args:
        final.update(d)
    return final

def prune_dict(dict1, dict2):
    """
    Return a new dict based on dict1 with all keys not found in dict2 removed
    recursively; i.e. this function is intended to operate on two trees of nested
    dictionaries with similar structure.
    """
    if not isinstance(dict1, dict) or not isinstance(dict2, dict):
        return dict1
    return dict((k, prune_dict(dict1[k], dict2[k]))
        for k in dict1
        if k in dict2)
def dicts_take_intersecting_keys(d1, d2):
    return prune_dict(d1, d2), prune_dict(d2, d1)

def roundrobin(*iterables):
    """Merges iterables in an interleaved fashion.

    roundrobin('ABC', 'D', 'EF') --> A D E B F C"""
    # Recipe credited to George Sakkis
    if not iterables:
        raise ValueError("Arguments must be 1 or more iterables")
    nexts = itertools.cycle(iter(it).__next__ for it in iterables)
    stopcount = 0
    while 1:
        try:
            for i, next in enumerate(nexts):
                yield next()
                stopcount = 0
        except StopIteration:
            stopcount += 1
            if stopcount >= len(iterables):
                break

def mpi_rank():
    from mpi4py import MPI
    comm = MPI.COMM_WORLD
    return comm.Get_rank()

def mpimap(func, lst):
    """
    Map func over list in parallel over all MPI cores.

    The full result is returned in each rank.
    """
    from mpi4py import MPI
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()
    results = \
        [func(elt)
        for n, elt in enumerate(lst)
        if n % size == rank]
    results = comm.allgather(results)
    if results:
        results = list(roundrobin(*results))
    return results

def parallelmap(func, lst, nodes = None):
    """
    Return the averaged signal and background (based on blank frames) over the given runs using
    multiprocessing (as opposed to MPI).
    """
    from pathos.multiprocessing import ProcessingPool
    from pathos import multiprocessing
    if not nodes:
        nodes = multiprocessing.cpu_count() - 2
    pool = ProcessingPool(nodes=nodes)
    try:
        return pool.map(func, lst)
    except KeyboardInterrupt:
        pool.terminate()
        pool.join()


def ifplot(func):
    """
    Decorator that causes a function to execute only if config.noplot is False
    and the MPI core rank is 0.
    """
    def inner(*args, **kwargs):
        import config
        if config.noplot:
            log( "PLOTTING DISABLED, EXITING." )
        else:
            return func(*args, **kwargs)
    return inner
    

# playback fails for this function
#@playback.db_insert
def save_image(save_path, imarr, fmt = 'tiff'):
    """
    Save a 2d array to file as an image.
    """
    if not isinstance(imarr, np.ndarray):
        imarr = np.array(imarr)
    from PIL import Image
    from scipy import misc
    import matplotlib.image as image
    dirname = os.path.dirname(save_path)
    if dirname and (not os.path.exists(dirname)):
        os.system('mkdir -p ' + os.path.dirname(save_path))
    np.save(save_path + '.npy', imarr)
    if imarr.dtype == 'uint16':
        imarr = imarr.astype('float')
    im = Image.fromarray(imarr)
    im.save(save_path + '.tif')
    image.imsave(save_path + '.png', imarr)

#@playback.db_insert
def save_data(x, y, save_path, mongo_key = 'data', init_dict = {}):
    import database
    dirname = os.path.dirname(save_path)
    if dirname and (not os.path.exists(dirname)):
        os.system('mkdir -p ' + os.path.dirname(save_path))
    np.savetxt(save_path, [x, y])
    #database.mongo_add(mongo_key, [list(x), list(y)])
    # TODO: collection should be referred to by a string
    to_insert_local = merge_dicts(dict((k, v) for k, v in list(database.to_insert.items())), init_dict)
    to_insert_local[mongo_key] = [list(x), list(y)]
    database.mongo_replace_atomic(database.collections_lookup['session_cache'], to_insert_local)



#def load_data(search_dict = {}, mongo_key = 'data'):
#    """
#    
#    import database
#    return database.collections_lookup['session_cache'].find(search_dict)

def flatten_dict(d):
    """
    Given a nested dictionary whose values at the "bottom" are numeric, create
    a 2d array where the rows are of the format:
        k1, k2, k3, value
    This particular row would correspond to the following subset of d:
        {k1: {k2: {k3: v}}}
    Stated another way, this function traverses the dictionary from node to leaf
    once for every single leaf.

    The dict must be "rectangular" (i.e. all leafs are at the same depth)
    """
    def walkdict(d, parents = []):
        if not isinstance(d, dict):
            for p in parents:
                yield p
            yield d
        else:
            for k in d:
                for elt in walkdict(d[k], parents + [k]):
                    yield elt
    def dict_depth(d, depth=0):
        if not isinstance(d, dict) or not d:
            return depth
        return max(dict_depth(v, depth+1) for k, v in list(d.items()))
    depth = dict_depth(d) + 1
    flat_arr = np.fromiter(walkdict(d), float)
    try:
        return np.reshape(flat_arr, (len(flat_arr) / depth, depth))
    except ValueError as e:
        raise ValueError("Dictionary of incorrect format given to flatten_dict: " + e)

def save_0d_event_data(save_path, event_data_dict, **kwargs):
    """
    Save an event data dictionary to file in the following column format:
        run number, event number, value
    """
    dirname = os.path.dirname(save_path)
    if dirname and (not os.path.exists(dirname)):
        os.system('mkdir -p ' + os.path.dirname(save_path))
    np.savetxt(save_path, flatten_dict(event_data_dict), **kwargs)


def save_image_and_show(save_path, imarr, title = 'Image', rmin = None, rmax = None, show_plot = True):
    """
    Save a 2d array to file as an image and then display it.
    """
    ave, rms = imarr.mean(), imarr.std()
    if not rmin:
        rmin = ave - rms
    if not rmax:
        rmax = ave + 5 * rms
    @ifplot
    def show():
        log( "rmin", rmin)
        log( "rmax", rmax)
        import pyimgalgos.GlobalGraphics as gg
        gg.plotImageLarge(imarr, amp_range=(rmin, rmax), title = title, origin = 'lower')
        if show_plot:
            gg.show()
    save_image(save_path, imarr)
    show()


#@playback.db_insert
@ifplot
def global_save_and_show(save_path):
    """
    Save current matplotlib plot to file and then show it.
    """
    import config
    if config.plotting_mode == 'notebook':
        from .mpl_plotly  import plt
    else:
        import matplotlib.pyplot as plt
    dirname = os.path.dirname(save_path)
    name = os.path.basename(save_path)
    extsplit = name.split('.')
    if len(extsplit) <= 1:
        ext = ''
    else:
        ext = '.' + extsplit[-1]
    name = name[:255 - (len(ext) + 1)]
    save_path = dirname + '/' + name + ext
    if dirname and (not os.path.exists(dirname)):
        os.system('mkdir -p ' + os.path.dirname(save_path))
    plt.savefig(save_path)
    plt.show()

def get_default_args(func):
    """
    returns a dictionary of arg_name:default_values for the input function
    """
    import inspect
    args, varargs, keywords, defaults = inspect.getargspec(func)
    if defaults:
        return dict(list(zip(args[-len(defaults):], defaults)))
    else:
        return {}

def resource_f(fpath, pkg_name = PKG_NAME):
    from io import StringIO
    return StringIO(pkg_resources.resource_string(pkg_name, fpath))

def resource_path(fpath, pkg_name = PKG_NAME):
    return pkg_resources.resource_filename(pkg_name, fpath)

def extrap1d(x, y, **kwargs):
    from scipy.interpolate import interp1d
    interpolator = interp1d(x, y, **kwargs)
    xs = interpolator.x
    ys = interpolator.y

    def pointwise(x):
        if x < xs[0]:
            return ys[0]
        elif x > xs[-1]:
            return ys[-1]
        else:
            return interpolator(x)

    def ufunclike(xs):
        try:
            iter(xs)
        except TypeError:
            xs = np.array([xs])
        return np.array(list(map(pointwise, np.array(xs))))

    return ufunclike

# TODO: improve efficiency for large objects (such as numpy arrays)
def hash_obj(obj):
    """
    return a hash of any python object
    """
    from meta.decompiler import decompile_func
    import ast
    def obj_digest(to_digest):
        return hashlib.sha1(dill.dumps(to_digest)).hexdigest()

    def iter_digest(to_digest):
        return obj_digest(reduce(operator.add, list(map(hash_obj, to_digest))))

    if (not isinstance(obj, np.ndarray)) and hasattr(obj, '__iter__') and (len(obj) > 1):
        if isinstance(obj, dict):
            return iter_digest(iter(list(obj.items())))
        else:
            return iter_digest(obj)
    else:
        # Functions receive special treatment, such that code changes alter
        # the hash value
        if hasattr(obj, '__call__'):
            try:
                return obj_digest(ast.dump(decompile_func(obj)))
            # This covers an exception that happens in meta.decompiler under
            # certain situations. TODO: replace this workaround with something
            # better.
            except IndexError:
                return obj_digest(dill.dumps(obj))
        else:
            return obj_digest(obj)

def hashable_dict(d):
    """
    try to make a dict convertible into a frozen set by 
    replacing any values that aren't hashable but support the 
    python buffer protocol by their sha1 hashes
    """
    #TODO: replace type check by check for object's bufferability
    for k, v in list(d.items()):
        # for some reason ndarray.__hash__ is defined but is None! very strange
        #if (not isinstance(v, collections.Hashable)) or (not v.__hash__):
        if isinstance(v, np.ndarray):
            d[k] = hash_obj(v)
    return d

def memoize_condition(cache_valid):
    """
    Memoization operator that invalidates cache whenever cache_valid()
    evaluates to False.
    """
    cache = {}
    def decorator(f):
        def new_func(*args):
            if (args in cache) and cache_valid():
                return cache[args]
            else:
                cache[args] = f(*args)
                return cache[args]
        return new_func
    return decorator

def memoize_timeout(timeout = 10):
    state = {}
    def cache_valid():
        if 'last' not in state:
            state['last'] = time()
        curtime = time()
        if curtime - state['last'] > timeout:
            state['last'] = curtime
            return False
        else:
            return True
    return memoize_condition(cache_valid)

def memoize(timeout = None):
    """
    Memoization decorator with an optional timout parameter.
    """
    cache = {}
    # sad hack to get around python's scoping behavior
    cache2 = {}
    def get_timestamp():
        return cache2[0]
    def set_timestamp():
        cache2[0] = time()
    def decorator(f):
        def new_func(*args, **kwargs):
            key = dill.dumps([args, kwargs])
            if key in cache:
                if (not timeout) or (time() - get_timestamp() < timeout):
                    return cache[key]
            if timeout:
                set_timestamp()
            cache[key] = f(*args, **kwargs)
            return cache[key]
        return new_func
    return decorator

def persist_to_file(file_name):
    """
    Decorator for memoizing function calls to disk

    Inputs:
        file_name: File name prefix for the cache file(s)
    """
    # Optimization: initialize the cache dict but don't load data from disk
    # until the memoized function is called.
    cache = {}

    # These are the hoops we need to jump through because python doesn't allow
    # assigning to variables in enclosing scope:
    state = {'loaded': False, 'cache_changed': False}
    def check_cache_loaded():
        return state['loaded']
    def flag_cache_loaded():
        state['loaded'] = True
    def check_cache_changed():
        return state['cache_changed']
    def flag_cache_changed():
        return state['cache_changed']

    def dump():
        os.system('mkdir -p ' + os.path.dirname(file_name))
        with open(file_name, 'wb') as f:
            dill.dump(cache, f)

    def decorator(func):
        #check if function is a closure and if so construct a dict of its bindings
        def compute(key):
            if not check_cache_loaded():
                try:
                    with open(file_name, 'rb') as f:
                        to_load = dill.load(f)
                        for k, v in list(to_load.items()):
                            cache[k] = v
                except (IOError, ValueError):
                    #print "no cache file found"
                    pass
                flag_cache_loaded()
            if not key in list(cache.keys()):
                cache[key] = func(*dill.loads(key[0]), **dict((k, v) for k, v in key[1]))
                if not check_cache_changed():
                    # write cache to file at interpreter exit if it has been
                    # altered
                    import atexit
                    atexit.register(dump)
                    flag_cache_changed()

        if func.__code__.co_freevars:
            closure_dict = hashable_dict(dict(list(zip(func.__code__.co_freevars, (c.cell_contents for c in func.__closure__)))))
        else:
            closure_dict = {}

        def new_func(*args, **kwargs):
            # if the "flush" kwarg is passed, recompute regardless of whether
            # the result is cached
            if "flush" in list(kwargs.keys()):
                kwargs.pop("flush", None)
                key = (dill.dumps(args), frozenset(list(kwargs.items())), frozenset(list(closure_dict.items())))
                compute(key)
            key = (dill.dumps(args), frozenset(list(kwargs.items())), frozenset(list(closure_dict.items())))
            if key not in cache:
                compute(key)
            return cache[key]
        return new_func

    return decorator

def eager_persist_to_file(file_name, excluded = None, args_only = False):
    """
    Decorator for memoizing function calls to disk.
    Differs from persist_to_file in that the cache file is accessed and updated
    at every call, and that each call is cached in a separate file. This allows
    parallelization without problems of concurrency of the memoization cache,
    provided that the decorated function is expensive enough that the
    additional read/write operations have a negligible impact on performance.

    Inputs:
        file_name: File name prefix for the cache file(s)
    """
    cache = {}

    def decorator(func):
        #check if function is a closure and if so construct a dict of its bindings
        if func.__code__.co_freevars:
            closure_dict = hashable_dict(dict(list(zip(func.__code__.co_freevars, (c.cell_contents for c in func.__closure__)))))
        else:
            closure_dict = {}

        def gen_key(*args, **kwargs):
            """
            Based on args and kwargs of a function, as well as the 
            closure bindings, generate a cache lookup key
            """
            # union of default bindings in func and the kwarg bindings in new_func
            # TODO: merged_dict: why aren't changes in kwargs reflected in it?
            merged_dict = get_default_args(func)
            if not merged_dict:
                merged_dict = kwargs
            else:
                for k, v in list(merged_dict.items()):
                    if k in kwargs:
                        merged_dict[k] = kwargs[k]
            if excluded:
                for k in list(merged_dict.keys()):
                    if k in excluded:
                        merged_dict.pop(k)
            if args_only:
                key = hash_obj(tuple(map(hash_obj, [args, list(kwargs.items())])))
            else:
                key = hash_obj(tuple(map(hash_obj, [args, merged_dict, func, list(kwargs.items())])))
            #print "key is", key
#            for k, v in kwargs.iteritems():
#(                print k, v)
            return key

        def dump_to_file(d, file_name):
            os.system('mkdir -p ' + os.path.dirname(file_name))
            with open(file_name, 'wb') as f:
                dill.dump(d, f)
            #print "Dumped cache to file"
    
        def compute(*args, **kwargs):
            file_name = kwargs.pop('file_name', None)
            key = gen_key(*args, **kwargs)
            value = func(*args, **kwargs)
            cache[key] = value
            # Write to disk if the cache file doesn't already exist
            if not os.path.isfile(file_name):
                dump_to_file(value, file_name)
            return value

        def new_func(*args, **kwargs):
            # Because we're splitting into multiple files, we can't retrieve the
            # cache until here
            #print "entering ", func.func_name
            if 'load' in list(kwargs.keys()):
                key = kwargs['load']
            else:
                key = gen_key(*args, **kwargs)
            full_name = file_name + key
            if key not in cache:
                try:
                    try:
                        with open(full_name, 'rb') as f:
                            cache[key] = dill.load(f)
                    except EOFError:
                        os.remove(full_name)
                        log( "corrupt cache file deleted")
                        raise ValueError("Corrupt file")
                    #print "cache found"
                except (IOError, ValueError, FileNotFoundError):
                    #print "no cache found; computing"
                    compute(*args, file_name = full_name, **kwargs)
            # if the "flush" kwarg is passed, recompute regardless of whether
            # the result is cached
            if "flush" in list(kwargs.keys()):
                kwargs.pop("flush", None)
                # TODO: refactor
                compute(*args, file_name = full_name, **kwargs)
            #print "returning from ", func.func_name
            return cache[key]

        return new_func

    return decorator

@eager_persist_to_file("cache/xrd.combine_masks/")
def combine_masks(imarray, mask_paths, verbose = False, transpose = False):
    """
    Takes a list of paths to .npy mask files and returns a numpy array
    consisting of those masks ANDed together.
    """
    # Initialize the mask based on zero values in imarray.
    import numpy.ma as ma
    base_mask = ma.make_mask(np.ones(np.shape(imarray)))
    base_mask[imarray == 0.] = False
    if not mask_paths:
        log( "No additional masks provided")
        return base_mask
    else:
        # Data arrays must be transposed here for the same reason that they
        # are in data_extractor.
        if transpose:
            masks = [np.load(path).T for path in mask_paths]
        else:
            masks = [np.load(path) for path in mask_paths]
        log( "Applying mask(s): ", mask_paths)
        return base_mask & reduce(lambda x, y: x & y, masks)

def df_to_dict(df):
    """
    convert pandas DataFrame of two columns to a dict
    """
    d = {}
    for r in df.iterrows():
        d[r[0]] =  r[1][0]
    return d

