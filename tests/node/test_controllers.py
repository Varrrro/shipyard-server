import unittest
import base64

import hug

from typing import List
from unittest import mock

from bson.objectid import ObjectId

from shipyard.errors import NotFound, NotFeasible, MissingDevices, AlreadyPresent
from shipyard.node import controllers
from shipyard.node.model import Node


test_nodes = Node.Schema().load([
    {
        '_id': str(ObjectId()),
        'name': 'Test1',
        'ip': '1.1.1.1',
        'ssh_user': 'Test1',
        'cpu_cores': 4
    },
    {
        '_id': str(ObjectId()),
        'name': 'Test2',
        'ip': '2.2.2.2',
        'ssh_user': 'Test2',
        'cpu_cores': 1
    }
], many=True)


class MockService():

    @staticmethod
    def get_all() -> List[Node]:
        return test_nodes

    @staticmethod
    def get_by_id(node_id: str) -> Node:
        for node in test_nodes:
            if ObjectId(node_id) == node._id:
                return node

        raise NotFound

    @staticmethod
    def get_by_name(node_name: str) -> Node:
        for node in test_nodes:
            if node_name == node.name:
                return node

        raise NotFound

    @staticmethod
    def create(new_node: Node, ssh_user: str, ssh_pass: str) -> str:
        for node in test_nodes:
            if new_node.name == node.name:
                raise AlreadyPresent

        return str(ObjectId())

    @staticmethod
    def update(node_id: str, new_values: dict) -> Node:
        for node in test_nodes:
            if ObjectId(node_id) == node._id:
                return node

        raise NotFound

    @staticmethod
    def delete(node_id: str) -> Node:
        for node in test_nodes:
            if ObjectId(node_id) == node._id:
                return node

        raise NotFound

    @staticmethod
    def add_task(node_id: str, task_id: str) -> Node:
        for node in test_nodes:
            if ObjectId(node_id) == node._id:
                if task_id == 'NotFeasible':
                    raise NotFeasible

                if task_id == 'MissingDevices':
                    raise MissingDevices

                return test_nodes[0]

        raise NotFound

    @staticmethod
    def remove_task(node_id: str, task_id: str) -> Node:
        for node in test_nodes:
            if ObjectId(node_id) == node._id:
                return node

        raise NotFound


