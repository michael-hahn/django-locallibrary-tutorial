"""Synthesis classes"""
from z3 import Solver, sat
from z3 import String, StringVal, Length, SubSeq, Concat
from z3 import Re, InRe, Union, Star, Plus
from z3 import Int

from django.core.untrustedtypes import UntrustedInt, UntrustedStr


class Synthesizer(object):
    """Synthesis base class."""
    def __init__(self, symbol):
        self.solver = Solver()
        self.var = symbol

    def _bounded_constraints(self, upper_bound, lower_bound, **kargs):
        """Add to solver constraints derived from an upper bound and
        a lower bound, either of which can be optional, but not both.
        Subclass should implement this function if the synthesizer
        allows bounded constraints but it should not call this function
        directly; instead, subclass should call bounded_synthesis()."""
        raise NotImplementedError("It seems like <{subclass}> does not support "
                                  "synthesis through bounds because it is not "
                                  "overridden.".format(subclass=self.__class__.__name__))

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
        """Synthesis based on an upper and a lower bound, either
        of which can be optional, but not both! The date type of
        upper_bound and lower_bound must be able to be compared
        and upper_bound must be larger than lower_bound. Subclasses
        must override _bounded_constraints() and call this function
        as public API. __bounded_constraints() can also raise
        ValueError if given bounds are not valid. A synthesized
        value is returned if synthesis is successful; otherwise,
        we return None."""
        if not upper_bound and not lower_bound:
            raise ValueError("No bounds are specified. Perhaps use a different"
                             "synthesis method or simply call random()?")
        if upper_bound and lower_bound and upper_bound <= lower_bound:
            raise ValueError("The upper bound should at least "
                             "be larger than the lower bound.")
        self._bounded_constraints(upper_bound, lower_bound, **kargs)
        if self.value is not None:
            return self.to_python(self.value)
        else:
            return None

    def reset_constraints(self):
        self.solver.reset()


class IntSynthesizer(Synthesizer):
    """Synthesize integer value, subclass from Synthesizer."""
    def __init__(self):
        super().__init__(Int('var'))

    def _bounded_constraints(self, upper_bound, lower_bound, **kargs):
        """upper_bound and lower_bound must be integers if given.
        Assume that at least one of the bounds must exists."""
        if upper_bound:
            self.solver.add(self.var < upper_bound)
        if lower_bound:
            self.solver.add(self.var > lower_bound)

    def to_python(self, value):
        return UntrustedInt(value.as_long(), synthesized=True)


