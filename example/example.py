import requests
from pprint import pprint

inf = int(1e9)

UP, DOWN = 0, 1
url = 'http://localhost:8000'
top_floor = 5
call_track = dict()


def start(user, problem, count):
    uri = url + '/start' + '/' + user + '/' + str(problem) + '/' + str(count)
    return requests.post(uri).json()


def oncalls(token):
    uri = url + '/oncalls'
    return requests.get(uri, headers={'X-Auth-Token': token}).json()


def action(token, cmds):
    uri = url + '/action'

    return requests.post(uri, headers={'X-Auth-Token': token}, json={'commands': cmds}).json()


def is_upward(start, end):
    return UP if start <= end else DOWN


def check_enter(floor, is_reached, direction):
    global calls
    for call in calls:
        if floor == call["start"]:
            return True
        #     print(floor)
        #     print(is_upward(call["start"], call["end"]))
        #     print(direction)

        #     exit(0)
        # if floor == call["start"] and (is_reached or is_upward(call["start"], call["end"]) == direction):
        #     return True

    return False


def check_exit(floor, passengers):
    for passenger in passengers:
        if passenger["end"] == floor:
            return True
    return False


def find_next_destination(floor):
    global calls
    global top_floor
    closest = inf
    next_des = top_floor
    for call in calls:
        top_floor = max(top_floor, call["end"])
        top_floor = max(top_floor, call["start"])
        if abs(floor - call["start"]) < closest:
            closest = abs(floor - call["start"])
            next_des = call["start"]
    return next_des


def next_stop(elevator, info):
    global calls
    global top_floor

    is_enter = check_enter(
        elevator["floor"], info["is_reached"], info["direction"])
    if is_enter:
        return "OPEN"

    is_exit = check_exit(elevator["floor"], elevator["passengers"])
    if is_exit:
        return "OPEN"

    if not calls:
        return "STOP"
    if info["is_reached"]:
        next_des = find_next_destination(elevator["floor"])
        info["is_reached"] = False
        info["destination"] = next_des
        info["direction"] = UP if next_des > elevator["floor"] else DOWN

        return "UP" if elevator["floor"] <= next_des else "DOWN"

    return "UP" if info["direction"] == UP else "DOWN"


def check_open_exit(floor, passengers):
    ret = False
    ret_arr = []
    for passenger in passengers:
        if floor == passenger["end"]:
            call_track[passenger["id"]] = False
            ret_arr.append(passenger["id"])

    return (ret, ret_arr)


def check_open_enter(floor, info):
    is_reached = info["is_reached"]
    direction = info["direction"]
    ret = False
    ret_arr = []
    for call in calls:
        if call["id"] in call_track and call_track[call["id"]]:
            continue
        call_dir = "UP" if call["end"] > call["start"] else "DOWN"
        if is_reached:
            info["is_reached"] = False
            is_reached = False
            info["destination"] = call["end"]
            info["direction"] = call_dir
            call_track[call["id"]] = True
            ret = True
            ret_arr.append(call["id"])
        elif call["start"] == floor:
            call_track[call["id"]] = True
            ret = True
            ret_arr.append(call["id"])
    return (ret, ret_arr)


def next_open(elevator, info):
    is_exit, ret_arr = check_open_exit(
        elevator["floor"], elevator["passengers"])
    if is_exit:
        return ("EXIT", ret_arr)

    is_enter, ret_arr = check_open_enter(
        elevator["floor"], info)
    if is_enter:
        return ("ENTER", ret_arr)

    return ("CLOSE", None)


def next_move(elevator, info):
    global top_floor

    is_exit = check_exit(elevator["floor"], elevator["passengers"])
    if is_exit:
        return "STOP"

    is_enter = check_enter(
        elevator["floor"], info["is_reached"], info["direction"])
    if is_enter:
        return "STOP"

    if elevator["floor"] == 1:
        info["direction"] = UP
        return "UP"

    if elevator["floor"] == top_floor:
        info["direction"] = DOWN
        return "DOWN"

    return "UP" if info["direction"] == UP else "DOWN"


