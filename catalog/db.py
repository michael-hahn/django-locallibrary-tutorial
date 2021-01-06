from z3 import Int, String, Solver, sat, InRe, Union, Re, StringVal, Length, SubSeq, Concat, Star
from django.core.untrustedtypes import UntrustedInt, UntrustedStr


class BiNode(object):
    """Node class with two children."""
    def __init__(self, val, *, key=None):
        """Use key for organization if exists; otherwise, use val"""
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


def _synthesize_int(upper_bound, lower_bound):
    """Synthesize an integer value given bounds."""
    # TODO: If neither upper and lower bound exists,
    #  perhaps we should pick a random value
    z3_solver = Solver()
    var = Int('v')
    if upper_bound:
        z3_solver.add(var < upper_bound)
    if lower_bound:
        z3_solver.add(var > lower_bound)
    satisfied = z3_solver.check()
    if satisfied == sat:
        return UntrustedInt(z3_solver.model()[var].as_long(),
                            untrusted=True, synthesized=True)
    else:
        return None


def _synthesize_str(upper_bound, lower_bound, charset=None):
    """Synthesize a string from charset and bounds.
    If charset is not given by the user, default is A-Za-z.
    charset must be arranged from the smallest to largest."""
    z3_solver = Solver()
    var = String('s')
    # Possible characters to generate a synthesized string
    if not charset:
        charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"  # upper-case
        charset += "abcdefghijklmnopqrstuvwxyz"  # lower-case
    chars = Union([Re(StringVal(c)) for c in charset])

    from random import randint
    # Create a regular expression template
    # Case 1: if only the lower bound is provided
    if lower_bound and not upper_bound:
        bound_length = len(lower_bound)
        # The length of our synthesized string is
        # the length of the lower bound + 1
        z3_solver.add(Length(var) == bound_length + 1)
        # We make the first "offset" characters of our
        # synthesized string be the same as the lower
        # bound and "offset" is picked randomly
        # offset may change later, as we will see
        offset = randint(0, bound_length - 1)
        # The "offset"+1-th character of our synthesized
        # string should be larger than that of the lower
        # bound (if possible) to ensure our string is larger
        bound_char = lower_bound[offset]
        # Find the position of bound_char in charset
        bound_pos = charset.find(bound_char)
        if bound_pos < 0:
            # If not found, charset is not given correctly.
            # Consider synthesis failed.
            # TODO: Perhaps raise an error to be explicit
            return None
        elif bound_pos >= len(charset) - 1:
            # If bound_char is the biggest possible in charset
            while bound_pos >= len(charset) - 1 and offset < bound_length:
                # Go to the next character until we are no longer
                # able to because we are at the last character
                # of the bound string
                bound_char = lower_bound[offset]
                bound_pos = charset.find(bound_char)
                offset += 1
        # The first part of our synthesized string
        # TODO: The next line of code is potentially redundant (thanks to template)
        z3_solver.add(SubSeq(var, 0, offset) == StringVal(lower_bound[:offset]))
        if offset == bound_length:
            # We cannot find any usable character in bound string
            # This is OK because we always add a new character at
            # the end of our synthesized string anyways.
            # So the first part of our synthesized string looks
            # just like the bound string.
            template = Concat(Re(StringVal(lower_bound[:offset])), Star(chars))
        else:
            # We can find (randomly) a larger character
            synthesized_char = charset[randint(bound_pos + 1, len(charset) - 1)]
            char = Re(StringVal(synthesized_char))
            template = Concat(Re(StringVal(lower_bound[:offset])), char, Star(chars))
    # Case 2: if only the upper bound is provided
    #         We follow the opposite to Case 1, with some differences
    elif upper_bound and not lower_bound:
        bound_length = len(upper_bound)
        # The length of our synthesized string is
        # the length of the upper bound - 1 unless
        # the length of the upper bound is 1
        if bound_length == 1:
            # Find the position of the only character
            # in the bound string
            bound_pos = charset.find(upper_bound[0])
            if bound_pos < 0:
                # If not found, charset is not given correctly.
                # Consider synthesis failed.
                # TODO: Perhaps raise an error to be explicit
                return None
            elif bound_pos == 0:
                # If it is already the smallest that can be,
                # we simply have no options. Consider synthesis failed.
                # TODO: Perhaps raise an error/warning to be explicit
                return None
            else:
                # synthesized_char is the final synthesis string
                synthesized_char = charset[randint(0, bound_pos - 1)]
                return UntrustedStr(synthesized_char, untrusted=True, synthesized=True)
        else:
            # The length of our synthesized string is
            # the length of the upper bound - 1.
            z3_solver.add(Length(var) == bound_length - 1)
            offset = randint(0, bound_length - 2)
            bound_char = upper_bound[offset]
            bound_pos = charset.find(bound_char)
            if bound_pos < 0:
                # TODO: Perhaps raise an error to be explicit
                return None
            elif bound_pos == 0:
                # If bound_char is the smallest possible in charset
                while bound_pos == 0 and offset < bound_length - 1:
                    # Go to the next character until we are no longer
                    # able to because we are at the last character
                    # of the bound string
                    bound_char = upper_bound[offset]
                    bound_pos = charset.find(bound_char)
                    offset += 1
            # The first part of our synthesized string
            # TODO: The next line of code is potentially redundant (thanks to template)
            z3_solver.add(SubSeq(var, 0, offset) == StringVal(upper_bound[:offset]))
            if offset == bound_length:
                # We cannot find any usable character in bound string
                # This is OK because our synthesized string already has
                # one fewer character anyways.
                # So the first part of our synthesized string looks
                # just like the bound string.
                template = Concat(Re(StringVal(upper_bound[:offset])), Star(chars))
            else:
                # We can find (randomly) a smaller character
                synthesized_char = charset[randint(0, bound_pos - 1)]
                char = Re(StringVal(synthesized_char))
                template = Concat(Re(StringVal(upper_bound[:offset])), char, Star(chars))
    # Case 3: if both bounds are provided
    elif upper_bound and lower_bound:
        # Note that there must exist a valid string between
        # the upper and the lower bound; otherwise, the data
        # structure itself must have been ill-formed! (It is
        # possible that only one valid string exists between
        # the bounds, however.)
        upper_bound_length = len(upper_bound)
        lower_bound_length = len(lower_bound)
        bound_length = min(upper_bound_length, lower_bound_length)
        # The first "offset" characters are the same
        # between both upper and lower bound strings
        offset = 0
        while offset < bound_length and upper_bound[offset] == lower_bound[offset]:
            offset += 1
        # TODO: The next line of code is potentially redundant (thanks to template)
        z3_solver.add(SubSeq(var, 0, offset) == StringVal(lower_bound[:offset]))

        # Case A: offset is smaller than both
        #         upper and lower bound length
        if offset < bound_length:
            # We can set our synthesized string
            # to be the same as the bound length
            z3_solver.add(Length(var) == bound_length)
            # The character after the first offset
            # characters should be smaller than
            # upper bound character but larger than
            # the character at the same location in
            # the lower bound string
            upper_bound_char = upper_bound[offset]
            upper_bound_pos = charset.find(upper_bound_char)
            lower_bound_char = lower_bound[offset]
            lower_bound_pos = charset.find(lower_bound_char)
            synthesized_char = charset[randint(lower_bound_pos + 1, upper_bound_pos - 1)]
        # Case B: offset is the same length as the bound length,
        #         which means the low bound string is the same
        #         as the first part of the upper bound string and
        #         the upper bound string must be longer
        else:
            # We can set our synthesized string
            # to be the same as the upper bound
            # string's length
            z3_solver.add(Length(var) == upper_bound_length)
            # The character after the first offset
            # characters should be smaller than
            # upper bound character
            upper_bound_char = upper_bound[offset]
            upper_bound_pos = charset.find(upper_bound_char)
            synthesized_char = charset[randint(0, upper_bound_pos - 1)]

        char = Re(StringVal(synthesized_char))
        template = Concat(Re(StringVal(lower_bound[:offset])), char, Star(chars))
    # TODO: If neither upper and lower bound exists,
    #  perhaps we should pick a random string, instead
    #  of returning None
    else:
        return None

    # Our synthesized string should match the template
    z3_solver.add(InRe(var, template))
    satisfied = z3_solver.check()
    if satisfied == sat:
        return UntrustedStr(z3_solver.model()[var].as_string(),
                            untrusted=True, synthesized=True)
    else:
        return None


