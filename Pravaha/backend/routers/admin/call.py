from utils.call import get_call_status, handle_call, latest_summary


def call(phone_number, name, system_prompt, context=""):
    return handle_call(phone_number, name, system_prompt, context)


def get_status(call_id):
    return get_call_status(call_id)


def get_latest_summary(call_id=None):
    return latest_summary(call_id)