def p0_simulator():
    global calls
    global top_floor

    user = 'tester'
    problem = 0
    count = 4

    ret = start(user, problem, count)
    token = ret['token']
    print('Token for %s is %s' % (user, token))

    # ELEVATOR INFORMATION
    elevator_info = [0 for _ in range(count)]
    id_to_idx = dict()

    is_first = True
    is_end = ret["is_end"]
    while not is_end:
        oncalls_res = oncalls(token)
        calls = oncalls_res["calls"]
        print("="*10)
        print("calls")
        pprint(calls)
        elevators = oncalls_res["elevators"]
        print("elevators")
        pprint(elevators)
        if is_first:
            for idx, ele in enumerate(elevators):
                id_to_idx[ele["id"]] = idx
                elevator_info[idx] = {"direction": UP,
                                      "is_reached": True,
                                      "destination": -1}
                top_floor = max(ele["floor"], top_floor)
                is_first = False

        # timestamps = oncalls_res["timestamps"]
        is_end = oncalls_res["is_end"]

        actions = []
        for elevator in elevators:
            action_dict = {}
            action_dict["elevator_id"] = elevator["id"]

            if elevator["status"] == "STOPPED":
                next_action = next_stop(
                    elevator, elevator_info[id_to_idx[elevator["id"]]])
                action_dict["command"] = next_action
            elif elevator["status"] == "OPENED":
                next_action, arr = next_open(
                    elevator, elevator_info[id_to_idx[elevator["id"]]])
                action_dict["command"] = next_action
                if arr:
                    action_dict['call_ids'] = arr
            else:
                next_action = next_move(
                    elevator, elevator_info[id_to_idx[elevator["id"]]])
                action_dict["command"] = next_action
            actions.append(action_dict)
        pprint(actions)
        action(token, actions)

    # action(token, [{'elevator_id': 0, 'command': 'UP'},
    #                {'elevator_id': 1, 'command': 'STOP'}])

    # oncalls(token)
    # action(token, [{'elevator_id': 0, 'command': 'UP'},
    #                {'elevator_id': 1, 'command': 'OPEN'}])

    # oncalls(token)
    # action(token, [{'elevator_id': 0, 'command': 'UP'}, {
    #        'elevator_id': 1, 'command': 'ENTER', 'call_ids': [2, 3]}])

    # oncalls(token)
    # action(token, [{'elevator_id': 0, 'command': 'STOP'},
    #                {'elevator_id': 1, 'command': 'CLOSE'}])

    # oncalls(token)
    # action(token, [{'elevator_id': 0, 'command': 'OPEN'},
    #                {'elevator_id': 1, 'command': 'UP'}])

    # oncalls(token)
    # action(token, [{'elevator_id': 0, 'command': 'ENTER', 'call_ids': [0, 1]}, {
    #        'elevator_id': 1, 'command': 'STOP'}])

    # oncalls(token)
    # action(token, [{'elevator_id': 0, 'command': 'CLOSE'},
    #                {'elevator_id': 1, 'command': 'OPEN'}])

    # oncalls(token)
    # action(token, [{'elevator_id': 0, 'command': 'DOWN'}, {
    #        'elevator_id': 1, 'command': 'EXIT', 'call_ids': [2]}])

    # oncalls(token)
    # action(token, [{'elevator_id': 0, 'command': 'STOP'},
    #                {'elevator_id': 1, 'command': 'CLOSE'}])

    # oncalls(token)
    # action(token, [{'elevator_id': 0, 'command': 'OPEN'},
    #                {'elevator_id': 1, 'command': 'UP'}])

    # oncalls(token)
    # action(token, [{'elevator_id': 0, 'command': 'EXIT', 'call_ids': [1]}, {
    #        'elevator_id': 1, 'command': 'UP'}])

    # oncalls(token)
    # action(token, [{'elevator_id': 0, 'command': 'CLOSE'},
    #                {'elevator_id': 1, 'command': 'STOP'}])

    # oncalls(token)
    # action(token, [{'elevator_id': 0, 'command': 'DOWN'},
    #                {'elevator_id': 1, 'command': 'OPEN'}])

    # oncalls(token)
    # action(token, [{'elevator_id': 0, 'command': 'STOP'}, {
    #        'elevator_id': 1, 'command': 'EXIT', 'call_ids': [3]}])

    # oncalls(token)
    # action(token, [{'elevator_id': 0, 'command': 'OPEN'},
    #                {'elevator_id': 1, 'command': 'CLOSE'}])EXIT',

    # oncalls(token)
    # action(token, [{'elevator_id': 0, 'command': 'ENTER', 'call_ids': [4]}, {
    #        'elevator_id': 1, 'command': 'STOP'}])

    # oncalls(token)
    # action(token, [{'elevator_id': 0, 'command': 'CLOSE'},
    #                {'elevator_id': 1, 'command': 'STOP'}])

    # oncalls(token)
    # action(token, [{'elevator_id': 0, 'command': 'DOWN'},
    #                {'elevator_id': 1, 'command': 'STOP'}])

    # oncalls(token)
    # action(token, [{'elevator_id': 0, 'command': 'STOP'},
    #                {'elevator_id': 1, 'command': 'STOP'}])

    # oncalls(token)
    # action(token, [{'elevator_id': 0, 'command': 'OPEN'},
    #                {'elevator_id': 1, 'command': 'STOP'}])

    # oncalls(token)
    # action(token, [{'elevator_id': 0, 'command': 'EXIT', 'call_ids': [0, 4]}, {
    #        'elevator_id': 1, 'command': 'STOP'}])

    # oncalls(token)
    # action(token, [{'elevator_id': 0, 'command': 'ENTER', 'call_ids': [5]}, {
    #        'elevator_id': 1, 'command': 'STOP'}])

    # oncalls(token)
    # action(token, [{'elevator_id': 0, 'command': 'CLOSE'},
    #                {'elevator_id': 1, 'command': 'STOP'}])

    # oncalls(token)
    # action(token, [{'elevator_id': 0, 'command': 'UP'},
    #                {'elevator_id': 1, 'command': 'STOP'}])


    # oncalls(token)
    # action(token, [{'elevator_id': 0, 'command': 'STOP'},
    #                {'elevator_id': 1, 'command': 'STOP'}])
    # oncalls(token)
    # action(token, [{'elevator_id': 0, 'command': 'OPEN'},
    #                {'elevator_id': 1, 'command': 'STOP'}])
    # oncalls(token)
    # action(token, [{'elevator_id': 0, 'command': 'EXIT', 'call_ids': [5]}, {
    #        'elevator_id': 1, 'command': 'STOP'}])
if __name__ == '__main__':
    p0_simulator()