class BinarySearchTree(object):
    """BST using BiNode."""
    def __init__(self):
        self.root = None

    def insert(self, val, key=None):
        if self.root is None:
            self._set_root(val, key)
        else:
            # BST nodes either all have a key or none of the nodes have a key
            if self.root.has_key() and not key:
                return False
            elif not self.root.has_key() and key:
                return False
            else:
                self._insert_node(self.root, val, key)

    def _set_root(self, val, key=None):
        self.root = BiNode(val, key=key)

    def _insert_node(self, curr, val, key=None):
        """Only unique values (or keys if exist) inserted modify the tree"""
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
            pass

    def _max_value(self, node):
        """The maximum value (or key is exists) of a (sub)tree rooted at node."""
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
        """The minimum value (or key if exists) of a (sub)tree rooted at node."""
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
        """Synthesize the value (or key if exists) of a node."""
        # TODO: CRITICAL! In some cases, synthesis value
        #  should take into consideration the parent value!
        upper_bound = self._min_value(node.right_child)
        lower_bound = self._max_value(node.left_child)
        # If neither bound exists, no synthesis
        if not upper_bound and not lower_bound:
            # TODO: consider a random value as synthesized value?
            #  If so, handle this case in each specific type.
            return False
        # Synthesize either the key (if exists) or val
        if node.key:
            synthesize_type = type(node.key).__name__
        else:
            synthesize_type = type(node.val).__name__

        if synthesize_type == 'int' or synthesize_type == 'UntrustedInt':
            synthesized_value = _synthesize_int(upper_bound, lower_bound)
        elif synthesize_type == 'str' or synthesize_type == 'UntrustedStr':
            synthesized_value = _synthesize_str(upper_bound, lower_bound)
        else:
            raise NotImplementedError("")

        # Synthesis failed if synthesized_value is None
        if synthesized_value is None:
            return False
        else:
            if node.key:
                node.key = synthesized_value
                # If a key is synthesized, val is automatically set to None
                node.val = None
            else:
                node.val = synthesized_value
            return True

    def to_ordered_list(self, node, ordered_list):
        """Convert the tree into an ordered list of nodes."""
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
