from api import start, oncalls, action
from collections import defaultdict
from pprint import pprint


TOP = 25
MAX_CAPACITY = 8

DOWN = 0
UP = 1
STOP = 2


class Controller:
    def __init__(self):
        self.call_cache = dict()
        self.elevator_info = dict()

    def init_elevator(self, elevator):
        elev_id = elevator["id"]
        floor = elevator["floor"]

        self.elevator_info[elev_id] = dict()
        self.elevator_info[elev_id]["destination"] = 1
        self.elevator_info[elev_id]["direction"] = STOP
        self.elevator_info[elev_id]["floor"] = floor
        self.elevator_info[elev_id]["preserved_calls"] = []

    def is_scheduled_call(self, call_id):
        return call_id in self.call_cache

    def is_same_direction(self, call_dir, elev_dir):
        return call_dir == elev_dir

    def schedule_call(self, call_id, call_start, call_end, direction):
        ret_id = None
        distance = TOP
        ret = False

        for elev_id, info in self.elevator_info.items():
            if info["direction"] == STOP:
                if distance > abs(call_start - info["floor"]):
                    distance = abs(call_start - info["floor"])
                    ret_id = elev_id
            elif self.is_same_direction(direction, info["direction"]):
                if distance > abs(call_start - info["destination"]):
                    distnace = abs(call_start - info["destination"])
                    ret_id = elev_id

        if ret_id != None:
            self.elevator_info[ret_id]["preserved_calls"].append(
                (call_id, call_start, call_end))
            return True
        else:
            return False

    def schedule(self, call, elevator):

        call_id = call["id"]
        elev_id = elevator["id"]

        call_start = call["start"]
        call_end = call["end"]
        direction = call_end > call_start

        if elev_id == 3:
            print(len(elevator["passengers"]))
            print(len(self.elevator_info[elev_id]["preserved_calls"]))
            print("sum")
            print(len(elevator["passengers"]) +
                  len(self.elevator_info[elev_id]["preserved_calls"]))
        if len(elevator["passengers"]) + len(self.elevator_info[elev_id]["preserved_calls"]) >= MAX_CAPACITY:
            print("in")
            return

        if self.is_scheduled_call(call_id):
            return

        is_scheduled = self.schedule_call(
            call_id, call_start, call_end, direction)
        if is_scheduled:
            self.call_cache[call_id] = True

    def is_enter(self, elevator, calls):
        floor = elevator["floor"]
        elev_id = elevator["id"]
        for call in calls:
            if call[1] == floor:
                return True
        return False

    def is_exit(self, elevator, calls):
        floor = elevator["floor"]
        passengers = elevator["passengers"]
        for passenger in passengers:
            if passenger["end"] == floor:
                return True

        return False

    def nothing_to_do(self, elevator, calls):
        return not elevator["passengers"] and not calls

    def next_direction(self, direction):
        return "UP" if direction == UP else "DOWN"

    def get_next_move(self, elevator):
        elev_id = elevator["id"]
        floor = elevator["floor"]
        passengers = elevator["passengers"]
        status = elevator["status"]

        is_stopped = status == "STOPPED"
        is_opened = status == "OPENED"

        calls = self.elevator_info[elev_id]["preserved_calls"]
        destination = self.elevator_info[elev_id]["destination"]

        # STOPPED
        if is_stopped:
            if self.is_enter(elevator, calls) or self.is_exit(elevator, calls):
                return "OPEN"
        if is_opened:
            if self.is_exit(elevator, calls):
                return "EXIT"
            elif self.is_enter(elevator, calls):
                return "ENTER"
            else:
                return "CLOSE"
        if is_stopped:
            if self.nothing_to_do(elevator, calls):
                return "STOP"
            else:
                return self.next_direction(self.elevator_info[elev_id]["direction"])

        if self.is_enter(elevator, calls) or self.is_exit(elevator, calls):
            return "STOP"
        # MOVE
        direction = self.elevator_info[elev_id]["direction"]
        if direction == UP:
            return "UP"
        elif direction == DOWN:
            return "DOWN"
        else:
            print(direction)
            raise ValueError

    def get_enter_arr(self, elevator):
        elev_id = elevator["id"]
        floor = elevator["floor"]

        calls = self.elevator_info[elev_id]["preserved_calls"]

        ret_arr = []

        for idx, (call_id, call_start, call_end) in enumerate(calls):
            if call_start == floor:
                ret_arr.append(call_id)
                # remove preserved_calls

                calls.pop(idx)

        return ret_arr

    def get_exit_arr(self, elevator):
        floor = elevator["floor"]
        passengers = elevator["passengers"]
        elev_id = elevator["id"]

        ret_arr = []

        for passenger in passengers:
            if floor == passenger["end"]:
                ret_arr.append(passenger["id"])

        return ret_arr

    def get_next(self, elevator):
        next_move = self.get_next_move(elevator)
        ret_arr = []
        if next_move == "ENTER":
            ret_arr = self.get_enter_arr(elevator)
        elif next_move == "EXIT":
            ret_arr = self.get_exit_arr(elevator)

        return (next_move, ret_arr)

    def update_direction(self, elevators):
        for elevator in elevators:
            elev_id = elevator["id"]
            floor = elevator["floor"]
            passengers = elevator["passengers"]

            info = self.elevator_info[elev_id]
            info["floor"] = elevator["floor"]

            if passengers:
                passenger = passengers[0]
                p_end = passenger["end"]
                info["direction"] = UP if p_end > floor else DOWN
            else:
                # start of preserved call
                if not info["preserved_calls"]:
                    return
                call_start = info["preserved_calls"][0][1]
                call_end = info["preserved_calls"][0][2]
                if call_start == floor:
                    info["direction"] = "UP" if call_end > floor else "DOWN"

    def update_destination(self, elevators):
        for elevator in elevators:
            elev_id = elevator["id"]
            passengers = elevator["passengers"]
            floor = elevator["floor"]

            info = self.elevator_info[elev_id]

            if passengers:
                passenger = passengers[0]
                p_start, p_end = passenger["start"], passenger["end"]
                info["direction"] = UP if p_end > p_start else DOWN
            elif info["preserved_calls"]:
                call = info["preserved_calls"][0]
                c_start = call[1]

                info["direction"] = UP if c_start > floor else DOWN
            else:
                info["direction"] = STOP


