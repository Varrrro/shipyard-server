from typing import List

from bson.objectid import ObjectId
from pymongo import ReturnDocument

from shipyard.db import db
from shipyard.errors import NotFound, NotFeasible
from shipyard.node.model import Node
from shipyard.task.model import Task
from shipyard.crane.feasibility import check_feasibility


class NodeService():
    """Node business logic."""

    @staticmethod
    def get_all() -> List[Node]:
        """Fetch all nodes from the database."""

        return Node.Schema().load(db.nodes.find(), many=True)

    @staticmethod
    def get_by_id(node_id: str) -> Node:
        """
        Fetch a node from the database by its ID.

        Returns `None` if no node is found with the given ID.
        """

        result = db.nodes.find_one({'_id': ObjectId(node_id)})
        if result is None:
            return None
        return Node.Schema().load(result)

    @staticmethod
    def get_by_name(node_name: str) -> Node:
        """
        Fetch a node from the database by its name.

        Returns `None` if no node is found with the given name.
        """

        result = db.nodes.find_one({'name': node_name})
        if result is None:
            return None
        return Node.Schema().load(result)

    @staticmethod
    def create(new_node: Node) -> str:
        """
        Insert a new node into the database.

        If the name of the new node is already in use, this method raises a
        `ValueError`. If not, the new node is inserted and its new ID is
        returned.
        """

        result = db.nodes.find_one({'name': new_node.name})
        if result is not None:
            raise ValueError('A node already exists with the given name.')

        new_id = db.nodes.insert_one(Node.Schema(
            exclude=['_id']).dump(new_node)).inserted_id
        return str(new_id)

    @staticmethod
    def delete(node_id: str) -> Node:
        """
        Removes the node with the given ID from the database.

        Returns the node that has been deleted. If no node is found with the
        given ID, this method returns `None`.
        """

        result = db.nodes.find_one_and_delete({'_id': ObjectId(node_id)})
        if result is None:
            return None
        return Node.Schema().load(result)

    @staticmethod
    def add_task(node_id: str, task_id: str) -> Node:
        """
        Adds a new task to the given node's taskset.

        Returns the updated node with the new task added to its task list.

        If the node or the task can't be found using the given IDs, raises a
        `NotFound` exception.

        If the new taskset doesn't pass the feasibility check, raises a
        `NotFeasible` exception.
        """

        node = db.nodes.find_one({'_id': ObjectId(node_id)})
        if node is None:
            raise NotFound('No node found with the given ID')
        node = Node.Schema().load(node)

        task = db.tasks.find_one({'_id': ObjectId(task_id)})
        if task is None:
            raise NotFound('No task found with the given ID')
        task = Task.Schema().load(task)

        new_taskset = node.tasks + [task]
        if check_feasibility(new_taskset) is False:
            raise NotFeasible('The new taskset isn\'t feasible')

        updated_node = db.nodes.find_one_and_update({'_id': ObjectId(node_id)},
                                                    {'$push': {
                                                        'tasks': Task.Schema().dump(task)
                                                    }},
                                                    return_document=ReturnDocument.AFTER)
        return Node.Schema().load(updated_node)
