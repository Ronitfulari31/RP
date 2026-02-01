import logging

class DAGNode:
    """Base class for all nodes in the DAG NLP pipeline."""
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"dag.{name}")

    def run(self, context: dict) -> dict:
        """
        Execute the node logic.
        Returns the updated context, or None if the pipeline should STOP (HARD GATE).
        """
        raise NotImplementedError("Nodes must implement run(context)")

class ProcessingNode(DAGNode):
    """Nodes that perform computation and update the context."""
    def run(self, context: dict) -> dict:
        self.logger.info(f"Executing ProcessingNode: {self.name}")
        return self._process(context)

    def _process(self, context: dict) -> dict:
        raise NotImplementedError

class GateNode(DAGNode):
    """Nodes that evaluate quality and decide if the flow should continue or change."""
    def run(self, context: dict) -> dict:
        self.logger.info(f"Evaluating GateNode: {self.name}")
        return self._evaluate(context)

    def _evaluate(self, context: dict) -> dict:
        raise NotImplementedError

class RouterNode(DAGNode):
    """Nodes that decide which branch to take."""
    def run(self, context: dict) -> str:
        self.logger.info(f"Routing via Node: {self.name}")
        return self._route(context)

    def _route(self, context: dict) -> str:
        raise NotImplementedError
