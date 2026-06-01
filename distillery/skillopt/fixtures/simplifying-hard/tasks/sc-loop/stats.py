def sum_even_squares(nums):
    """Sum the squares of the even numbers in nums."""
    total = 0
    for n in nums:
        if n % 2 == 0:
            total = total + n * n
    return total