def p0_simulator():
    user = 'TG'
    problem = 2
    count = 4

    ret = start(user, problem, count)
    token = ret['token']
    print('Token for %s is %s' % (user, token))

    elevators = ret["elevators"]
    controller = Controller()
    for elevator in elevators:
        controller.init_elevator(elevator)

    while True:
        ret = oncalls(token)
        calls = ret["calls"]
        elevators = ret["elevators"]
        is_end = ret["is_end"]

        if is_end:
            break

        action_dict = {"commands": []}

        for call in calls:
            for elevator in elevators:
                controller.schedule(call, elevator)

        controller.update_direction(elevators)
        controller.update_destination(elevators)

        actions = []
        for elevator in elevators:
            next_action, action_arr = controller.get_next(elevator)
            tmp_dict = {}
            tmp_dict["elevator_id"] = elevator["id"]
            tmp_dict["command"] = next_action
            if action_arr:
                tmp_dict["call_ids"] = action_arr
            actions.append(tmp_dict)

        print("=" * 10)
        print("CALLS")
        pprint(calls)
        print()
        print("ELEVATOR")
        pprint(elevators)
        print()
        print("ELEV INFO")
        pprint(controller.elevator_info)
        print()
        print("ACTION")
        pprint(actions)
        print()
        assert len(elevators) == len(actions), print("elevator lens are diff")
        action(token, actions)

    # oncalls(token)
    # action(token, next_actions)


if __name__ == '__main__':
    p0_simulator()
