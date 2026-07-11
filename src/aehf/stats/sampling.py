import math


def wilson_interval(successes:int, n:int, z: float=1.96 ) -> tuple[float,float]:
    if n == 0:
        raise ValueError('no of runs can not be zero')
        

    p_cap = successes / n 
    

    center = (p_cap + (z**2 / (2 * n))) / (1 + ((z**2) / n))
    

    half_width = (z * math.sqrt((p_cap * (1 - p_cap) / n) + (z**2 / (4 * n**2)))) / (1 + ((z**2) / n))
    

    return (center - half_width, center + half_width)
