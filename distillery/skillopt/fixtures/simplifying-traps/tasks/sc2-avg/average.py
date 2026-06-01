def mean_or_zero(nums):
    """Arithmetic mean of nums, or 0 for an empty list."""
    if not nums:
        return 0
    total = 0
    for n in nums:
        total += n
    return total / len(nums)
