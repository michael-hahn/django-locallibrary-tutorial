from django.core.untrustedtypes import UntrustedInt, UntrustedStr
from catalog.synthesis import IntSynthesizer, StrSynthesizer

from collections import UserDict
from sortedcontainers import SortedList


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

    def delete(self, key_or_val):
        """Modify the tree by removing a node if it has the
        given value (or key if exists). Otherwise, do nothing.
        This is the public API to delete a node in a tree."""
        self.root = self._delete_node(self.root, key_or_val)

    def _delete_node(self, curr, key_or_val):
        """Find a node based on the given value (or key if exists)
        and delete the node from the tree if it exists. Application
        should call the public API delete() instead."""
        if curr is None:
            return curr
        curr_val = curr.val
        if curr.has_key():
            curr_val = curr.key

        if key_or_val < curr_val:
            curr.left_child = self._delete_node(curr.left_child, key_or_val)
        elif key_or_val > curr_val:
            curr.right_child = self._delete_node(curr.right_child, key_or_val)
        else:
            if curr.left_child is None:
                return curr.right_child
            elif curr.right_child is None:
                return curr.left_child
            candidate = self._min_value_node(curr.right_child)

            curr.val = candidate.val
            key_or_val = candidate.val
            if curr.has_key():
                curr.key = candidate.key
                key_or_val = candidate.key
            curr.right_child = self._delete_node(curr.right_child, key_or_val)
        return curr

    def _max_value_node(self, node):
        """The node with the maximum value (or key if exists) of a (sub)tree
        rooted at node. The maximum value is the node itself if it has no
        right subtree."""
        if node is None:
            return None
        if node.right_child:
            return self._max_value_node(node.right_child)
        return node

    def _max_value(self, node):
        """The maximum value (or key if exists) of a (sub)tree rooted at node.
        The maximum value is the node itself if it has no right subtree."""
        max_node = self._max_value_node(node)
        if max_node is None:
            return False
        if max_node.has_key():
            return max_node.key
        else:
            return max_node.val

    def _min_value_node(self, node):
        """The node with the minimum value (or key if exists) of a (sub)tree
        rooted at node. The minimum value is the node itself if it has no
        left subtree."""
        if node is None:
            return None
        if node.left_child:
            return self._min_value_node(node.left_child)
        else:
            return node

    def _min_value(self, node):
        """The minimum value (or key if exists) of a (sub)tree rooted at node.
        The minimum value is the node itself if it has no left subtree."""
        min_node = self._min_value_node(node)
        if min_node is None:
            return False
        if min_node.has_key():
            return min_node.key
        else:
            return min_node.val

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


class SynthesizableSortedList(SortedList):
    """Inherit from SortedList to create a custom sorted list
    that behaves exactly like a sorted list (with elements sorted
    in the list) but the elements in the SynthesizableSortedList
    can be synthesized. Reference of the sorted containers:
    http://www.grantjenks.com/docs/sortedcontainers/sortedlist.html."""
    def __setitem__(self, index, value):
        """SortedList raise not-implemented error when calling
        __setitem__ because it will not allow users to simply
        replace a value at index (in case the list becomes
        unsorted). We implement this function based on SortedList
        __getitem__ implementation for direct replacement so that
        synthesis can replace a value directly. Note that our
        synthesis guarantees the sorted order so it is OK to do
        so, but the user of SynthesizableSortedList should not
        call this function.

        This function is implemented specifically for our synthesis.
        One should not use this function to e.g., append a new value.

        Note that We are unfortunately using many supposedly
        "protected" instance attributes to implement __setitem__."""
        _lists = self._lists
        _maxes = self._maxes

        pos, idx = self._pos(index)
        _lists[pos][idx] = value
        # SortedList maintains a list of maximum values for each sublist.
        # We must update the maximum value if "value" becomes the
        # maximum value of its sublist.
        if idx == len(_lists[pos]) - 1:
            _maxes[pos] = value

    def synthesis(self, index):
        """Synthesize a value at a given index in the sorted list.
        The synthesized value must ensure that the list is still sorted."""
        if index >= self._len:
            raise IndexError('list index out of range')

        value = self.__getitem__(index)
        synthesize_type = type(value).__name__
        if synthesize_type == 'UntrustedInt':
            synthesizer = IntSynthesizer()
        elif synthesize_type == 'UntrustedStr':
            synthesizer = StrSynthesizer()
        else:
            raise NotImplementedError("We cannot synthesize value of type "
                                      "{type} yet".format(type=synthesize_type))

        if index == 0:
            # The value to be synthesized is the smallest in the sorted list
            synthesizer.lt_constraint(self.__getitem__(index + 1))
        elif index == self._len - 1:
            # The value to be synthesized is the largest in the sorted list
            synthesizer.gt_constraint(self.__getitem__(index - 1))
        else:
            # The value to be synthesized is in the middle of the sorted list
            synthesizer.bounded_constraints(upper_bound=self.__getitem__(index + 1),
                                            lower_bound=self.__getitem__(index - 1))
        synthesized_value = synthesizer.to_python(synthesizer.value)
        self.__setitem__(index, synthesized_value)