@mock.patch('shipyard.node.controllers.NodeService', MockService)
class TestControllers(unittest.TestCase):

    def test_get_node_list(self):
        response = hug.test.call('GET', controllers, '')
        self.assertEqual(response.status, hug.HTTP_OK)
        self.assertIsNotNone(response.data)
        self.assertEqual(len(response.data), 2)

        response = hug.test.call('GET', controllers, '', params={
            'name': test_nodes[0].name
        })
        self.assertEqual(response.status, hug.HTTP_OK)
        self.assertIsNotNone(response.data)

        response = hug.test.call('GET', controllers, '', params={
            'name': 'Error'
        })
        self.assertEqual(response.status, hug.HTTP_NOT_FOUND)
        self.assertIsNotNone(response.data)

    def test_post_node(self):
        response = hug.test.call(
            'POST',
            controllers,
            '',
            body={
                'name': 'Test3',
                'ip': '3.3.3.3',
                'cpu_cores': 1
            },
            headers={
                'AUTHORIZATION': f'Basic {base64.b64encode(b"test:test").decode()}'
            }
        )
        self.assertEqual(response.status, hug.HTTP_OK)
        self.assertIsNotNone(response.data)
        self.assertIsInstance(response.data['_id'], str)

        response = hug.test.call(
            'POST',
            controllers,
            '',
            body={
                'name': 'Test3',
                'ip': '3.3.3.3'
            },
            headers={
                'AUTHORIZATION': f'Basic {base64.b64encode(b"test:test").decode()}'
            }
        )
        self.assertEqual(response.status, hug.HTTP_BAD_REQUEST)
        self.assertIsNotNone(response.data)

        response = hug.test.call(
            'POST',
            controllers,
            '',
            body=Node.Schema(exclude=['_id']).dump(test_nodes[0]),
            headers={
                'AUTHORIZATION': f'Basic {base64.b64encode(b"test:test").decode()}'
            }
        )
        self.assertEqual(response.status, hug.HTTP_CONFLICT)
        self.assertIsNotNone(response.data)
        self.assertIsInstance(response.data['error'], str)

    def test_get_node(self):
        response = hug.test.call(
            'GET', controllers, f'{str(test_nodes[0]._id)}')
        self.assertEqual(response.status, hug.HTTP_OK)
        self.assertIsNotNone(response.data)

        response = hug.test.call('GET', controllers, f'{ObjectId()}')
        self.assertEqual(response.status, hug.HTTP_NOT_FOUND)
        self.assertIsNotNone(response.data)
        self.assertIsInstance(response.data['error'], str)

        response = hug.test.call('GET', controllers, 'error')
        self.assertEqual(response.status, hug.HTTP_BAD_REQUEST)
        self.assertIsNotNone(response.data)
        self.assertIsInstance(response.data['error'], str)

    def test_put_node(self):
        response = hug.test.call('PUT',
                                 controllers,
                                 f'{test_nodes[0]._id}',
                                 body={'name': 'Updated'})
        self.assertEqual(response.status, hug.HTTP_OK)
        self.assertIsNotNone(response.data)

        response = hug.test.call('PUT',
                                 controllers,
                                 'error',
                                 body={})
        self.assertEqual(response.status, hug.HTTP_BAD_REQUEST)
        self.assertIsNotNone(response.data)
        self.assertIsInstance(response.data['error'], str)

        response = hug.test.call('PUT',
                                 controllers,
                                 f'{ObjectId()}',
                                 body={})
        self.assertEqual(response.status, hug.HTTP_NOT_FOUND)
        self.assertIsNotNone(response.data)
        self.assertIsInstance(response.data['error'], str)

    def test_delete_node(self):
        response = hug.test.call(
            'DELETE', controllers, f'{str(test_nodes[0]._id)}')
        self.assertEqual(response.status, hug.HTTP_OK)
        self.assertIsNotNone(response.data)

        response = hug.test.call('DELETE', controllers, f'{ObjectId()}')
        self.assertEqual(response.status, hug.HTTP_NOT_FOUND)
        self.assertIsNotNone(response.data)
        self.assertIsInstance(response.data['error'], str)

        response = hug.test.call('DELETE', controllers, 'error')
        self.assertEqual(response.status, hug.HTTP_BAD_REQUEST)
        self.assertIsNotNone(response.data)
        self.assertIsInstance(response.data['error'], str)

    def test_post_node_tasks(self):
        response = hug.test.call('POST', controllers, f'{test_nodes[0]._id}/tasks', params={
            'task_id': 'Test'
        })
        self.assertEqual(response.status, hug.HTTP_OK)
        self.assertIsNotNone(response.data)

        response = hug.test.call('POST', controllers, f'{ObjectId()}/tasks', params={
            'task_id': 'Test'
        })
        self.assertEqual(response.status, hug.HTTP_NOT_FOUND)
        self.assertIsNotNone(response.data)
        self.assertIsInstance(response.data['error'], str)

        response = hug.test.call(
            'POST', controllers, f'{test_nodes[0]._id}/tasks')
        self.assertEqual(response.status, hug.HTTP_BAD_REQUEST)
        self.assertIsNotNone(response.data)
        self.assertIsInstance(response.data['error'], str)

        response = hug.test.call('POST', controllers, f'error/tasks', params={
            'task_id': 'Test'
        })
        self.assertEqual(response.status, hug.HTTP_BAD_REQUEST)
        self.assertIsNotNone(response.data)
        self.assertIsInstance(response.data['error'], str)

        response = hug.test.call('POST', controllers, f'{test_nodes[0]._id}/tasks', params={
            'task_id': 'MissingDevices'
        })
        self.assertEqual(response.status, hug.HTTP_INTERNAL_SERVER_ERROR)
        self.assertIsNotNone(response.data)
        self.assertIsInstance(response.data['error'], str)

        response = hug.test.call('POST', controllers, f'{test_nodes[0]._id}/tasks', params={
            'task_id': 'NotFeasible'
        })
        self.assertEqual(response.status, hug.HTTP_INTERNAL_SERVER_ERROR)
        self.assertIsNotNone(response.data)
        self.assertIsInstance(response.data['error'], str)

    def test_delete_node_tasks(self):
        response = hug.test.call(
            'DELETE', controllers, f'{test_nodes[0]._id}/tasks/{ObjectId()}')
        self.assertEqual(response.status, hug.HTTP_OK)
        self.assertIsNotNone(response.data)

        response = hug.test.call(
            'DELETE', controllers, f'error/tasks/{ObjectId()}')
        self.assertEqual(response.status, hug.HTTP_BAD_REQUEST)
        self.assertIsNotNone(response.data)
        self.assertIsInstance(response.data['error'], str)

        response = hug.test.call(
            'DELETE', controllers, f'{ObjectId()}/tasks/{ObjectId()}')
        self.assertEqual(response.status, hug.HTTP_NOT_FOUND)
        self.assertIsNotNone(response.data)
        self.assertIsInstance(response.data['error'], str)
