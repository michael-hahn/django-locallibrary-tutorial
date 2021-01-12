"""Synthesis classes"""
from z3 import Solver, sat
from z3 import String, StringVal, Length, SubSeq, Concat
from z3 import Re, InRe, Union, Star, Plus
from z3 import Int
from z3 import BitVec

from django.core.untrustedtypes import UntrustedInt, UntrustedStr


class Synthesizer(object):
    """Synthesis base class."""
    def __init__(self, symbol):
        self.solver = Solver()
        self.var = symbol

    def lt_constraint(self, value, **kargs):
        """Add to solver a less-than constraint:
        self.var < value. By default, we assume that the type
        of the value can be handled by Z3 directly with <, such
        as integer, but this is not always the case. In some
        cases like string, this function should be overridden."""
        self.solver.add(self.var < value)

    def gt_constraint(self, value, **kargs):
        """Add to solver a greater-than constraint:
        self.var > value. By default, we assume that the type
        of the value can be handled by Z3 directly with >, such
        as integer, but this is not always the case. In some
        cases like string, this function should be overridden."""
        self.solver.add(self.var > value)

    def eq_constraint(self, func, value, **kargs):
        """Add to solver an equal-to constraints:
        func(self.var, **kargs) == value. Note that
        func can be any custom function but operations
        in func must be supported by the Z3 variable
        type. For example, Z3's Int() does not support
        << (bit shift); therefore, func cannot have
        operations that use << to manipulate Int() variable.
        func can take any number of *keyed* arguments
        but the first argument (required, non-keyed)
        must be the value to be synthesized. In summary,
        not all func can be supported for synthesis!

        This is most useful for func to be a custom hash
        function so func is expected to have operations
        like <<, >>, +, -. If this is the use case, one
        should use BitVec for the synthesis value since
        BitVec supports << and >> in Z3."""
        self.solver.add(func(self.var, **kargs) == value)

    def _bounded_constraints(self, upper_bound, lower_bound, **kargs):
        """Add to solver constraints derived from an upper bound and
        a lower bound, both of which must exist (otherwise, one should
        call either lt_constraint() or gt_constraint() instead).
        Subclass should implement this function if the synthesizer
        allows bounded constraints but it should not call this function
        directly; instead, subclass should call bounded_synthesis().
        Note that this function is implemented mostly for convenience;
        In most cases, one can easily combine lt_constraint() and
        gt_constraint() to create the same bounded constraints. In
        some cases like string, this function should be overridden."""
        self.lt_constraint(upper_bound)
        self.gt_constraint(lower_bound)

    def is_satisfied(self):
        """Returns True if given constraints can be satisfied."""
        return self.solver.check() == sat

    @property
    def value(self):
        """Return synthesized variable value (Z3 type) if
        the model can be satisfied; otherwise returns None."""
        if self.is_satisfied():
            return self.solver.model()[self.var]
        else:
            return None

    def to_python(self, value):
        """Convert the value of Z3 type to Untrusted
        Python type (e.g., from z3.IntNumRef to
        UntrustedInt) depend on the type of _var."""
        raise NotImplementedError("to_python() is not overridden in <{subclass}>, "
                                  "subclassed from <{superclass}>.".
                                  format(subclass=self.__class__.__name__,
                                         superclass=type(self).__base__.__name__))

    def bounded_synthesis(self, *, upper_bound=None, lower_bound=None, **kargs):
        """Synthesis based on an upper and a lower bound, both
        of which must exist! The data type of upper_bound and
        lower_bound must be able to be compared and upper_bound
        must be larger than lower_bound. Subclasses must override
        _bounded_constraints() and call this function
        as public API. _bounded_constraints() can also raise
        ValueError if given bounds are not valid. A synthesized
        value is returned if synthesis is successful; otherwise,
        we return None."""
        if not upper_bound or not lower_bound:
            raise ValueError("Two bounds must be specified. Perhaps use a different"
                             "synthesis method or simply call random()?")
        if upper_bound <= lower_bound:
            raise ValueError("The upper bound should at least "
                             "be larger than the lower bound.")
        self._bounded_constraints(upper_bound, lower_bound, **kargs)
        if self.value is not None:
            return self.to_python(self.value)
        else:
            return None

    def simple_synthesis(self, value):
        """Synthesis by simply wrapping value in an Untrusted type
        (e.g., wrap Int to UntrustedInt) and set the type's
        synthesized flag to True."""
        raise NotImplementedError("simple_synthesis() is not overridden "
                                  "in <{subclass}>, subclassed from <{superclass}>.".
                                  format(subclass=self.__class__.__name__,
                                         superclass=type(self).__base__.__name__))

    def reset_constraints(self):
        self.solver.reset()


