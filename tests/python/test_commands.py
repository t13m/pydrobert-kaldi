# Copyright 2016 Sean Robertson

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Pytests for `pydrobert.kaldi.test_commands`"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging

import numpy as np
import pydrobert.kaldi.io as kaldi_io
import pytest

from pydrobert.kaldi import command_line
from pydrobert.kaldi.logging import kaldi_lvl_to_logging_lvl
from six.moves import cPickle as pickle


def test_can_parse_equals():
    parser = command_line.KaldiParser()
    parser.add_argument('--foo', type=int, default=1)
    assert parser.parse_args([]).foo == 1
    assert parser.parse_args(['--foo', '2']).foo == 2
    assert parser.parse_args(['--foo=2']).foo == 2


def test_config(temp_file_1_name):
    with open(temp_file_1_name, mode='w') as conf_file:
        conf_file.write('--foo 2\n')
        conf_file.write('#--foo 3\n')
        conf_file.write('#--foo 4\n')
    parser = command_line.KaldiParser()
    parser.add_argument('--foo', type=int, default=1)
    assert parser.parse_args([]).foo == 1
    assert parser.parse_args(['--config', temp_file_1_name]).foo == 2
    assert parser.parse_args(
        ['--foo', '4', '--config', temp_file_1_name]).foo == 4


def test_verbosity():
    logger = logging.getLogger('this_should_not_be_used')
    parser = command_line.KaldiParser(logger=logger)
    assert logger.level == kaldi_lvl_to_logging_lvl(0)
    parser.parse_args(['-v', '-1'])
    assert logger.level == kaldi_lvl_to_logging_lvl(-1)
    parser.parse_args(['-v', '9'])
    assert logger.level == kaldi_lvl_to_logging_lvl(9)


@pytest.mark.parametrize('values', [
    [
        np.array([1, 2, 3], dtype=np.float32),
        np.array([4], dtype=np.float32),
        np.array([], dtype=np.float32),
    ],
    [
        np.random.random((100, 20)),
    ],
    ['foo', 'bar', 'baz'],
    [
        ('foo', 'bar'),
        ('baz',),
    ],
    [],
])
def test_write_pickle_to_table(values, temp_file_1_name, temp_file_2_name):
    if len(values):
        kaldi_dtype = kaldi_io.util.infer_kaldi_data_type(values[0]).value
    else:
        kaldi_dtype = 'bm'
    with open(temp_file_1_name, 'wb') as pickle_file:
        for num, value in enumerate(values):
            pickle.dump((str(num), value), pickle_file)
    ret_code = command_line.write_pickle_to_table(
        [temp_file_1_name, 'ark:' + temp_file_2_name, '-o', kaldi_dtype])
    assert ret_code == 0
    kaldi_reader = kaldi_io.open('ark:' + temp_file_2_name, kaldi_dtype, 'r')
    num_entries = 0
    for key, value in kaldi_reader.items():
        num_entries = int(key) + 1
        try:
            values[num_entries - 1].dtype
            assert np.allclose(value, values[num_entries - 1])
        except AttributeError:
            assert value == values[num_entries - 1]
    assert num_entries == len(values)


@pytest.mark.parametrize('values', [
    [
        np.array([1, 2, 3], dtype=np.float32),
        np.array([4], dtype=np.float32),
        np.array([], dtype=np.float32),
    ],
    [
        np.random.random((100, 20)),
    ],
    ['foo', 'bar', 'baz'],
    [
        ('foo', 'bar'),
        ('baz',),
    ],
    [],
])
def test_write_table_to_pickle(values, temp_file_1_name, temp_file_2_name):
    if len(values):
        kaldi_dtype = kaldi_io.util.infer_kaldi_data_type(values[0]).value
    else:
        kaldi_dtype = 'bm'
    with kaldi_io.open('ark:' + temp_file_1_name, kaldi_dtype, 'w') as writer:
        for num, value in enumerate(values):
            writer.write(str(num), value)
    ret_code = command_line.write_table_to_pickle(
        ['ark:' + temp_file_1_name, temp_file_2_name, '-i', kaldi_dtype])
    assert ret_code == 0
    num_entries = 0
    pickle_file = open(temp_file_2_name, 'rb')
    num_entries = 0
    try:
        while True:
            key, value = pickle.load(pickle_file)
            num_entries = int(key) + 1
            try:
                values[num_entries - 1].dtype
                assert np.allclose(value, values[num_entries - 1])
            except AttributeError:
                assert value == values[num_entries - 1]
    except EOFError:
        pass
    assert num_entries == len(values)
