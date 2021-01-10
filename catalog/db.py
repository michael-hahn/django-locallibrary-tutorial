from django.core.untrustedtypes import UntrustedInt, UntrustedStr
from catalog.synthesis import IntSynthesizer, StrSynthesizer


class BiNode(object):
    """Node class with two children."""
    def __init__(self, val, *, key=None):
        """Use key for organization if exists; otherwise, use val."""
        self._val = val
        self._key = key
        self._left = None
        self._right = None

    @property
    def val(self):
        return self._val

    @val.setter
    def val(self, val):
        self._val = val

    @property
    def key(self):
        return self._key

    @key.setter
    def key(self, key):
        self._key = key

    def has_key(self):
        return bool(self._key)

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

    def insert(self, val, key=None):
        """Insert a value (or key/value pair if keys are used) to a BST.
        Returns False if insertion failed (e.g., if a key/value pair
        is given to be inserted into a value-only tree). This is the
        public API to construct a new tree or add new nodes to an existing tree."""
        if self.root is None:
            self._set_root(val, key)
        else:
            # BST nodes either all have a key or none of the nodes have a key!
            if self.root.has_key() and not key:
                return False
            elif not self.root.has_key() and key:
                return False
            else:
                self._insert_node(self.root, val, key)

    def _set_root(self, val, key=None):
        """Application should not call this function directly.
        Always call the public API insert() to construct a new tree."""
        self.root = BiNode(val, key=key)

    def _insert_node(self, curr, val, key=None):
        """Only unique values (or keys if exist) inserted modify the tree.
        If insertion is not successful (e.g., val is the same as a node
        already in the tree), it returns False. Application should not call
        this function directly. Always call the public API insert() to add
        new nodes to an existing tree."""
        if key and key < curr.key or not key and val < curr.val:
            if curr.left_child:
                self._insert_node(curr.left_child, val, key)
            else:
                curr.left_child = BiNode(val, key=key)
        elif key and key > curr.key or not key and val > curr.val:
            if curr.right_child:
                self._insert_node(curr.right_child, val, key)
            else:
                curr.right_child = BiNode(val, key=key)
        else:
            return False

    def find(self, key_or_val):
        """Return the node if value (or key if exists) is in the
        tree; otherwise, return None. This is the public API to
        find a node in a tree."""
        return self._find_node(self.root, key_or_val)

    def _find_node(self, curr, key_or_val):
        """Find a node based on the given value (or key if exists).
        Returns None if the value (or key) does not exist in the
        tree. Application should call the public API find() instead."""
        if not curr:
            return None
        curr_val = curr.val
        if curr.key:
            curr_val = curr.key

        if key_or_val == curr_val:
            return curr
        elif key_or_val > curr_val:
            return self._find_node(curr.right_child, key_or_val)
        else:
            return self._find_node(curr.left_child, key_or_val)

    def _max_value(self, node):
        """The maximum value (or key if exists) of a (sub)tree rooted at node.
        The maximum value is the node itself if it has no right subtree."""
        if node is None:
            return False
        if node.right_child:
            return self._max_value(node.right_child)
        else:
            if node.key:
                return node.key
            else:
                return node.val

    def _min_value(self, node):
        """The minimum value (or key if exists) of a (sub)tree rooted at node.
        The minimum value is the node itself if it has no left subtree."""
        if node is None:
            return False
        if node.left_child:
            return self._min_value(node.left_child)
        else:
            if node.key:
                return node.key
            else:
                return node.val

    def synthesize(self, node):
        """Synthesize the val (or key if exists) of a node.
        Only performs bounded value synthesis if both upper
        and lower bound exist for the node. Otherwise, create
        an Untrusted val (or key if exists) of the same value
        and with the synthesized flag set. If synthesis
        failed for any reason, return False. If synthesis
        succeeded, return True."""
        upper_bound = self._min_value(node.right_child)
        lower_bound = self._max_value(node.left_child)
        # Synthesize either the key (if exists) or val
        # How key (or val) is synthesized is based on
        # its type, so we obtain the type first.
        synthesize_type = type(node.val).__name__
        if node.key:
            synthesize_type = type(node.key).__name__

        if synthesize_type == 'int' or synthesize_type == 'UntrustedInt':
            synthesizer = IntSynthesizer()
        elif synthesize_type == 'str' or synthesize_type == 'UntrustedStr':
            synthesizer = StrSynthesizer()
        else:
            raise NotImplementedError("We cannot synthesize value of type "
                                      "{type} yet".format(type=synthesize_type))

        # If at most one bound exists, do simple synthesis
        if not upper_bound or not lower_bound:
            if node.key:
                synthesized_value = synthesizer.simple_synthesis(node.key)
            else:
                synthesized_value = synthesizer.simple_synthesis(node.val)
        else:
            # Do bounded synthesis if both bounds exist
            synthesized_value = synthesizer.bounded_synthesis(upper_bound=upper_bound,
                                                              lower_bound=lower_bound)

        # Some synthesis can fail; synthesis
        # failed if synthesized_value is None
        if synthesized_value is None:
            return False
        # Finally, if synthesis succeeded, replace the val
        # (or key if exists) with the synthesized value.
        else:
            if node.key:
                node.key = synthesized_value
                node.val = None
            else:
                node.val = synthesized_value
        return True

    def to_ordered_list(self, node, ordered_list):
        """Convert the tree into an in-ordered list of nodes.
        The list is stored at ordered_list parameter."""
        if node is None:
            return ordered_list

        if node.left_child:
            self.to_ordered_list(node.left_child, ordered_list)
        ordered_list.append(node)
        if node.right_child:
            self.to_ordered_list(node.right_child, ordered_list)

    def __str__(self):
        """Print out the tree in-order."""
        ordered_list = list()
        self.to_ordered_list(self.root, ordered_list)
        printout = ""
        for node in ordered_list:
            if node.key:
                printout += "{key}({value}) ".format(key=node.key, value=node.val)
            else:
                printout += "{value} ".format(value=node.val)
        return printout


if __name__ == "__main__":
    bst = BinarySearchTree()
    bst.insert(UntrustedStr("Jake"), UntrustedInt(7))
    bst.insert(UntrustedStr("Blair"), UntrustedInt(5))
    bst.insert(UntrustedStr("Luke"), UntrustedInt(14))
    bst.insert(UntrustedStr("Andre"), UntrustedInt(9))
    bst.insert(UntrustedStr("Zack"), UntrustedInt(12))
    print(str(bst))
    print(bst.synthesize(bst.root))
    print(str(bst))

    bst = BinarySearchTree()
    bst.insert(UntrustedStr("Jake"))
    bst.insert(UntrustedStr("Blair"))
    bst.insert(UntrustedStr("Luke"))
    bst.insert(UntrustedStr("Andre"))
    bst.insert(UntrustedStr("Zack"))
    print(str(bst))
    print(bst.synthesize(bst.root))
    print(str(bst))
