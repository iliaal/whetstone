def first_even(nums):
    """First even number in nums, or None if there is none."""
    for n in nums:
        if n % 2 == 0:
            return n
    return None
