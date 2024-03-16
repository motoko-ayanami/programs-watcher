import json
from modules.platforms.functions import find_program, generate_program_key, get_resource, remove_elements, save_data, check_send_notification
from modules.notifier.discord import send_notification

# Parse the rewards of the json
def parse_rewards(reward_summary):
    # Check if reward_summary is None and treat it as an empty dictionary if so
    if reward_summary is None:
        reward_summary = {}

    min_reward_str = reward_summary.get("minReward", "0").replace("$", "").replace(",", "")
    max_reward_str = reward_summary.get("maxReward", "0").replace("$", "").replace(",", "")
    min_reward = int(min_reward_str) if min_reward_str.isdigit() else 0
    max_reward = int(max_reward_str) if max_reward_str.isdigit() else 0
    return min_reward, max_reward

# checking bugcrowd
def check_bugcrowd(tmp_dir, mUrl, first_time, db, config):
    json_programs_key = []
    notifications = config['notifications']
    monitor = config['monitor']
    get_resource(tmp_dir, config['url'], "bugcrowd")
    bugcrowdFile = open(f"{tmp_dir}bugcrowd.json")
    bugcrowd = json.load(bugcrowdFile)
    bugcrowdFile.close()
    for program in bugcrowd:
        programName = program["name"]
        programURL = "https://bugcrowd.com" + program.get("briefUrl", "")
        logoUrl = program.get("logoUrl", "")
        reward_summary = program.get("rewardSummary", {})
        min_reward, max_reward = parse_rewards(reward_summary)

        data = {"programName": programName, "reward": {"min": min_reward, "max": max_reward}, "isRemoved": False, "newType": "", "newInScope": [], "removeInScope": [], "newOutOfScope": [], "removeOutOfScope": [], "programURL": programURL,
                "logoUrl": logoUrl, "platformName": "Bugcrowd", "isNewProgram": False, "color": 14584064}
        dataJson = {"programName": programName, "programURL": programURL, "programType": "",
                    "outOfScope": [], "inScope": [], "reward": {"min": min_reward, "max": max_reward}}
        programKey = generate_program_key(programName, programURL)
        json_programs_key.append(programKey)
        watcherData = find_program(db, 'bugcrowd', programKey)
        if watcherData is None:
            data["isNewProgram"] = True
            watcherData = {"programKey": programKey, "programName": programName, "programURL": programURL, "programType": "",
                           "outOfScope": [], "inScope": [], "reward": {}}

        for target in program["target_groups"]:
            if not target["in_scope"]:
                for item in target["targets"]:
                    dataJson["outOfScope"].append(item["name"])
            else:
                for item in target["targets"]:
                    dataJson["inScope"].append(item["name"])

        programType = "rdp" if min_reward > 0 else "vdp"
        dataJson["programType"] = data["programType"] = programType

        newInScope, removeInScope, newOutOfScope, removedOutOfScope = check_scope_changes(dataJson, watcherData)

        hasChanged, is_update = update_watcher_data(watcherData, newInScope, removeInScope, newOutOfScope, removedOutOfScope, dataJson["programType"], dataJson["reward"], notifications)

        if hasChanged:
            save_data(db, "bugcrowd", programKey, watcherData)
            if check_send_notification(first_time, is_update, data, watcherData, monitor, notifications):
                send_notification(data, mUrl)

    check_removed_programs(json_programs_key, db, mUrl, notifications, first_time)

def check_scope_changes(dataJson, watcherData):
    newInScope = [i for i in dataJson["inScope"] if i not in watcherData["inScope"]]
    removeInScope = [i for i in watcherData["inScope"] if i not in dataJson["inScope"]]
    newOutOfScope = [i for i in dataJson["outOfScope"] if i not in watcherData["outOfScope"]]
    removedOutOfScope = [i for i in watcherData["outOfScope"] if i not in dataJson["outOfScope"]]
    return newInScope, removeInScope, newOutOfScope, removedOutOfScope

def update_watcher_data(watcherData, newInScope, removeInScope, newOutOfScope, removedOutOfScope, programType, reward, notifications):
    hasChanged = is_update = False
    if newInScope:
        watcherData["inScope"].extend(newInScope)
        hasChanged = is_update = notifications['new_inscope']
    if removeInScope:
        remove_elements(watcherData["inScope"], removeInScope)
        hasChanged = is_update = notifications['removed_inscope']
    if newOutOfScope:
        watcherData["outOfScope"].extend(newOutOfScope)
        hasChanged = is_update = notifications['new_out_of_scope']
    if removedOutOfScope:
        remove_elements(watcherData["outOfScope"], removedOutOfScope)
        hasChanged = is_update = notifications['removed_out_of_scope']
    if programType != watcherData["programType"]:
        watcherData["programType"] = programType
        hasChanged = is_update = notifications['new_type']
    if reward != watcherData["reward"]:
        watcherData["reward"] = reward
        hasChanged = is_update = notifications['new_bounty_table']
    return hasChanged, is_update

def check_removed_programs(json_programs_key, db, mUrl, notifications, first_time):
    db_programs_key = db['bugcrowd'].distinct("programKey")
    removed_programs_key = set(db_programs_key) - set(json_programs_key)
    for program_key in removed_programs_key:
        program = find_program(db, 'bugcrowd', program_key)
        data = {
            "color": 14584064,
            "logoUrl": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTwToiI8YA0eLclDkd-vJ0xXs7bun5LdHfTrgJucvI&s",
            "platformName": "Bugcrowd",
            "isRemoved": True,
            "programName": program["programName"],
            "programType": program["programType"]
        }
        if notifications['removed_program'] and not first_time:
            send_notification(data, mUrl)
        db['bugcrowd'].delete_many({"programKey": program_key})
