#!/usr/bin/python3

import logging

class OrthogonalFlagsMap:
    '''
    This is a mapping helper for various flags-to-strings facilities
    (Harp warnings, Harp flags, ...) encoded as a i.e. a bitwise field
    of *several* items. You can iterate through the warnings to reach
    all of them:
    ```
       >>> warn = OrthogonalFlagsMap(HarpWarnings, 0x441)
       >>> [ warn.text(w) for w in warn ]
       [ 'Sync rate is zero', 'Input rate is too high', 'Time span is too small' ]
       >>> warn.INPT_RATE_ZERO
       True
       >>> warn.INPT_RATE_TOO_HIGH
       False
    ```
    '''
    
    def __init__(self, flagsMap, code=None):
        '''
        Initializes the mapper. Parameters:
          - `code`: This is a bitwise field of flags that this instance represents.
          - `flagsMap`: This is a dictionary which maps single string keys to
            `(flagMask, flagDescription)` tuples. The string key part
            is a non-changeable string that describes the flags for all eternity,
            and which the user (or other program layers) can use to access the flag.
            `flagDescription` is a human-readable string which can change, e.g.
            by translation or a more precise specification, and `flagMask` is a bit
            mask that indicates whether the flag is set or not.
        '''
        self.flagsMap = flagsMap
        
        if not isinstance (flagsMap, dict):
            t = type(flagsMap)
            raise RuntimeError(f'Flags map needs to be a dictionary, received'+
                               f' {t}: {flagsMap}')

        if len(flagsMap) == 0:
            logging.debug(f'Flags map is empty: f{flagsMap}')
        else:
            first = next(iter(flagsMap))
            if not isinstance(flagsMap[first], tuple) or \
               2 != len(flagsMap[first]):
                raise RuntimeError(f'Flags map value needs to be a (key, description)'+
                                   f' tuple; got {flagsMap[first]} instead')
            
        if code is not None:
            self.recode(code)
    
    def recode(self, code):
        '''
        Resets the code to `code` and returns a reference to self.
        This is to update the active/inactive flags list to the
        ones encoded in `code` without altering the identity of the
        object.
        '''
        self.code = code
        return self

    def __str__(self):
        return str([f for f in self.keys()])

    def __repr__(self):
        return self.__str__()

    def __getattr__(self, key):
        return (self.code & self.flagsMap[key][0]) != 0

    def __iter__(self):
        ''' Iterate through all warnings encoded in `self.code`. '''
        for k,v in self.flagsMap.items():
            if (v[0] & self.code) != 0:
                yield k

    def keys(self):
        '''
        Mimic a bit of a `dict`-like interface: return all the HHLIB API
        warning keys that are encoded in `self.code`.
        '''
        for k in self:
            yield k

    def items(self):
        '''
        Mimic a bit more a `dict`-like interface: return all the HHLIB API
        warning keys that are encoded in `self.code`.
        '''
        for k,v in self.flagsMap.items():
            if (v[0] & self.code):
                yield (k, v[1])
    
    def __getitem__(self, flag):
        ''' Another way of reading a flag '''
        return self.__getattr__(flag)

    def text(self, flag):
        '''
        Returns the description text.
        '''
        return self.flagsMap.get(flag, None)[1]

    def mask(self, flag):
        '''
        Returns the numerical mask value.
        '''
        return self.flagsMap.get(flag, None)[0]

    def __len__(self):
        return len([i for i in self.items()])

#
# Flag map names must match the data type reported by PHAROS!
# The first round of keys can be chosen freely, but the number
# relates to the number of parameters reported by Pharos.
#


OPST = {
    'COM':   (0x80, "Communication error"),
    'CAL':   (0x40, "Calibration error"),
    'ATUNE': (0x20, "Autotune done and not active"),
    'NRDG':  (0x10, "New sensor reading"),
    'RAMP1': (0x08, "Loop1 ramp completed"),
    'RAMP2': (0x04, "Loop2 ramp completed"),
    'OVLD':  (0x02, "Sensor overload"),
    'ALARM': (0x01, "Input is in alarm state"),
}

OPSTE = {
    'COM':    (0x80, 'Processor communication error'),
    'CAL':    (0x40, 'Calibration error'),
    'ATUNE':  (0x20, 'Autotune completed'),
    'NRDG':   (0x10, 'New sensor reading'),
    'RAMP1':  (0x08, 'Loop 1 ramp done'),
    'RAMP2':  (0x04, 'Loop 2 ramp done'),
    'OVLD':   (0x02, 'Sensor overload'),
    'ARLARM': (0x01, 'Sensor alarm') 
}

OPSTR = {
    'COM':   (0x80, "Communication error"),
    'CAL':   (0x40, "Calibration error"),
    'ATUNE': (0x20, "Autotune done and not active"),
    'NRDG':  (0x10, "New sensor reading"),
    'RAMP1': (0x08, "Loop1 ramp completed"),
    'RAMP2': (0x04, "Loop2 ramp completed"),
    'OVLD':  (0x02, "Sensor overload"),
    'ALARM': (0x01, "Input is in alarm state"),
}

RAMPST = {
    0: "Not ramping",
    1: "Setpoint is ramping",
}

HTRST = {
    0: "No error",
    1: "Heater open load",
    2: "Heater short",
}

RDGST = {
    'INV':    (0x01, "Invalid sensor reading"),
    'UNDRGE': (0x04, "Temperature underrange"),
    'OVRGE':  (0x10, "Temperature overrange"),
    'ZERO':   (0x20, "Sensor units zero"),
    'UOVRGE': (0x30, "Sensor units overrange")
}

RELAYST = {
    0: "Off",
    1: "On",
}

#TUNEST

def code2obj(code, codemap):
    ''' Translates a numerical status code into a python iterable object.

    Args:
        code: the numerical code

        codemap: a translation map, either for orthogonal flas, compatible with
          what `OrthogonalFlagsMap` requires, or as a simple exclusive flags map,
          where the codemap key is a code, and the value is a string.

    Returns:
        If `key` is an `OrthogonalFlagsMap`-compatible dictionary, an
        initialized `OrthogonalFlagsMap` object is returned.
    
        If instead `key` is a code enum-style dictionary, the corresponding
        code name (string) is returned, wrapped in a tuple.
    '''

    first = next(iter(codemap.items()))
    
    if not isinstance(first[1], tuple):
        return (codemap[code],)

    return OrthogonalFlagsMap(codemap, code)

