import json
from modules.platforms.functions import find_program, generate_program_key, get_resource, save_data, check_send_notification
from modules.notifier.discord import send_notification

def check_intigriti(tmp_dir, mUrl, first_time, db, config):
    json_programs_key = []
    notifications = config['notifications']
    monitor = config['monitor']
    get_resource(tmp_dir, config['url'], "intigriti")
    with open(f"{tmp_dir}intigriti.json") as intigritiFile:
        intigriti = json.load(intigritiFile)

    for program in intigriti:
        programName = program["name"]
        programURL = f"https://app.intigriti.com/programs/{program['handle']}"
        data = {
            "programName": programName,
            "programType": "",
            "programURL": programURL,
            "platformName": "Intigriti",
            "isRemoved": False,
            "isNewProgram": False,
            "color": 10858237
        }

        dataJson = {
            "programName": programName,
            "programURL": programURL,
            "programType": "",
            "scope": {},
            "reward": {}
        }

        programKey = generate_program_key(programName, programURL)
        json_programs_key.append(programKey)
        watcherData = find_program(db, 'intigriti', programKey)

        if watcherData is None:
            data["isNewProgram"] = True
            watcherData = {
                "programName": programName,
                "programURL": programURL,
                "programType": "",
                "scope": {},
                "reward": {}
            }

        if 'domains' in program:
            for target in program['domains']:
                if 'description' in target and target['description'] is not None:
                    dataJson['scope'][target['id']] = f"{target['endpoint']}\n{target['description']}\n"
                else:
                    dataJson['scope'][target['id']] = f"{target['endpoint']}\n"

        if program.get("maxBounty", {}).get("value", 0) > 0:
            dataJson["programType"] = "rdp"
            data["programType"] = "rdp"
            bounty = {
                "min": f"{program['minBounty'].get('value', 0)} {program['minBounty'].get('currency', '')}",
                "max": f"{program['maxBounty'].get('value', 0)} {program['maxBounty'].get('currency', '')}"
            }
            dataJson["reward"] = bounty
        else:
            dataJson["programType"] = "vdp"
            data["programType"] = "vdp"

        # Assuming a function that checks and updates the database for changes
        # You will need to implement this logic based on your application's requirements
        hasChanged, is_update = False, False
        # Example check - you would expand this with actual logic to compare and detect changes
        if dataJson != watcherData:
            hasChanged = True
            save_data(db, "intigriti", programKey, dataJson)
            if check_send_notification(first_time, is_update, data, watcherData, monitor, notifications):
                send_notification(data, mUrl)

    # Handling removed programs
    db_programs_key = db['intigriti'].distinct("programKey")
    removed_programs_key = set(db_programs_key) - set(json_programs_key)
    for program_key in removed_programs_key:
        program = find_program(db, 'intigriti', program_key)
        if notifications['removed_program'] and not first_time:
            send_notification({
                "color": 10858237,
                "platformName": "Intigriti",
                "isRemoved": True,
                "programName": program["programName"],
                "programType": program["programType"]
            }, mUrl)
        db['intigriti'].delete_many({"programKey": program_key})