class IntSynthesizer(Synthesizer):
    """Synthesize an integer value, subclass from Synthesizer."""
    def __init__(self):
        super().__init__(Int('var'))

    def to_python(self, value):
        return UntrustedInt(value.as_long(), synthesized=True)

    def simple_synthesis(self, value):
        return UntrustedInt(value, synthesized=True)


class BitVecSynthesizer(Synthesizer):
    """Synthesize bit vector value, subclass from Synthesizer."""
    def __init__(self, bits=32):
        """Create a bit-vector variable in Z3
        named b with given (32 by default) bits."""
        super().__init__(BitVec('b', bits))

    def to_python(self, value):
        return UntrustedInt(value.as_long(), synthesized=True)

    def simple_synthesis(self, value):
        """Python can automatically convert a bit vector to int."""
        return UntrustedInt(value, synthesized=True)


class StrSynthesizer(Synthesizer):
    """Synthesize a string value, subclass from Synthesizer."""
    DEFAULT_UPPER_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    DEFAULT_LOWER_CHARS = "abcdefghijklmnopqrstuvwxyz"
    DEFAULT_NUM_CHARS = "0123456789"

    def __init__(self, charset=None):
        super().__init__(String("var"))
        if not charset:
            # Create a default character set
            # (always add upper-case chars first)
            charset = self.DEFAULT_UPPER_CHARS
            charset += self.DEFAULT_LOWER_CHARS
        self._charset = charset     # String representation
        self._chars = Union([Re(StringVal(c)) for c in self._charset])      # Z3 union representation

    def lt_constraint(self, value, **kargs):
        """Override base class lt_constraint(). We find the first character
        in value that has a smaller character and replace it with a smaller
        character picked by Z3. Every character before that would be the same
        as value and every character after that, if exists, is picked by Z3.
        If every character in value is the smallest character in charset, we
        try to remove the last character in value and use a shorter string.
        If there is no string smaller than value, an empty string is returned.
        The constraint is a regular expression template added to the solver.
        value cannot be an empty string!
        e.g., (assume the default charset)
        * "Jack" -> "[A-I]*"
        * "Adam" -> "A[A-Za-c]*" (the first "A" must be in template)
        * "AA" -> "A" (a shorter string)
        * "A" -> "" (there can be no smaller value, so empty string).

        An optional offset parameter can be provided, but this is mostly
        useful for bounded synthesis. If provided, characters in position
        0 to offset would be the same in synthesized string as in value
        (if offset < the length of the value). Offset is by default 0."""
        if not value:
            raise ValueError("value cannot be an empty string!")
        # Create a regular expression template for synthesis
        bound_length = len(value)
        offset = 0
        if "offset" in kargs:
            offset = kargs["offset"]
        # If bound_char is the smallest possible in charset
        # Go to the next character until we are no longer able to
        # because we are at the last character of the bound string
        while offset < bound_length:
            bound_char = value[offset]
            bound_pos = self._charset.find(bound_char)
            if bound_pos < 0:
                raise ValueError("upper-bound string '{upper}' contains a character "
                                 "'{character}' that is not found in the charset "
                                 "'{charset}'.".format(upper=value,
                                                       character=bound_char,
                                                       charset=self._charset))
            elif bound_pos == 0:
                offset += 1
            else:
                break
        if offset >= bound_length:
            # The last resort is to remove the last character
            # If value has only one character, then empty string
            # is the only possible answer
            synthesized_char = value[:bound_length-1]
            # In case synthesized_char is an empty string, we need
            # two arguments for Concat, which means we need to add
            # another empty string.
            empty_char = Re(StringVal(""))
            template = Concat(Re(StringVal(synthesized_char)), empty_char)
        else:
            possible_charset = self._charset[:bound_pos]
            char = Union([Re(StringVal(c)) for c in possible_charset])
            template = Concat(Re(StringVal(value[:offset])), char, Star(self._chars))
        # Our synthesized string should match the template
        self.solver.add(InRe(self.var, template))

    def gt_constraint(self, value, **kargs):
        """Override base class gt_constraint(). We find the first character
        in value that has a larger character and replace it (randomly) with
        a larger character. Every character before that would be the same
        as value and every character after that, if exists, is picked by Z3.
        If every character is value is the largest character in charset, we
        try to add at the end of value a new character and use a longer string.
        The constraint is a regular expression template added to the solver.
        e.g., (assume the default charset)
        * "Jack" -> "[K-Za-z][A-Za-z]*"
        * "" -> "[A-Za-z]+"
        * "z" -> "z[A-Za-z]+" (the first "z" must be in template).

        An optional offset parameter can be provided, but this is mostly
        useful for bounded synthesis. If provided, characters in position
        0 to offset would be the same in synthesized string as in value
        (if offset < the length of the value). Offset is by default 0."""
        bound_length = len(value)
        if bound_length == 0:
            # If value is an empty string, any non-empty string will do
            empty_char = Re(StringVal(""))
            template = Concat(empty_char, Plus(self._chars))
        else:
            offset = 0
            if "offset" in kargs:
                offset = kargs["offset"]
            # If bound_char is the biggest possible in charset,
            # go to the next character until we are no longer able to
            # because we are at the last character of the bound string
            while offset < bound_length:
                # The "offset" character of our synthesized string should
                # be larger than that of the lower bound (if possible)
                bound_char = value[offset]
                # Find the position of bound_char in charset
                bound_pos = self._charset.find(bound_char)
                if bound_pos < 0:
                    # If not found, charset is not given correctly.
                    return ValueError("lower-bound string '{lower}' contains a character "
                                      "'{character}' that is not found in the charset "
                                      "'{charset}'.".format(lower=value,
                                                            character=bound_char,
                                                            charset=self._charset))
                elif bound_pos >= len(self._charset) - 1:
                    offset += 1
                else:
                    break
            if offset >= bound_length:
                # We cannot find any usable character in bound string
                # This is OK because we can add a new character at
                # the end of our synthesized string anyways.
                # So the first part of our synthesized string looks
                # just like the bound string.
                template = Concat(Re(StringVal(value[:bound_length])), Plus(self._chars))
            else:
                # We can find a larger character
                possible_charset = self._charset[bound_pos+1:]
                char = Union([Re(StringVal(c)) for c in possible_charset])
                template = Concat(Re(StringVal(value[:offset])), char, Star(self._chars))
        # Our synthesized string should match the template
        self.solver.add(InRe(self.var, template))

    def _bounded_constraints(self, upper_bound, lower_bound, **kargs):
        """We cannot simply add lt_constraint() and gt_constraint() without
        specifying a common offset. Otherwise, it is possible that the template
        generated by lt_constraint() becomes incompatible with the template
        generated by gt_constraint() (so no string can be synthesized) even if it
        is lexicographically possible to synthesize a string between the two bounds."""
        upper_bound_length = len(upper_bound)
        lower_bound_length = len(lower_bound)
        bound_length = min(upper_bound_length, lower_bound_length)
        self.lt_constraint(upper_bound, offset=bound_length)
        self.gt_constraint(lower_bound, offset=bound_length)

    def to_python(self, value):
        return UntrustedStr(value.as_string(), synthesized=True)

    def simple_synthesis(self, value):
        return UntrustedStr(value, synthesized=True)


