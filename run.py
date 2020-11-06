import requests
from pprint import pprint

url = 'http://localhost:8000'

TOP = 25
MAX_CAPACITY = 8

DIRECTIONS = {
    "DOWNWARD": 0,
    "UPWARD": 1,
    "STOPPED": 2,
    "OPENED": 3
}


def start(user, problem, count):
    uri = url + '/start' + '/' + user + '/' + str(problem) + '/' + str(count)
    return requests.post(uri).json()


def oncalls(token):
    uri = url + '/oncalls'
    return requests.get(uri, headers={'X-Auth-Token': token}).json()


def action(token, cmds):
    uri = url + '/action'

    return requests.post(uri, headers={'X-Auth-Token': token}, json={'commands': cmds}).json()


def schedule_call(call, elevators, elevators_info):
    #   1 find closest elevator that has same direction as call and is coming to call
    #   2 if no elevators found, find closest call which is stopped
    # FIRST CASE
    closest_elevator_id = None
    closest_distance = TOP

    for elevator in elevators:
        call_direction = "UPWARD" if call["start"] - \
            call["end"] > 0 else "DOWNWARD"
        elevator_direction = elevator["status"]
        schedule_possible = call_direction == elevator_direction

        call_floor = call["start"]
        floor = elevator["floor"]
        if call_direction == "UPWARD":
            if floor > call_floor:
                schedule_possible = False
        else:
            if floor < call_floor:
                schedule_possible = False

        if schedule_possible or elevator_direction == "STOPPED":
            if len(elevators_info[elevator["id"]]["calls"]) >= MAX_CAPACITY:
                continue
            if closest_distance > abs(elevator["floor"] - call["start"]):
                closest_distance = abs(elevator["floor"] - call["start"])
                closest_elevator_id = elevator["id"]

    if closest_elevator_id != None:
        elevators_info[closest_elevator_id]["calls"].append(call)
        return True

    return False


def is_stop(floor, calls, standard):
    # floor : int
    # calls : list of calls {id: int, timestamp: int, start: int, end: int}
    # standard : ["start" | "end"]
    ret_arr = []
    ret = False
    for call in calls:
        if floor == call[standard]:
            ret = True
            ret_arr.append(call["id"])
    return ret, ret_arr


def free_schedule(exit_arr, scheduled_calls):
    for each_call in exit_arr:
        for each_schedule_call in scheduled_calls:
            if each_schedule_call["id"] == each_call:
                try:
                    scheduled_calls.remove(each_schedule_call)
                except:
                    print(each_schedule_call)
                    raise


def free_cache(exit_arr, cache):
    for call in exit_arr:
        cache[call] = False


def find_next_move(floor, passengers, calls):
    ret = None
    if passengers:
        if passengers[0]["end"] > floor:
            ret = "UP"
        else:
            ret = "DOWN"
    elif calls:
        if calls[0]["start"] > floor:
            ret = "UP"
        else:
            ret = "DOWN"
    else:
        ret = "STOP"
    return ret


def p0_simulator():
    user = 'TG'
    problem = 2
    count = 4

    ret = start(user, problem, count)
    token = ret['token']
    print('Token for %s is %s' % (user, token))

    calls_cache = dict()
    elevators_info = dict()

    while True:
        # GET & PARSE INFO
        ret = oncalls(token)
        is_end = ret["is_end"]
        if is_end:
            break
        calls = ret["calls"]
        elevators = ret["elevators"]

        # MAKE ADDITIONAL NEEDED ELEVATOR INFO
        for elevator in elevators:
            if elevator["id"] not in elevators_info:
                elevators_info[elevator["id"]] = {
                    "calls": [],
                    "is_entered": False, "is_exit": False}

        # delete duplicated calls
        call_id_set = set()
        tmp = []
        for call in calls:
            call_id = call["id"]
            if call_id in call_id_set:
                continue
            call_id_set.add(call_id)
            tmp.append(call)
        calls = tmp

        # SCHEDULING CALLS
        for call in calls:
            call_id = call["id"]
            if call_id in calls_cache and calls_cache[call_id]:
                continue
            is_scheduled = schedule_call(call, elevators, elevators_info)
            if is_scheduled:
                calls_cache[call_id] = True

        # FIND ACTION
        next_actions = []
        for elevator in elevators:
            elevator_id = elevator["id"]
            status = elevator["status"]
            elevator_floor = elevator["floor"]
            passengers = elevator["passengers"]
            scheduled_calls = elevators_info[elevator_id]["calls"]
            extra_info = elevators_info[elevator_id]

            next_action = {}
            next_action['elevator_id'] = elevator_id

            def need_to_enter(passengers, calls):
                for call in calls:
                    for passenger in passengers:
                        if call["id"] == passenger["id"]:
                            return False
                return True
            if status == "STOPPED":
                enter_need = need_to_enter(passengers, scheduled_calls)
                if not passengers and not scheduled_calls:
                    next_action['command'] = "STOP"
                elif (enter_need and is_stop(elevator_floor, scheduled_calls, "start")[0] and not extra_info["is_entered"]) or (is_stop(elevator_floor, passengers, "end")[0] and not extra_info["is_exit"]):
                    next_action["command"] = "OPEN"
                else:
                    next_action["command"] = find_next_move(
                        elevator_floor, passengers, scheduled_calls)

            elif status == "OPENED":
                exit, exit_arr = is_stop(elevator_floor, passengers, "end")
                enter, enter_arr = is_stop(
                    elevator_floor, scheduled_calls, "start")
                enter_need = need_to_enter(passengers, scheduled_calls)

                if exit and not extra_info["is_exit"]:
                    # EXIT
                    next_action["command"] = "EXIT"
                    next_action["call_ids"] = exit_arr
                    extra_info["is_exit"] = True

                    # FREE call id from cache
                    free_schedule(exit_arr, scheduled_calls)
                    #free_cache(exit_arr, calls_cache)
                elif enter and not extra_info["is_entered"] and enter_need:
                    # ENTER
                    next_action["command"] = "ENTER"
                    next_action["call_ids"] = enter_arr
                    extra_info["is_entered"] = True
                else:
                    next_action["command"] = "CLOSE"
            elif status == "UPWARD":
                exit, _ = is_stop(elevator_floor, passengers, "end")
                enter, _ = is_stop(elevator_floor, scheduled_calls, "start")
                enter_need = need_to_enter(passengers, scheduled_calls)
                extra_info["is_exit"] = False
                extra_info["is_entered"] = False

                if exit or (enter and enter_need):
                    next_action["command"] = "STOP"

                else:
                    next_action["command"] = find_next_move(
                        elevator_floor, passengers, scheduled_calls)

            elif status == "DOWNWARD":
                exit, _ = is_stop(elevator_floor, passengers, "end")
                enter, _ = is_stop(elevator_floor, scheduled_calls, "start")
                enter_need = need_to_enter(passengers, scheduled_calls)
                extra_info["is_exit"] = False
                extra_info["is_entered"] = False

                if exit or (enter and enter_need):
                    next_action["command"] = "STOP"

                else:
                    next_action["command"] = find_next_move(
                        elevator_floor, passengers, scheduled_calls)

            next_actions.append(next_action)

        # debugging
        print("="*10)
        print("calls")
        pprint(calls)
        print("elevator")
        pprint(elevators)
        print("info")
        pprint(elevators_info)
        print("actions")
        pprint(next_actions)

        action(token, next_actions)


if __name__ == '__main__':
    p0_simulator()
