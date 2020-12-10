# Copyright 2020 The Cirq Developers
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from unittest import mock
import pytest

import sympy

import cirq
import cirq.ionq as ionq


@pytest.mark.parametrize(
    'target,expected_results', [('qpu', [[0], [1], [1], [1]]), ('simulator', [[1], [0], [1], [1]])]
)
def test_service_run(target, expected_results):
    service = ionq.Service(remote_host='http://example.com', api_key='key')
    mock_client = mock.MagicMock()
    mock_client.create_job.return_value = {
        'id': 'job_id',
        'status': 'ready',
    }
    mock_client.get_job.return_value = {
        'id': 'job_id',
        'status': 'completed',
        'target': target,
        'metadata': {'shots': '4', 'measurement0': f'a{chr(31)}0'},
        'qubits': '1',
        'data': {'histogram': {'0': '0.25', '1': '0.75'}},
        'status': 'completed',
    }
    service._client = mock_client

    a = sympy.Symbol('a')
    q = cirq.LineQubit(0)
    circuit = cirq.Circuit((cirq.X ** a)(q), cirq.measure(q, key='a'))
    params = cirq.ParamResolver({'a': 0.5})
    result = service.run(
        circuit=circuit,
        repetitions=4,
        target=target,
        name='bacon',
        param_resolver=params,
        seed=2,
    )
    assert result == cirq.Result(params=params, measurements={'a': expected_results})

    create_job_kwargs = mock_client.create_job.call_args[1]
    # Serialization induces a float, so we don't validate full circuit.
    assert create_job_kwargs['serialized_program'].body['qubits'] == 1
    assert create_job_kwargs['serialized_program'].metadata == {'measurement0': f'a{chr(31)}0'}
    assert create_job_kwargs['repetitions'] == 4
    assert create_job_kwargs['target'] == target
    assert create_job_kwargs['name'] == 'bacon'


def test_service_get_job():
    service = ionq.Service(remote_host='http://example.com', api_key='key')
    mock_client = mock.MagicMock()
    job_dict = {'id': 'job_id', 'status': 'ready'}
    mock_client.get_job.return_value = job_dict
    service._client = mock_client

    job = service.get_job('job_id')
    assert job.job_id() == 'job_id'
    mock_client.get_job.assert_called_with(job_id='job_id')


def test_service_create_job():
    service = ionq.Service(remote_host='http://example.com', api_key='key')
    mock_client = mock.MagicMock()
    mock_client.create_job.return_value = {'id': 'job_id', 'status': 'ready'}
    mock_client.get_job.return_value = {'id': 'job_id', 'status': 'completed'}
    service._client = mock_client

    circuit = cirq.Circuit(cirq.X(cirq.LineQubit(0)))
    job = service.create_job(circuit=circuit, repetitions=100, target='qpu', name='bacon')
    assert job.status() == 'completed'
    create_job_kwargs = mock_client.create_job.call_args[1]
    # Serialization induces a float, so we don't validate full circuit.
    assert create_job_kwargs['serialized_program'].body['qubits'] == 1
    assert create_job_kwargs['repetitions'] == 100
    assert create_job_kwargs['target'] == 'qpu'
    assert create_job_kwargs['name'] == 'bacon'


def test_service_get_current_calibration():
    service = ionq.Service(remote_host='http://example.com', api_key='key')
    mock_client = mock.MagicMock()
    calibration_dict = {'qubits': 11}
    mock_client.get_current_calibration.return_value = calibration_dict
    service._client = mock_client

    cal = service.get_current_calibration()
    assert cal.num_qubits() == 11
    mock_client.get_current_calibration.assert_called_once()