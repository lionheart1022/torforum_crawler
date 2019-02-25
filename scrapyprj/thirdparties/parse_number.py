"""
parse_number.py

Utilities for parsing English numbers into integers.

Author: pmdboi @ reddit (see
<http://www.reddit.com/r/Python/comments/hv8rp/can_anyone_suggest_a_library_for_converting/>)
"""

import re

SINGLE_WORD_NUMBERS = {}
for i, word in zip(xrange(0, 20+1),
        '''zero one two three four five six seven eight nine ten eleven twelve
        thirteen fourteen fifteen sixteen seventeen eighteen nineteen
        twenty'''.split()):
    SINGLE_WORD_NUMBERS[word] = i
for i, word in zip(xrange(30, 100+1, 10),
        '''thirty forty fifty sixty seventy eighty ninety hundred'''.split()):
    SINGLE_WORD_NUMBERS[word] = i
for i, word in zip(xrange(3, 24+1, 3),
        '''thousand million billion trillion quadrillion quintillion sextillion
        septillion'''.split()):
    SINGLE_WORD_NUMBERS[word] = 10**i

def tokenize_number(s):
    """
    Return the list of numbers corresponding to words that appear in an English
    number.

    >>> tokenize_number('twenty-nine')
    [20, 9]
    >>> tokenize_number('one hundred and five')
    [1, 100, 5]
    >>> tokenize_number('two hundred and bleen')
    Traceback (most recent call last):
      File "<stdin>", line 1
    ValueError: unrecognized word 'bleen'
    """
    # split on dash, space, comma-space
    words = re.split(r'-|,?\s+', s.lower())
    try:
        return [SINGLE_WORD_NUMBERS[word] for word in words if word != 'and']
    except KeyError, e:
        raise ValueError, 'unrecognized word %r' % e.args[0]

def coalesce_tokens(tokens):
    """
    Combine tokens that are part of the same sub-1000 number portion.

    >>> coalesce_tokens([20, 9, 1000, 300, 40, 2])
    [29, 1000, 342]
    >>> coalesce_tokens([1, 100, 5])
    [105]
    >>> coalesce_tokens([100])
    [100]
    >>> coalesce_tokens([1000000, 2, 100, 1000, 40, 7])
    [1000000, 200, 1000, 47]
    """
    result = []
    for token in tokens:
        if result and token == 100 and result[-1] < 100:
            result[-1] *= 100
        elif result and result[-1] < 1000 and token < 1000:
            result[-1] += token
        else:
            result.append(token)
    return result

def parse_number(s):
    """
    Return the integer corresponding to an English number, or raise ValueError
    if it couldn't be parsed.

    >>> parse_number('twenty-nine')
    29
    >>> parse_number('one hundred and five')
    105
    >>> parse_number('one million two hundred thousand and forty-seven')
    1200047
    >>> parse_number('thirteen hundred') # not correct strictly speaking
    1300
    >>> parse_number('two hundred and bleen')
    Traceback (most recent call last):
      ...
    ValueError: unrecognized word 'bleen'
    """
    tokens = coalesce_tokens(tokenize_number(s))
    total = 0
    while tokens:
        if len(tokens) == 1 or tokens[0] >= 1000:
            total += tokens.pop(0)
        else:
            assert tokens[1] >= 1000    # bad english otherwise?
            total += tokens[0] * tokens[1]
            del tokens[:2]
    return total

if __name__ == '__main__':
    import doctest
    doctest.testmod()