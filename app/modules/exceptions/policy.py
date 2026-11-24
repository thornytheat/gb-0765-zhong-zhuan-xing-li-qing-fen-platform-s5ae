
def verdict(planned_state, wrong_legs, uncertainty):
    if uncertainty or planned_state == 'CONFLICT' or (planned_state == 'LOADED' and wrong_legs):
        return 'pending', 'MULTI_LOADED' if planned_state == 'LOADED' and wrong_legs else 'UNCERTAIN'
    if planned_state == 'LOADED':
        return 'loaded', None
    if planned_state == 'OFFLOADED':
        return 'not_loaded', 'OFFLOADED'
    return 'pending', 'NO_LOAD'