class StrSynthesizer(Synthesizer):
    """Synthesize string value, subclass from Synthesizer."""
    def __init__(self):
        super().__init__(String("var"))

    def _bounded_constraints(self, upper_bound, lower_bound, **kargs):
        """upper_bound and lower_bound must be strings if given.
        Assume that at least one of the bounds must exist.
        Raise exceptions if nothing can be synthesized between
        the upper and the lower bound (mostly because bounds are
        not valid values).

        An optional keyed parameter "charset" takes a string of
        all possible characters available for synthesis. e.g.,
        charset="abc". """
        # Possible characters to generate a synthesized string
        if "charset" not in kargs:
            charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"  # upper-case
            charset += "abcdefghijklmnopqrstuvwxyz"  # lower-case
        else:
            charset = kargs["charset"]
        chars = Union([Re(StringVal(c)) for c in charset])

        from random import randint
        # Create a regular expression template for synthesis
        # Case 1: if only the lower bound is provided
        if lower_bound and not upper_bound:
            bound_length = len(lower_bound)
            # The length of our synthesized string is
            # the length of the lower bound + 1
            self.solver.add(Length(self.var) == bound_length + 1)
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
                raise ValueError("lower-bound string '{lower}' contains a character "
                                 "'{character}' that is not found in the charset "
                                 "'{charset}'.".format(lower=lower_bound,
                                                       character=bound_char,
                                                       charset=charset))
            elif bound_pos >= len(charset) - 1:
                # If bound_char is the biggest possible in charset
                while bound_pos >= len(charset) - 1 and offset < bound_length:
                    # Go to the next character until we are no longer able to
                    # because we are at the last character of the bound string
                    bound_char = lower_bound[offset]
                    bound_pos = charset.find(bound_char)
                    if bound_pos < 0:
                        return ValueError("lower-bound string '{lower}' contains a character "
                                          "'{character}' that is not found in the charset "
                                          "'{charset}'.".format(lower=lower_bound,
                                                                character=bound_char,
                                                                charset=charset))
                    offset += 1
            if offset == bound_length:
                # We cannot find any usable character in bound string
                # This is OK because we always add a new character at
                # the end of our synthesized string anyways.
                # So the first part of our synthesized string looks
                # just like the bound string.
                template = Concat(Re(StringVal(lower_bound[:offset])), Plus(chars))
            else:
                # We can find (randomly) a larger character
                synthesized_char = charset[randint(bound_pos + 1, len(charset) - 1)]
                char = Re(StringVal(synthesized_char))
                template = Concat(Re(StringVal(lower_bound[:offset])), char, Star(chars))
        # Case 2: if only the upper bound is provided. We follow
        #         the opposite to Case 1, with some differences
        elif upper_bound and not lower_bound:
            bound_length = len(upper_bound)
            # The length of our synthesized string is
            # the length of the upper bound - 1 unless
            # the length of the upper bound is 1
            if bound_length == 1:
                # Find the position of the only character in the bound string
                bound_pos = charset.find(upper_bound[0])
                if bound_pos < 0:
                    # If not found, charset is not given correctly.
                    raise ValueError("upper-bound string '{upper}' contains a character "
                                     "'{character}' that is not found in the charset "
                                     "'{charset}'.".format(upper=upper_bound,
                                                           character=upper_bound[0],
                                                           charset=charset))
                elif bound_pos == 0:
                    # If it is already the smallest that can be, we simply have no options.
                    raise ValueError("There is nothing smaller than the "
                                     "upper-bound string '{upper}'.".format(upper=upper_bound))
                else:
                    # synthesized_char is the final synthesis string
                    synthesized_char = charset[randint(0, bound_pos - 1)]
                    char = Re(StringVal(synthesized_char))
                    template = Concat(char)
            else:
                # The length of our synthesized string
                # is the length of the upper bound - 1.
                self.solver.add(Length(self.var) == bound_length - 1)
                offset = randint(0, bound_length - 2)
                bound_char = upper_bound[offset]
                bound_pos = charset.find(bound_char)
                if bound_pos < 0:
                    raise ValueError("upper-bound string '{upper}' contains a character "
                                     "'{character}' that is not found in the charset "
                                     "'{charset}'.".format(upper=upper_bound,
                                                           character=upper_bound[0],
                                                           charset=charset))
                elif bound_pos == 0:
                    # If bound_char is the smallest possible in charset
                    while bound_pos == 0 and offset < bound_length - 1:
                        # Go to the next character until we are no longer
                        # able to because we are at the last character
                        # of the bound string
                        bound_char = upper_bound[offset]
                        bound_pos = charset.find(bound_char)
                        if bound_pos < 0:
                            raise ValueError("upper-bound string '{upper}' contains a character "
                                             "'{character}' that is not found in the charset "
                                             "'{charset}'.".format(upper=upper_bound,
                                                                   character=upper_bound[0],
                                                                   charset=charset))
                        offset += 1
                if offset == bound_length - 1:
                    # We cannot find any usable character in bound string
                    # This is OK because our synthesized string already has
                    # one fewer character anyways. So the first part of our
                    # synthesized string looks just like the bound string.
                    template = Concat(Re(StringVal(upper_bound[:offset])))
                else:
                    # We can find (randomly) a smaller character
                    synthesized_char = charset[randint(0, bound_pos - 1)]
                    char = Re(StringVal(synthesized_char))
                    template = Concat(Re(StringVal(upper_bound[:offset])), char, Star(chars))
        # Case 3: if both bounds are provided
        elif upper_bound and lower_bound:
            # Note that there must exist a valid string between
            # the upper and the lower bound; otherwise, the data
            # structure itself must have been ill-formed!
            upper_bound_length = len(upper_bound)
            lower_bound_length = len(lower_bound)
            bound_length = min(upper_bound_length, lower_bound_length)
            # The first "offset" characters are the same
            # between both upper and lower bound strings
            offset = 0
            while offset < bound_length and upper_bound[offset] == lower_bound[offset]:
                offset += 1
            # Case A: offset is smaller than both
            #         upper and lower bound length
            if offset < bound_length:
                # We can set our synthesized string
                # to be the same as the bound length
                self.solver.add(Length(self.var) == bound_length)
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
                self.solver.add(Length(self.var) == upper_bound_length)
                # The character after the first offset
                # characters should be smaller than
                # upper bound character
                upper_bound_char = upper_bound[offset]
                upper_bound_pos = charset.find(upper_bound_char)
                if upper_bound_pos < 0:
                    raise ValueError("upper-bound string '{upper}' contains a character "
                                     "'{character}' that is not found in the charset "
                                     "'{charset}'.".format(upper=upper_bound,
                                                           character=upper_bound_char,
                                                           charset=charset))
                elif upper_bound_pos == 0:
                    # If the upper_bound_char is the smallest possible
                    while upper_bound_pos == 0 and offset < upper_bound_length:
                        # Go to the next character until we are no longer able to
                        # because we are at the last character of the bound string
                        upper_bound_char = upper_bound[offset]
                        upper_bound_pos = charset.find(upper_bound_char)
                        if upper_bound_pos < 0:
                            raise ValueError("upper-bound string '{upper}' contains a character "
                                             "'{character}' that is not found in the charset "
                                             "'{charset}'.".format(upper=upper_bound,
                                                                   character=upper_bound_char,
                                                                   charset=charset))
                        offset += 1
                    if offset == upper_bound_length:
                        # We cannot find any usable character in bound string,
                        # because there is nothing in between the upper and lower bound.
                        raise ValueError("There is nothing between the upper-bound string '{upper}' "
                                         "and the lower-bound string '{lower}'.".format(upper=upper_bound,
                                                                                        lower=lower_bound))
                synthesized_char = charset[randint(0, upper_bound_pos - 1)]

            char = Re(StringVal(synthesized_char))
            template = Concat(Re(StringVal(lower_bound[:offset])), char, Star(chars))
        # We should never reach this branch!
        else:
            raise AssertionError("This branch should never be reached!")

        # Our synthesized string should match the template
        self.solver.add(InRe(self.var, template))

    def to_python(self, value):
        return UntrustedStr(value.as_string(), synthesized=True)


