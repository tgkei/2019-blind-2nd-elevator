from random import random
import requests
from pprint import pprint

inf = int(1e9)

UP, DOWN = 0, 1
url = 'http://localhost:8000'
TOP_FLOOR = 25
MAX_CAPACITY = 8


def start(user, problem, count):
    uri = url + '/start' + '/' + user + '/' + str(problem) + '/' + str(count)
    return requests.post(uri).json()


def oncalls(token):
    uri = url + '/oncalls'
    return requests.get(uri, headers={'X-Auth-Token': token}).json()


def action(token, cmds):
    uri = url + '/action'

    return requests.post(uri, headers={'X-Auth-Token': token}, json={'commands': cmds}).json()


def stop_check(elevator, calls, word):
    ret = False
    ret_arr = []
    for call in calls:
        pos = call[word]
        floor = elevator["floor"]
        if pos == floor:
            ret = True
            ret_arr.append(call["id"])
    return ret, ret_arr


def check_movement(elevator, schedule_calls):
    pass


def next_stop(elevator, schedule_calls, info):
    is_exit, _ = stop_check(elevator, elevator["passengers"], "end")
    if is_exit:
        return 'OPEN', _

    is_enter, _ = stop_check(elevator, schedule_calls, "start")
    if is_enter:
        return 'OPEN', _

    passengers = elevator["passengers"]
    floor = elevator["floor"]

    if passengers:
        end = passengers[0]["end"]
        if floor < end:
            return 'UP', []
        else:
            return 'DOWN', []
    if schedule_calls:
        start = schedule_calls[0]["start"]
        if floor < start:
            return 'UP', []
        else:
            return 'DOWN', []
    return 'STOP', []


def next_open(elevator, schedule_calls):
    is_exit, ret_arr = stop_check(elevator, elevator["passengers"], "end")
    if is_exit:
        return 'EXIT', ret_arr

    is_enter, ret_arr = stop_check(elevator, schedule_calls, "start")
    if is_enter:
        return 'ENTER', ret_arr

    return 'CLOSE', None


def next_move(elevator, schedule_calls, info):
    passengers = elevator["passengers"]

    is_exit, _ = stop_check(elevator, passengers, "end")
    if is_exit:
        return 'STOP'

    is_enter, _ = stop_check(elevator, schedule_calls, "start")
    if is_enter:
        return 'STOP'

    return "UP" if elevator["status"] == "UPWARD" else "DOWN"


def p0_simulator():
    user = 'tester'
    problem = 1
    count = 4

    ret = start(user, problem, count)
    token = ret['token']
    print('Token for %s is %s' % (user, token))

    # ELEVATOR INFORMATION
    elevator_info = [0 for _ in range(count)]
    id_to_idx = dict()

    is_first = True
    is_end = ret["is_end"]

    controller = dict()
    calls_dict = dict()
    while not is_end:
        print("="*10)
        ret = oncalls(token)
        calls = ret["calls"]
        elevators = ret["elevators"]
        is_end = ret["is_end"]

        if is_first:
            for idx, ele in enumerate(elevators):
                id_to_idx[ele["id"]] = idx
                elevator_info[idx] = {"direction": UP,
                                      "is_reached": True,
                                      "is_opened": False
                                      }
            is_first = False

        # delete duplicated calls
        new_calls = []
        ids = set()
        for call in calls:
            if call["id"] in ids:
                continue
            ids.add(call["id"])
            new_calls.append(call)
        calls = new_calls

        # schedule elevators to each call
        for call in calls:
            # find closest and is coming to me or is_reached
            # if no closest which is coming to me or is_reached just continue
            if call["id"] in calls_dict and calls_dict[call["id"]]:
                continue

            calls_dict[call["id"]] = True

            ele = None
            distance = TOP_FLOOR + 1
            for elevator in elevators:
                floor = elevator["floor"]
                info = elevator_info[id_to_idx[elevator["id"]]]
                if elevator["id"] in controller:
                    if len(controller[elevator["id"]]) >= MAX_CAPACITY:
                        continue

                if distance > abs(floor - call["start"]):
                    if info["is_reached"]:
                        ele = elevator["id"]
                        distance = abs(floor - call["start"])
                    elif floor > call["start"] and info["direction"] == DOWN:
                        ele = elevator["id"]
                        distance = abs(floor - call["start"])
                    elif floor < call["start"] and info["direction"] == UP:
                        ele = elevator["id"]
                        distance = abs(floor - call["start"])
                    else:
                        ele = elevator["id"]
                        distance = abs(floor - call["start"])

            if ele != None:
                if ele not in controller:
                    controller[ele] = [call]
                else:
                    if len(controller[ele]) < MAX_CAPACITY:
                        controller[ele].append(call)

        actions = []

        for elevator in elevators:
            action_dict = {}
            action_dict["elevator_id"] = elevator["id"]
            info = elevator_info[id_to_idx[elevator["id"]]]
            scheduled = controller[elevator["id"]
                                   ] if elevator["id"] in controller else []

            if elevator["status"] == "STOPPED":  # and not info["is_opened"]:
                next_action, _ = next_stop(
                    elevator, scheduled, info)
                action_dict["command"] = next_action

            elif elevator["status"] == "OPENED":
                if info["is_opened"]:
                    info["is_opened"] = False
                    action_dict["command"] = "CLOSE"
                else:
                    next_action, arr = next_open(
                        elevator, scheduled)
                    action_dict["command"] = next_action

                    if arr:
                        # if call are entered, remove them from controller array
                        action_dict['call_ids'] = arr
                        if next_action == "ENTER":
                            for entered_id in arr:
                                for idx, call in enumerate(scheduled):
                                    if call["id"] == entered_id:
                                        scheduled.pop(idx)
                        if next_action == "EXIT":
                            for exited_id in arr:
                                calls_dict[exited_id] = False
                    info["is_opened"] = True
            else:
                next_action = next_move(
                    elevator, scheduled, info)
                action_dict["command"] = next_action
            actions.append(action_dict)

        print("call")
        pprint(calls)
        print("scheduler")
        pprint(controller)
        print("action")
        pprint(actions)
        print("elevaotrs")
        pprint(elevators)
        action(token, actions)


if __name__ == '__main__':
    p0_simulator()