class SynthesizableDict(UserDict):
    """Inherit from UserDict to create a custom dict that
    behaves exactly like Python's built-in dict but the
    elements in the SynthesizableDict can be synthesized.
    UserDict is a wrapper/adapter class around the built-in
    dict, which makes the painful process of inheriting
    directly from Python's built-in dict class much easier.
    Reference:
    https://docs.python.org/3/library/collections.html#userdict-objects.

    Alternatively, we can use abstract base classes in
    Python's collections.abc module. In this case, we could
    use MutableMapping as a mixin class to inherit. ABC makes
    modifying a data structure's core functionality easier
    than directly modifying it from dict."""
    def synthesis(self, key):
        """dict does not provide a programmatic way to
        access and overwrite keys in-place. Since UserDict
        (as well as MutableMapping for that matter) uses
        Python's built-in key, we cannot do a real
        synthesis. We will do a "fake" one just to illustrate,
        but something still won't work in this data structure."""
        if key not in self.data:
            return True
        val = self.data[key]
        synthesize_type = type(key).__name__
        if synthesize_type == 'UntrustedInt':
            synthesizer = IntSynthesizer()
            synthesizer.eq_constraint(UntrustedInt.custom_hash, key.__hash__())
        elif synthesize_type == 'UntrustedStr':
            synthesizer = StrSynthesizer()
            synthesizer.eq_constraint(UntrustedStr.custom_hash, key.__hash__())
        else:
            raise NotImplementedError("We cannot synthesize value of type "
                                      "{type} yet".format(type=synthesize_type))

        synthesized_value = synthesizer.to_python(synthesizer.value)
        # synthesized_value and key should have the same hash value
        # TODO: Note that if synthesized_value happens to be the same as
        #  the original key, this insertion does nothing. For example,
        #  because of the default hash function of UntrustedInt, the
        #  synthesized int might be the same as the original int key, so
        #  this insertion does not have any effect.
        self.data[synthesized_value] = val


def bst_test():
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


def sorted_list_test():
    sl = SynthesizableSortedList()
    sl.update([UntrustedStr("Jake"), UntrustedStr("Blair"), UntrustedStr("Luke"),
               UntrustedStr("Andre"), UntrustedStr("Zack")])
    print(sl)
    sl.synthesis(2)
    print(sl)
    sl.synthesis(0)
    print(sl)
    sl.synthesis(4)
    print(sl)

    sl = SynthesizableSortedList()
    sl.update([UntrustedInt(7), UntrustedInt(5), UntrustedInt(14),
              UntrustedInt(9), UntrustedInt(12)])
    print(sl)
    sl.synthesis(2)
    print(sl)
    sl.synthesis(0)
    print(sl)
    sl.synthesis(4)
    print(sl)


def dict_test():
    sd = SynthesizableDict()
    sd[UntrustedStr("Jake")] = UntrustedInt(7)
    sd[UntrustedStr("Blair")] = UntrustedInt(5)
    sd[UntrustedStr("Luke")] = UntrustedInt(14)
    sd[UntrustedStr("Andre")] = UntrustedInt(9)
    sd[UntrustedStr("Zack")] = UntrustedInt(12)
    for key in sd:
        print("{key} -> {value}".format(key=key, value=sd[key]))
    sd.synthesis(UntrustedStr("Blair"))
    print("After deleting 'Blair' by synthesis...")
    for key in sd:
        print("{key}({hash}) -> {value} [Synthesized: {synthesis}]".format(key=key,
                                                                           hash=key.__hash__(),
                                                                           value=sd[key],
                                                                           synthesis=key.synthesized))
    sd = SynthesizableDict()
    sd[UntrustedInt(7)] = UntrustedStr("Jake")
    # We need a super big integer key so that the synthesized integer
    # value would be different from this original value (see the TODO above)
    sd[UntrustedInt(32345435432758439203535345435)] = UntrustedStr("Blair")
    sd[UntrustedInt(14)] = UntrustedStr("Luke")
    sd[UntrustedInt(9)] = UntrustedStr("Andre")
    sd[UntrustedInt(12)] = UntrustedStr("Zack")
    for key in sd:
        print("{key} -> {value}".format(key=key, value=sd[key]))
    sd.synthesis(UntrustedInt(32345435432758439203535345435))
    print("After deleting '5' by synthesis...")
    for key in sd:
        print("{key}({hash}) -> {value} [Synthesized Key: {synthesis}]".format(key=key,
                                                                               hash=key.__hash__(),
                                                                               value=sd[key],
                                                                               synthesis=key.synthesized))


if __name__ == "__main__":
    bst_test()
    dict_test()
    sorted_list_test()
