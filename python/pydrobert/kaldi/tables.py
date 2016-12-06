"""Interface for Kaldi's readers and writers

The README file has a good example of standard usage; using `open`
should be enough for most. However, :class:`KaldiIO` subclasses can be
initialized directly for greater granularity.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import abc

from enum import Enum # need enum34 for python 2.7

import numpy

from future.utils import implements_iterator
from six import with_metaclass

from . import _internal as _i

__author__ = "Sean Robertson"
__email__ = "sdrobert@cs.toronto.edu"
__license__ = "Apache 2.0"
__copyright__ = "Copyright 2016 Sean Robertson"

class KaldiDataType(Enum):
    """Indicates the data type an archive stores. Values for `kaldi_dtype`

    Whenever `kaldi_dtype` is an argument to a method or function in
    `tables`, one of these attributes can be passed directly via
    ``KaldiDataType.XXX`, or by its :class:`str` form, e.g. ``'bv'``.

    Attributes:
        +----------------+------------+-------------+-----------------+
        | Attribute Name | String Rep | Numpy shape | Precision       |
        +================+============+=============+=================+
        | `BaseVector`   | ``'bv'``   | (X,)        | Kaldi default   |
        +----------------+------------+-------------+-----------------+
        | `DoubleVector` | ``'dv'``   | (X,)        | 64-bit          |
        +----------------+------------+-------------+-----------------+
        | `FloatVector`  | ``'fv'``   | (X,)        | 32-bit          |
        +----------------+------------+-------------+-----------------+
        | `BaseMatrix`   | ``'bm'``   | (X,X)       | Kaldi default   |
        +----------------+------------+-------------+-----------------+
        | `DoubleMatrix` | ``'dm'``   | (X,X)       | 64-bit          |
        +----------------+------------+-------------+-----------------+
        | `FloatMatrix`  | ``'fm'``   | (X,X)       | 32-bit          |
        +----------------+------------+-------------+-----------------+
        | `WaveMatrix`   | ``'wm'``   | (X,X)       | Kaldi default   |
        +----------------+------------+-------------+-----------------+
        | `Token`        | ``'t'``    | N/A         | N/A             |
        +----------------+------------+-------------+-----------------+
        | `TokenVector`  | ``'tv'``   | N/A         | N/A             |
        +----------------+------------+-------------+-----------------+
    """
    BaseVector = 'bv'
    DoubleVector = 'dv'
    FloatVector = 'fv'
    BaseMatrix = 'bm'
    DoubleMatrix = 'dm'
    FloatMatrix = 'fm'
    WaveMatrix = 'wm'
    Token = 't'
    TokenVector = 'tv'

    @property
    def is_matrix(self):
        return str(self.value) in ('bm', 'dm', 'fm', 'wm')

    @property
    def is_floating_point(self):
        return str(self.value) in ('bv', 'fv', 'dv', 'bm', 'fm', 'dm', 'wm')

    @property
    def is_double(self):
        '''bool: whether this data type is double precision (64-bit)'''
        if str(self.value) in ('bv', 'bm', 'wm'):
            return _i.kDoubleIsBase
        elif str(self.value) in ('dv', 'dm'):
            return True
        else:
            return False

class KaldiIO(with_metaclass(abc.ABCMeta), object):
    """Base class for interacting with Kaldi scripts/archives

    :class:`KaldiIO` subclasses all contain `open` and `close` methods.
    Additional methods depend on the subclass, but in general have
    either read- or write-like methods, depending on whether they are
    reading or writing the archives. The return type is determined by
    `kaldi_dtype`. `Kaldi I/O Mechanisms`_ describes how Kaldi uses
    extended file names, tables, and such.

    Args:
        xfilename(str,optional): read or write extended filename. If
            both this and `kaldi_dtype` are specified, `open` will be
            called immediately with these and any additional keyword
            arguments.
        kaldi_dtype(:class:`KaldiDataType`,optional): read or write
            extended filename. If both this and `xfilename` are
            specified, `open` will be called immediately with these
            and any additional keyword arguments.

    Raises:
        TypeError: if only one of `xfilename` or `kaldi_dtype` are
            specified.

    Warning:
        It is possible to raise one of Kaldi's runtime errors when using
        these subclasses. You should consult Kaldi's output to stderr to
        figure out what went wrong. Hopefully the error will be wrapped
        in Python's :class:`RuntimeError` rather than causing a
        segfault.

    .. _Kaldi I/O Mechanisms:
        http://kaldi-asr.org/doc2/io.html
    """

    def __init__(self, **kwargs):
        if 'xfilename' in kwargs and 'kaldi_dtype' in kwargs:
            self.open(**kwargs)
        elif 'xfilename' in kwargs:
            raise TypeError('"xfilename" was specified but not "kaldi_dtype"')
        elif 'kaldi_dtype' in kwargs:
            raise TypeError('"kaldi_dtype" was specified but not "xfilename"')

    if _i.kDoubleIsBase:
        _BaseVector = KaldiDataType.DoubleVector
        _BaseMatrix = KaldiDataType.DoubleMatrix
    else:
        _BaseVector = KaldiDataType.FloatVector
        _BaseMatrix = KaldiDataType.FloatMatrix

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_val, trace):
        self.close()

    def __del__(self):
        self.close()

    def open(self, xfilename, kaldi_dtype, **kwargs):
        """Open a Kaldi script or archive

        Args:
            xfilename(str): An extended file name to open. Whether this
                is a `wxfilename` or `rxfilename` depends on the
                subclass. This can be an archive or script file.
            kaldi_dtype(KaldiDataType): What kaldi data type is/will be
                stored. All array-likes written or read are expected to
                be of this type.
            utt2spk(str, optional): Applicable to
                :class:`KaldiRandomAccessTableReader`, setting this
                opens a `RandomAccessTableReaderMapped`_ and with
                `utt2spk_rxfilename` set to this.
            with_keys(bool, optional): Applicable to
                :class:`KaldiSequentialTableReader`, setting this to
                true returns pairs of (key, val) when iterating instead
                of just the value
            wav_with_info(bool, optional): Applicable to readers of
                `kaldi_dtype = WaveMatrix`. If `True`, `WaveInfoMatrix`
                output will be appended to values, making tuples of
                `(val, n_channels, duration_in_secs, sample_rate)`.
            tv_error_on_str(bool, optional): Applicable to
                :class:`KaldiTableWriter` when `kaldi_dtype` is
                `TokenVector`. If True, this raises a `ValueError` when
                the user tries to write a string to file. If False, the
                string will be interpreted as a list of character
                tokens. Defaults to True.

        Raises:
            IOError: If the arhive or script cannot be opened, but does
                not cause a :class:`RuntimeError`.

        ..seealso:: :class:`KaldiDataType`
        .. _`RandomAccessTableReaderMapped`:
            http://kaldi-asr.org/doc2/classkaldi_1_1RandomAccessTableReaderMapped.html
        """
        kaldi_dtype = KaldiDataType(kaldi_dtype)
        if kaldi_dtype == KaldiDataType.BaseVector:
            kaldi_dtype = KaldiIO._BaseVector
        elif kaldi_dtype == KaldiDataType.BaseMatrix:
            kaldi_dtype = KaldiIO._BaseMatrix
        return self._open(xfilename, kaldi_dtype, **kwargs)

    @abc.abstractmethod
    def _open(self, xfilename, dtype, **kwargs):
        pass

    @abc.abstractmethod
    def close(self):
        """Closes the `KaldiIO` object, or does nothing if not opened

        This happens automatically when this object is destroyed.
        """
        pass

@implements_iterator
class KaldiSequentialTableReader(KaldiIO):
    """Read a Kaldi script/archive as an iterable"""

    def __init__(self, **kwargs):
        self._internal = None
        self._with_keys = False
        super(KaldiSequentialTableReader, self).__init__(**kwargs)

    def close(self):
        if self._internal:
            self._internal.Close()
            self._internal = None

    def _open(self, xfilename, kaldi_dtype, with_keys=False, **kwargs):
        if len(kwargs):
            raise TypeError(
                "'{}' is an invalid argument for this function".format(
                    next(iter(kwargs))))
        self._with_keys = with_keys
        cls = None
        if kaldi_dtype == KaldiDataType.DoubleVector:
            cls = _i.SequentialDoubleVectorReader
        elif kaldi_dtype == KaldiDataType.FloatVector:
            cls = _i.SequentialFloatVectorReader
        elif kaldi_dtype == KaldiDataType.DoubleMatrix:
            cls = _i.SequentialDoubleMatrixReader
        elif kaldi_dtype == KaldiDataType.FloatMatrix:
            cls = _i.SequentialFloatMatrixReader
        elif kaldi_dtype == KaldiDataType.WaveMatrix:
            cls = _i.SequentialWaveReader
        elif kaldi_dtype == KaldiDataType.Token:
            cls = _i.SequentialTokenReader
        elif kaldi_dtype == KaldiDataType.TokenVector:
            cls = _i.SequentialTokenVectorReader
        assert cls
        instance = cls()
        if not instance.Open(xfilename):
            raise IOError(
                'Unable to open file "{}" for sequential '
                'read.'.format(xfilename))
        self._internal = instance

    def __iter__(self):
        if not self._internal:
            raise ValueError('I/O operation on a closed file')
        return self

    def __next__(self):
        if not self._internal:
            raise ValueError('I/O operation on a closed file')
        if self._internal.Done():
            raise StopIteration
        ret = self._internal.Value()
        if self._with_keys:
            ret = self._internal.Key(), ret
        self._internal.Next()
        return ret

class KaldiRandomAccessTableReader(KaldiIO):
    """Read a Kaldi archive/script like a dictionary with string keys"""

    def __init__(self, **kwargs):
        self._internal = None
        super(KaldiRandomAccessTableReader, self).__init__(**kwargs)

    def close(self):
        if self._internal:
            self._internal.Close()
            self._internal = None

    def _open(self, xfilename, kaldi_dtype, utt2spk=None, **kwargs):
        if len(kwargs):
            raise TypeError(
                "'{}' is an invalid argument for this function".format(
                    next(iter(kwargs))))
        cls = None
        if kaldi_dtype == KaldiDataType.DoubleVector:
            if utt2spk:
                cls = _i.RandomAccessDoubleVectorReaderMapped
            else:
                cls = _i.RandomAccessDoubleVectorReader
        elif kaldi_dtype == KaldiDataType.FloatVector:
            if utt2spk:
                cls = _i.RandomAccessFloatVectorReaderMapped
            else:
                cls = _i.RandomAccessFloatVectorReader
        elif kaldi_dtype == KaldiDataType.DoubleMatrix:
            if utt2spk:
                cls = _i.RandomAccessDoubleMatrixReaderMapped
            else:
                cls = _i.RandomAccessDoubleMatrixReader
        elif kaldi_dtype == KaldiDataType.FloatMatrix:
            if utt2spk:
                cls = _i.RandomAccessFloatMatrixReaderMapped
            else:
                cls = _i.RandomAccessFloatMatrixReader
        elif kaldi_dtype == KaldiDataType.WaveMatrix:
            cls = _i.RandomAccessWaveReader
        elif kaldi_dtype == KaldiDataType.Token:
            cls = _i.RandomAccessTokenReader
        elif kaldi_dtype == KaldiDataType.TokenVector:
            cls = _i.RandomAccessTokenVectorReader
        assert cls
        instance = cls()
        res = None
        if utt2spk:
            res = instance.Open(xfilename, utt2spk, **kwargs)
        else:
            res = instance.Open(xfilename, **kwargs)
        if not res:
            raise IOError(
                'Unable to open file "{}" for writing.'.format(xfilename))
        self._internal = instance

    def get(self, key, will_raise=False):
        """Get data indexed by key

        Args:
            key(str): Key which data is mapped to in archive
            will_raise(bool optional): Whether to raise a
                :class:`KeyError`. If the key is not found. Defaults to
                ``False``.

        Returns:
            :class:`numpy.ndarray` associated with key if present,
            ``None`` if the key is absent and `will_raise` is set to
            ``False``

        Raises:
            ValueError: If object is closed
            KeyError: If `key` is not present in script/archive and
                `will_raise` is set to ``True``.

        Examples:
            >>> reader.get('foo') # (1)
            >>> reader.get('foo', will_raise=True) # (2)
            >>> reader['foo'] # equivalent to (2)
        """
        if not self._internal:
            raise ValueError('I/O operation on a closed file')
        if not self._internal.HasKey(key):
            if will_raise:
                raise KeyError(key)
            return None
        return self._internal.Value(key)

    def __getitem__(self, key):
        return self.get(key, will_raise=True)

class KaldiTableWriter(KaldiIO):
    """Write to key/data combinations sequentially to a Kaldi script/archive"""

    def __init__(self, **kwargs):
        self._error_on_str = False
        self._internal = None
        super(KaldiTableWriter, self).__init__(**kwargs)

    def close(self):
        if self._internal:
            self._internal.Close()
            self._internal = None

    def _open(self, xfilename, kaldi_dtype, tv_error_on_str=True, **kwargs):
        if len(kwargs):
            raise TypeError(
                "'{}' is an invalid argument for this function".format(
                    next(iter(kwargs))))
        cls = None
        self._error_on_str = False
        if kaldi_dtype == KaldiDataType.DoubleVector:
            cls = _i.DoubleVectorWriter
        elif kaldi_dtype == KaldiDataType.FloatVector:
            cls = _i.FloatVectorWriter
        elif kaldi_dtype == KaldiDataType.DoubleMatrix:
            cls = _i.DoubleMatrixWriter
        elif kaldi_dtype == KaldiDataType.FloatMatrix:
            cls = _i.FloatMatrixWriter
        elif kaldi_dtype == KaldiDataType.WaveMatrix:
            cls = _i.WaveWriter
        elif kaldi_dtype == KaldiDataType.Token:
            cls = _i.TokenWriter
        elif kaldi_dtype == KaldiDataType.TokenVector:
            cls = _i.TokenVectorWriter
            self._error_on_str = tv_error_on_str
        assert cls
        instance = cls()
        if not instance.Open(xfilename, **kwargs):
            raise IOError(
                'Unable to open file "{}" for writing.'.format(xfilename))
        self._internal = instance

    def write(self, key, value):
        """Write key/value pair to script/archive

        Args:
            key(str):
            value(array-like):

        Raises:
            ValueError: Operating on closed file, or `value` cannot be
                cast to the `kaldi_dtype` specified when this object
                was opened
            TypeError: If casting the 1value`, already a
                :class:`numpy.ndarray` to the `kaldi_dtype`

        Warning:
            In the case of a matrix `kaldi_dtype`, Kaldi does not accept
            arrays of shape (0,X) or (X,0), where X > 0. This method
            automatically converts all such input to a matrix of shape
            (0,0).
        """
        if not self._internal:
            raise ValueError('I/O operation on a closed file')
        if self._error_on_str and isinstance(value, str):
            raise TypeError(
                'Writing strings as vectors was disallowed. If desired, '
                'set tv_error_on_str to False on open.'
            )
        self._internal.Write(key, value)

def open(xfilename, kaldi_dtype, mode='r', **kwargs):
    """:class:`KaldiIO` factory method for initializing/opening tables

    Args:
        xfilename(str):
        kaldi_dtype(KaldiDataType):
        utt2spk(str, optional):
        tv_error_on_str(bool, optional):
        with_keys(bool, optional)
        mode(str, optional): One of "r", "r+", and "w", which generate
            a :class:`KaldiSequentialTableReader`,
            a :class:`KaldiRandomAccessTableReader`, and a
            :class:`KaldiTableWriter` respectively.

    Returns:
        A :class:`KaldiIO` subclass, opened

    Raises:
        IOError:

    ..seealso:: :class:`KaldiIO`
    """
    if mode == 'r':
        io_obj = KaldiSequentialTableReader(
            xfilename=xfilename, kaldi_dtype=kaldi_dtype, **kwargs)
    elif mode == 'r+':
        io_obj = KaldiRandomAccessTableReader(
            xfilename=xfilename, kaldi_dtype=kaldi_dtype, **kwargs)
    elif mode in ('w', 'w+'):
        io_obj = KaldiTableWriter(
            xfilename=xfilename, kaldi_dtype=kaldi_dtype, **kwargs)
    else:
        raise ValueError(
            'Invalid Kaldi I/O mode "{}" (should be one of "r","r+","w")'
            ''.format(mode))
    return io_obj
