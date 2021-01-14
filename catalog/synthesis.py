"""Synthesis classes"""
from z3 import Solver, sat
from z3 import String, StringVal, Concat
from z3 import Re, InRe, Union, Star, Plus
from z3 import Int
from z3 import BitVec
from z3 import And, Or, If

from django.core.untrustedtypes import UntrustedInt, UntrustedStr


class Synthesizer(object):
    """Synthesis base class."""
    def __init__(self, symbol):
        self.solver = Solver()
        self.var = symbol

    def lt_constraint(self, values, **kwargs):
        """Add to solver a less-than constraint: values can be
        a single value or a *list* of values: for v in values,
        self.var < v. By default, we assume that the type
        of the values can be handled by Z3 directly with <, such
        as list of integer, but this is not always the case. In some
        cases like string, this function should be overridden."""
        if isinstance(values, list):
            for v in values:
                self.solver.add(self.var < v)
        else:
            self.solver.add(self.var < values)

    def gt_constraint(self, values, **kwargs):
        """Add to solver a greater-than constraint: values can
        be a single value or a *list* of values: for v in
        values, self.var > v. By default, we assume that the type
        of the values can be handled by Z3 directly with >, such
        as integer, but this is not always the case. In some
        cases like string, this function should be overridden."""
        if isinstance(values, list):
            for v in values:
                self.solver.add(self.var > v)
        else:
            self.solver.add(self.var > values)

    def eq_constraint(self, func, value, **kwargs):
        """Add to solver an equal-to constraints:
        func(self.var, **kwargs) == value. Note that
        func can be any custom function but operations
        in func must be supported by the Z3 variable
        type. For example, Z3's Int() does not support
        << (bit shift); therefore, func cannot have
        operations that use << to manipulate Int() variable.
        func can take any number of *keyed* arguments
        but the first argument (required, non-keyed)
        must be the value to be synthesized. In summary,
        not all func can be supported for synthesis!

        Note that func can return self.var itself to
        create a trivial equal-to constraint."""
        self.solver.add(func(self.var, **kwargs) == value)

    def le_constraint(self, values, **kwargs):
        """Add to solver a less-than-or-equal-to constraint:
        values can be a single value or a *list* of values:
        for v in values, self.var < v. By default, we assume that
        the type of the values can be handled by Z3 directly with <=,
        such as list of integer, but this is not always the case.
        In some cases like string, this function should be overridden."""
        if isinstance(values, list):
            for v in values:
                self.solver.add(self.var <= v)
        else:
            self.solver.add(self.var <= values)

    def ge_constraint(self, values, **kwargs):
        """Add to solver a greater-than-or-equal-to constraint:
        values can be a single value or a *list* of values: for v in
        values, self.var >= v. By default, we assume that the type
        of the values can be handled by Z3 directly with >=, such
        as integer, but this is not always the case. In some
        cases like string, this function should be overridden."""
        if isinstance(values, list):
            for v in values:
                self.solver.add(self.var >= v)
        else:
            self.solver.add(self.var >= values)

    def bounded_constraints(self, upper_bound, lower_bound, **kwargs):
        """Add to solver constraints derived from an upper bound and
        a lower bound (not inclusive), both of which must exist (if
        not, call either lt_constraint() or gt_constraint() instead).
        Subclass can override this function if the synthesizer
        allows different bounded constraints. Note that this function
        is implemented mostly for convenience; In most cases, one can
        easily combine lt_constraint() and gt_constraint() to create
        the same bounded constraints. In some cases like string,
        however, this function should be overridden."""
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
        UntrustedInt) depend on the type of _var.
        Returns None if value is None."""
        raise NotImplementedError("to_python() is not overridden in <{subclass}>, "
                                  "subclassed from <{superclass}>.".
                                  format(subclass=self.__class__.__name__,
                                         superclass=type(self).__base__.__name__))

    def bounded_synthesis(self, *, upper_bound=None, lower_bound=None, **kwargs):
        """Synthesis based on an upper and a lower bound (not inclusive),
        both of which must exist! The data type of upper_bound and
        lower_bound must be able to be compared and upper_bound
        must be larger than lower_bound. Subclasses can override
        bounded_constraints() and call this function
        as public API. bounded_constraints() can also raise
        ValueError if given bounds are not valid. A synthesized
        value is returned if synthesis is successful; otherwise,
        we return None."""
        if not upper_bound or not lower_bound:
            raise ValueError("Two bounds must be specified. Perhaps use a different"
                             "synthesis method or simply call random()?")
        if upper_bound <= lower_bound:
            raise ValueError("The upper bound should at least "
                             "be larger than the lower bound.")
        self.bounded_constraints(upper_bound, lower_bound, **kwargs)
        if self.value is not None:
            return self.to_python(self.value)
        else:
            return None

    def simple_synthesis(self, value):
        """Synthesis by simply wrapping value in an Untrusted type
        (e.g., wrap Int to UntrustedInt) and set the type's
        synthesized flag to True. Returns None if value is None."""
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
        if value is not None:
            return UntrustedInt(value.as_long(), synthesized=True)
        else:
            return None

    def simple_synthesis(self, value):
        if value is not None:
            return UntrustedInt(value, synthesized=True)
        else:
            return None


class BitVecSynthesizer(Synthesizer):
    """Synthesize bit vector value, subclass from Synthesizer."""
    def __init__(self, bits=32):
        """Create a bit-vector variable in Z3
        named b with given (32 by default) bits."""
        super().__init__(BitVec('b', bits))

    def to_python(self, value):
        if value is not None:
            return UntrustedInt(value.as_long(), synthesized=True)
        else:
            return None

    def simple_synthesis(self, value):
        """Python can automatically convert a bit vector to int."""
        if value is not None:
            return UntrustedInt(value, synthesized=True)
        else:
            return None


def printable_ascii_chars():
    """Returns an order string of printable ASCII
    characters we use from 0x20 (space) to 0x7E (~)"""
    chars = str()
    for i in range(32, 127):
        chars += chr(i)
    return chars


class StrSynthesizer(Synthesizer):
    """Synthesize a string value, subclass from Synthesizer."""
    # All default possible characters in a synthesized string (printable ASCII)
    DEFAULT_ASCII_CHARS = printable_ascii_chars()
    # The maximum possible length of a synthesized string
    DEFAULT_MAX_CHAR_LENGTH = 50

    def __init__(self, charset=None):
        super().__init__(String("var"))
        if not charset:
            # Create a default character set
            # (always add upper-case chars first)
            charset = self.DEFAULT_ASCII_CHARS
        self._charset = charset     # String representation
        self._chars = Union([Re(StringVal(c)) for c in self._charset])      # Z3 union representation

    @property
    def value(self):
        """Return synthesized variable values (Z3 type) if
        the model can be satisfied; otherwise returns None.
        This property overrides base class value property
        because eq_constraint() might add new Z3 variables
        to the solver, so we cannot simply inherit from base.
        This function either returns a single Z3 String-typed
        value or a list of Z3 Int-typed value [x0, x1...],
        where x0 is the byte value of the first character,
        x1 is the byte value of the second character, etc."""
        if self.is_satisfied():
            m = dict()                      # Store variable name (str) -> Z3 value
            model = self.solver.model()
            for var in model:
                m[var.name()] = model[var]
            if "var" in m:                  # The model contains only our String variable
                return m["var"]
            else:                           # The model contains Int variables
                # Returns an ordered (starting from x0) list of Int values
                return [m['x%s' % i] for i in range(self.DEFAULT_MAX_CHAR_LENGTH)]
        else:
            return None

    def lt_constraint(self, value, **kwargs):
        """Override base class lt_constraint(). We find the first character
        in value that has a smaller character and replace it with a smaller
        character picked by Z3. Every character before that would be the same
        as value and every character after that, if exists, is picked by Z3.
        If every character in value is the smallest character in charset, we
        try to remove the last character in value and use a shorter string.
        If there is no string smaller than value, an empty string is returned.
        The constraint is a regular expression template added to the solver.
        If value is an empty string, the synthesis will always fail!
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
            # For an empty string value, we add
            # False so synthesis always return 'unsat'.
            self.solver.add(False)
        else:
            template = self._lt_constraint(value, **kwargs)
            self.solver.add(InRe(self.var, template))

    def le_constraint(self, value, **kwargs):
        """The same rules as in lt_constraint() except that
        the synthesized string can be the same as value."""
        lt_template = self._lt_constraint(value, **kwargs)
        eq_template = Re(StringVal(value))
        self.solver.add(Or(InRe(self.var, lt_template), InRe(self.var, eq_template)))

    def _lt_constraint(self, value, **kwargs):
        """Helper function for lt_constraint(). Returns the template
        to synthesize a string (or ValueError). See lt_constraint()
        for more detailed description. User should always call
        lt_constraint() as the public API, but not this function.

        value should never be an empty string in this function."""
        if isinstance(value, UntrustedStr):
            # Get str type value if value is UntrustedStr
            value = value.data
        # Create a regular expression template for synthesis
        bound_length = len(value)
        offset = 0
        if "offset" in kwargs:
            offset = kwargs["offset"]
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
        return template

    def gt_constraint(self, value, **kwargs):
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
        template = self._gt_constraint(value, **kwargs)
        self.solver.add(InRe(self.var, template))

    def ge_constraint(self, value, **kwargs):
        """The same rules as in gt_constraint() except that
        the synthesized string can be the same as value."""
        gt_template = self._gt_constraint(value, **kwargs)
        eq_template = Re(StringVal(value))
        self.solver.add(Or(InRe(self.var, gt_template), InRe(self.var, eq_template)))

    def _gt_constraint(self, value, **kwargs):
        """Helper function for gt_constraint(). Returns the template
        to synthesize a string (or ValueError). See gt_constraint()
        for more detailed description. User should always call
        gt_constraint() as the public API, but not this function."""
        if isinstance(value, UntrustedStr):
            # Get str type value if value is UntrustedStr
            value = value.data
        bound_length = len(value)
        if bound_length == 0:
            # If value is an empty string, any non-empty string will do
            empty_char = Re(StringVal(""))
            template = Concat(empty_char, Plus(self._chars))
        else:
            offset = 0
            if "offset" in kwargs:
                offset = kwargs["offset"]
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
        return template

    def eq_constraint(self, func, value, **kwargs):
        """The synthesized string is represented by a list of bytes (integers of ASCII)
        and the func used must take a list of integers as its first positional parameter."""
        # We use Z3's list comprehension to create a list of Z3 Int() variables
        chars = [Int('x%s' % i) for i in range(self.DEFAULT_MAX_CHAR_LENGTH)]
        for char in chars:
            # 0 is the NULL character
            # 32 is the smallest printable ASCII value
            # 126 is the largest printable ASCII value
            self.solver.add(Or(char == 0, And(char >= 32, char <= 126)))
        # The character string must be well-formed, therefore, if
        # a character is set to be NULL (0), then the character in
        # front of it must be NULL as well.
        for i in range(len(chars) - 1):
            self.solver.add(If(chars[i+1] == 0, chars[i] == 0, True))
        self.solver.add(func(chars, **kwargs) == value)

    def bounded_constraints(self, upper_bound, lower_bound, **kwargs):
        """We cannot simply add lt_constraint() and gt_constraint() without
        specifying a common offset. Otherwise, it is possible that the template
        generated by lt_constraint() becomes incompatible with the template
        generated by gt_constraint() (so no string can be synthesized) even if it
        is lexicographically possible to synthesize a string between the two bounds."""
        upper_bound_length = len(upper_bound)
        lower_bound_length = len(lower_bound)
        bound_length = min(upper_bound_length, lower_bound_length)
        pos = 0
        while pos < bound_length:
            if upper_bound[pos] == lower_bound[pos]:
                pos += 1
            else:
                break
        self.lt_constraint(upper_bound, offset=pos)
        self.gt_constraint(lower_bound, offset=pos)

    def to_python(self, value):
        if value is not None:
            if isinstance(value, list):
                # Reconstruct a string from a list of Z3 Int ASCII values
                reconstruct_str = str()
                for i in range(self.DEFAULT_MAX_CHAR_LENGTH):
                    # Only use non-null characters
                    if value[i].as_long() > 0:
                        # chr converts integer to ASCII character
                        reconstruct_str += chr(value[i].as_long())
                return UntrustedStr(reconstruct_str, synthesized=True)
            else:
                return UntrustedStr(value.as_string(), synthesized=True)
        else:
            return None

    def simple_synthesis(self, value):
        if value is not None:
            return UntrustedStr(value, synthesized=True)
        else:
            return None


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
    synthesizer.lt_constraint([34, 45, -3])
    int_val = synthesizer.to_python(synthesizer.value)
    assert int_val < -3, "{val} should be smaller than than -3, but it is not.".format(val=int_val)
    synthesizer.reset_constraints()
    synthesizer.gt_constraint(21)
    int_val = synthesizer.to_python(synthesizer.value)
    assert int_val > 7, "{val} should be larger than 21, but it is not.".format(val=int_val)
    synthesizer.reset_constraints()
    synthesizer.gt_constraint([21, 100, -45])
    int_val = synthesizer.to_python(synthesizer.value)
    assert int_val > 100, "{val} should be larger than 100, but it is not.".format(val=int_val)

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
    assert str_val < "A", "{val} should be smaller than 'A', but it is not.".format(val=str_val)
    synthesizer.reset_constraints()
    synthesizer.lt_constraint("AA")
    str_val = synthesizer.to_python(synthesizer.value)
    assert str_val < "AA", "{val} should be smaller than 'AA', but it is not.".format(val=str_val)
    synthesizer.reset_constraints()
    synthesizer.lt_constraint("Jack")
    str_val = synthesizer.to_python(synthesizer.value)
    assert str_val < "Jack", "{val} should be smaller than than 'Jack', but it is not.".format(val=str_val)
    synthesizer.reset_constraints()
    synthesizer.lt_constraint("Adam")
    str_val = synthesizer.to_python(synthesizer.value)
    assert str_val < "Adam", "{val} should be smaller than 'Adam', but it is not.".format(val=str_val)
    synthesizer.reset_constraints()
    synthesizer.lt_constraint("")
    str_val = synthesizer.to_python(synthesizer.value)
    assert str_val is None, "{val} should be None, but it is not.".format(val=str_val)
    synthesizer.reset_constraints()
    synthesizer.gt_constraint("z")
    str_val = synthesizer.to_python(synthesizer.value)
    assert str_val > "z", "{val} should be larger than 'z', but it is not.".format(val=str_val)
    synthesizer.reset_constraints()
    synthesizer.gt_constraint("")
    str_val = synthesizer.to_python(synthesizer.value)
    assert str_val > "", "{val} should be larger than '', but it is not.".format(val=str_val)
    synthesizer.reset_constraints()
    synthesizer.gt_constraint("Jack")
    str_val = synthesizer.to_python(synthesizer.value)
    assert str_val > "Jack", "{val} should be larger than 'Jack', but it is not.".format(val=str_val)
    synthesizer.reset_constraints()
    synthesizer.gt_constraint("zza")
    str_val = synthesizer.to_python(synthesizer.value)
    assert str_val > "zza", "{val} should be larger than 'zza', but it is not.".format(val=str_val)
    synthesizer.reset_constraints()
    synthesizer.le_constraint("")
    str_val = synthesizer.to_python(synthesizer.value)
    assert str_val <= "", "{val} should be smaller than or equal to '', but it is not.".format(val=str_val)
    synthesizer.reset_constraints()
    synthesizer.le_constraint("A")
    str_val = synthesizer.to_python(synthesizer.value)
    assert str_val <= "A", "{val} should be smaller than or equal to 'A', but it is not.".format(val=str_val)
    synthesizer.reset_constraints()
    synthesizer.ge_constraint("zza")
    str_val = synthesizer.to_python(synthesizer.value)
    assert str_val >= "zza", "{val} should be larger than or equal to 'zza', but it is not.".format(val=str_val)
    synthesizer.reset_constraints()
    str_val = synthesizer.bounded_synthesis(upper_bound="zzzB", lower_bound="zzz")
    assert str_val < "zzzB", "{val} should be smaller than 'zzzB', but it is not.".format(val=str_val)
    assert str_val > "zzz", "{val} should be larger than 'zzz', but it is not.".format(val=str_val)
    synthesizer.reset_constraints()
    str_val = synthesizer.bounded_synthesis(upper_bound="Luke", lower_bound="Blair")
    assert str_val < "Luke", "{val} should be smaller than 'Luke', but it is not.".format(val=str_val)
    assert str_val > "Blair", "{val} should be larger than 'Blair', but it is not.".format(val=str_val)
    synthesizer.reset_constraints()
    untrusted_str = UntrustedStr("Luke")
    synthesizer.eq_constraint(UntrustedStr.custom_hash, untrusted_str.__hash__())
    str_val = synthesizer.to_python(synthesizer.value)
    assert str_val.__hash__() == untrusted_str.__hash__(), "{synthesized_val} should have the same hashed value " \
                                                           "as {val}".format(synthesized_val=str_val,
                                                                             val=untrusted_str)
    assert str_val.synthesized, "{val} should be synthesized.".format(val=str_val)

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
    assert bitvec_val < 40, "{val} should be smaller than 40, but it is not.".format(val=bitvec_val)

    # Define a hash function
    def shr32(v, *, n):
        """v must be of Z3's BitVec type to support >> and <<."""
        return (v >> n) & ((1 << (32 - n)) - 1)

    synthesizer.reset_constraints()
    synthesizer.eq_constraint(shr32, 0x3E345C, n=2)
    bitvec_val = synthesizer.to_python(synthesizer.value)
    assert shr32(bitvec_val, n=2) == 0x3E345C
