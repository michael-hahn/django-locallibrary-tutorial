from z3 import Int, Solver, Z3_L_TRUE
from django.core.untrustedtypes import UntrustedInt


class BiNode(object):
    """Node class with two children."""
    def __init__(self, val):
        self._val = val
        self._left = None
        self._right = None

    @property
    def val(self):
        return self._val

    @val.setter
    def val(self, val):
        self._val = val

    @property
    def left_child(self):
        return self._left

    @left_child.setter
    def left_child(self, node):
        self._left = node

    @property
    def right_child(self):
        return self._right

    @right_child.setter
    def right_child(self, node):
        self._right = node


class BinarySearchTree(object):
    """BST using BiNode."""
    def __init__(self):
        self.root = None

    def insert(self, val):
        if self.root is None:
            self._set_root(val)
        else:
            self._insert_node(self.root, val)

    def _set_root(self, val):
        self.root = BiNode(val)

    def _insert_node(self, curr, val):
        """Only unique values inserted modify the tree"""
        if val < curr.val:
            if curr.left_child:
                self._insert_node(curr.left_child, val)
            else:
                curr.left_child = BiNode(val)
        elif val > curr.val:
            if curr.right_child:
                self._insert_node(curr.right_child, val)
            else:
                curr.right_child = BiNode(val)
        else:
            pass

    def _max_value(self, node):
        """The maximum value of a (sub)tree rooted at node."""
        if node is None:
            return False
        if node.right_child:
            return self._max_value(node.right_child)
        else:
            return node.val

    def _min_value(self, node):
        """The minimum value of a (sub)tree rooted at node."""
        if node is None:
            return False
        if node.left_child:
            return self._min_value(node.left_child)
        else:
            return node.val

    def synthesize(self, node):
        """Synthesize the value of a node."""
        # TODO: ATM we assume a node's val is UntrustedInt.
        z3_solver = Solver()
        synthesized_val = Int('v')
        max_bound = self._min_value(node.right_child)
        min_bound = self._max_value(node.left_child)
        # if neither bound exists, no synthesis
        if not max_bound and not min_bound:
            return False

        if max_bound:
            z3_solver.add(synthesized_val < max_bound)
        if min_bound:
            z3_solver.add(synthesized_val > min_bound)
        satisfied = z3_solver.check()
        if satisfied.r == Z3_L_TRUE:
            node.val = UntrustedInt(z3_solver.model()[synthesized_val].as_long(), untrusted=True, synthesized=True)
            return True
        else:
            return False

    def to_ordered_list(self, node, ordered_list):
        """Convert the tree into an ordered list."""
        if node.left_child:
            self.to_ordered_list(node.left_child, ordered_list)
        ordered_list.append(node.val)
        if node.right_child:
            self.to_ordered_list(node.right_child, ordered_list)

    def __str__(self):
        """Print out the tree in-order."""
        ordered_list = list()
        self.to_ordered_list(self.root, ordered_list)
        return str(ordered_list)


if __name__ == "__main__":
    bst = BinarySearchTree()
    bst.insert(UntrustedInt(7))
    bst.insert(UntrustedInt(5))
    bst.insert(UntrustedInt(14))
    bst.insert(UntrustedInt(9))
    bst.insert(UntrustedInt(7))
    bst.insert(UntrustedInt(12))
    print(str(bst))
    print(bst.synthesize(bst.root.right_child.left_child))
    print(str(bst))
