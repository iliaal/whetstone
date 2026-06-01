def shipping_cost(weight, country, express):
    """Base 5; +10 if international; +20 if express; free when weight == 0."""
    if weight > 0:
        if country == "US":
            if express:
                return 25
            else:
                return 5
        else:
            if express:
                return 35
            else:
                return 15
    else:
        return 0