if __name__ == "__main__":
    synthesizer = IntSynthesizer()
    int_val = synthesizer.bounded_synthesis(upper_bound=92, lower_bound=7)
    assert int_val > 7, "{val} should be larger than 7, but it is not.".format(val=int_val)
    assert int_val < 92, "{val} should be smaller than than 92, but it is not.".format(val=int_val)
    synthesizer.reset_constraints()
    int_val = synthesizer.bounded_synthesis(upper_bound=34)
    assert int_val < 34, "{val} should be smaller than than 34, but it is not.".format(val=int_val)
    synthesizer.reset_constraints()
    int_val = synthesizer.bounded_synthesis(lower_bound=21)
    assert int_val > 7, "{val} should be larger than 21, but it is not.".format(val=int_val)

    synthesizer = StrSynthesizer()
    str_val = synthesizer.bounded_synthesis(upper_bound="Jack")
    assert str_val < "Jack", "{val} should be smaller than than 'Jack', but it is not.".format(val=str_val)
    synthesizer.reset_constraints()
    str_val = synthesizer.bounded_synthesis(lower_bound="Daniel")
    assert str_val > "Daniel", "{val} should be larger than 'Daniel', but it is not.".format(val=str_val)
    synthesizer.reset_constraints()
    str_val = synthesizer.bounded_synthesis(lower_bound="zzz")
    assert str_val > "zzz", "{val} should be larger than 'zzz', but it is not.".format(val=str_val)
    synthesizer.reset_constraints()
    str_val = synthesizer.bounded_synthesis(upper_bound="zzzB", lower_bound="zzz")
    assert str_val == "zzzA", "{val} should be the same as 'zzzA', but it is not.".format(val=str_val)