if __name__ == "__main__":
    synthesizer = IntSynthesizer()
    int_val = synthesizer.bounded_synthesis(upper_bound=92, lower_bound=7)
    assert int_val > 7, "{val} should be larger than 7, but it is not.".format(val=int_val)
    assert int_val < 92, "{val} should be smaller than than 92, but it is not.".format(val=int_val)
    synthesizer.reset_constraints()
    synthesizer.lt_constraint(34)
    int_val = synthesizer.to_python(synthesizer.value)
    assert int_val < 34, "{val} should be smaller than than 34, but it is not.".format(val=int_val)
    synthesizer.reset_constraints()
    synthesizer.gt_constraint(21)
    int_val = synthesizer.to_python(synthesizer.value)
    assert int_val > 7, "{val} should be larger than 21, but it is not.".format(val=int_val)

    # Define a simple function that can take Z3's Int type
    def calc(x, *, y):
        """* is needed so that y is a keyed argument!"""
        return x + y * y

    synthesizer.reset_constraints()
    synthesizer.eq_constraint(calc, 40, y=5)   # y is a keyed argument
    int_val = synthesizer.to_python(synthesizer.value)
    assert int_val == 15, "{val} should be equal to 15, but it is not.".format(val=int_val)

    synthesizer = StrSynthesizer()
    synthesizer.lt_constraint("A")
    str_val = synthesizer.to_python(synthesizer.value)
    assert str_val < "A", "{val} should be smaller than than 'A', but it is not.".format(val=str_val)
    synthesizer.reset_constraints()
    synthesizer.lt_constraint("AA")
    str_val = synthesizer.to_python(synthesizer.value)
    assert str_val < "AA", "{val} should be smaller than than 'AA', but it is not.".format(val=str_val)
    synthesizer.reset_constraints()
    synthesizer.lt_constraint("Jack")
    str_val = synthesizer.to_python(synthesizer.value)
    assert str_val < "Jack", "{val} should be smaller than than 'Jack', but it is not.".format(val=str_val)
    synthesizer.reset_constraints()
    synthesizer.lt_constraint("Adam")
    str_val = synthesizer.to_python(synthesizer.value)
    assert str_val < "Adam", "{val} should be smaller than than 'Adam', but it is not.".format(val=str_val)
    synthesizer.reset_constraints()

    synthesizer.gt_constraint("z")
    str_val = synthesizer.to_python(synthesizer.value)
    assert str_val > "z", "{val} should be larger than than 'z', but it is not.".format(val=str_val)
    synthesizer.reset_constraints()
    synthesizer.gt_constraint("")
    str_val = synthesizer.to_python(synthesizer.value)
    assert str_val > "", "{val} should be larger than than '', but it is not.".format(val=str_val)
    synthesizer.reset_constraints()
    synthesizer.gt_constraint("Jack")
    str_val = synthesizer.to_python(synthesizer.value)
    assert str_val > "Jack", "{val} should be larger than than 'Jack', but it is not.".format(val=str_val)
    synthesizer.reset_constraints()
    synthesizer.gt_constraint("zza")
    str_val = synthesizer.to_python(synthesizer.value)
    assert str_val > "zza", "{val} should be larger than than 'zza', but it is not.".format(val=str_val)
    synthesizer.reset_constraints()

    str_val = synthesizer.bounded_synthesis(upper_bound="zzzB", lower_bound="zzz")
    assert str_val == "zzzA", "{val} should be the same as 'zzzA', but it is not.".format(val=str_val)

    synthesizer = BitVecSynthesizer()
    synthesizer.gt_constraint(43)   # BitVec supports base class >
    bitvec_val = synthesizer.to_python(synthesizer.value)
    assert bitvec_val > 43, "{val} should be larger than 43, but it is not.".format(val=bitvec_val)
    synthesizer.reset_constraints()
    synthesizer.lt_constraint(25)  # BitVec supports base class <
    bitvec_val = synthesizer.to_python(synthesizer.value)
    assert bitvec_val < 25, "{val} should be smaller than 25, but it is not.".format(val=bitvec_val)
    synthesizer.reset_constraints()
    synthesizer.bounded_synthesis(upper_bound=40, lower_bound=25)
    bitvec_val = synthesizer.to_python(synthesizer.value)
    assert bitvec_val > 25, "{val} should be larger than 25, but it is not.".format(val=bitvec_val)
    assert bitvec_val < 40, "{val} should be smaller than than 40, but it is not.".format(val=bitvec_val)

    # Define a hash function
    def shr32(v, *, n):
        """v must be of Z3's BitVec type to support >> and <<."""
        return (v >> n) & ((1 << (32 - n)) - 1)

    synthesizer.reset_constraints()
    synthesizer.eq_constraint(shr32, 0x3E345C, n=2)
    bitvec_val = synthesizer.to_python(synthesizer.value)
    assert bitvec_val == 16306544, "{val} should be equal to 16306544, but it is not.".format(val=bitvec_val)
