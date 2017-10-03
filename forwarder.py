import os
import sys
import time
import datetime
import base64
import json
import re
import signal
from functools import partial

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''

# For advanced users, if you want to create single instance mod input, uncomment this method.
"""
def use_single_instance_mode():
    print "hallo use_single_instance_mode"
    return True
"""

def shutdown_signal_handler(helper, key_already_running, signum, frame):
    # Delete we are running check point just to be sure.
    helper.log_debug("Ionic: Received terminate signal from Splunk.")
    helper.delete_check_point(key_already_running)
    sys.exit(0)

def s_print(message):
    print >>sys.stderr, message

def get_next_link_url(response):
    """Get the url for the next request via the Link header"""
    r_link_header = response.links.get("next")
    if r_link_header != None:
        return r_link_header.get("url")

'''
    IMPORTANT
    Anything below this point can be modified as needed.
'''

# Configured Splunk parameters
tenant_id_arg = "tenant_id"
api_environment_arg = "api_environment"
api_user_name_arg = "api_user_name"
api_user_password_arg = "api_user_password"
start_time_arg = "start_time"

# Timeout (in seconds) for each request sent to the Ionic Download API.
timeout_sec = 60.0
# Time to wait (in seconds) between retrying requests (when the previous response was empty).
# 15 minutes is the default based on how frequently new data becomes queryable.
wait_to_retry_sec = 60 * 15

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    pass

def collect_events(helper, ew):
    """Implement your data collection logic here"""
    opt_tenant_id = helper.get_arg('tenant_id')
    opt_api_environment = helper.get_arg('api_environment')
    opt_api_user_name = helper.get_arg('api_user_name')
    opt_api_password = helper.get_arg('api_user_password')
    opt_start_time = helper.get_arg('start_time')
    opt_object_type = helper.get_arg('object_type')
    opt_test_max_loops = helper.get_arg('test_max_loops')
    opt_start_new_loop = helper.get_arg('start_new_loop')
    opt_remove_already_running_pid = helper.get_arg('remove_already_running_pid')
    opt_check_already_running = helper.get_arg('check_already_running')

    if opt_tenant_id is None or opt_tenant_id == "":
        raise ValueError(": '--{}' must be defined".format(tenant_id_arg))

    if opt_api_environment is None or opt_api_environment == "":
        raise ValueError(": '--{}' must be defined".format(api_environment_arg))
    
    key_id = "{}_{}_{}".format(opt_tenant_id, opt_object_type, opt_api_environment)
    key_next_link = "next_link_{}".format(key_id)
    key_latest_id = "latest_id_{}".format(key_id)
    key_already_running = "already_running_{}".format(key_id)

    if opt_start_new_loop:
        helper.delete_check_point(key_next_link)
        helper.delete_check_point(key_latest_id)
        helper.delete_check_point(key_already_running)
        s_print(" Deleted all check point data for ID: {}".format(key_id))
        return

    elif opt_remove_already_running_pid:
        helper.delete_check_point(key_already_running)
        s_print(" Removed already running check point for ID: {}".format(key_id))
        return

    else:
        if opt_api_user_name is None or opt_api_user_name == "":
            raise ValueError(": '--{}' must be defined".format(api_user_name_arg))

        if opt_api_password is None or opt_api_password == "":
            raise ValueError(": '--{}' must be defined".format(api_user_password_arg))

        if opt_start_time is None or opt_start_time == "":
            raise ValueError(": '--{}' must be defined".format(start_time_arg))

        if re.match("^[0-9]{8}-[0-9]{2}:[0-9]{2}$", opt_start_time) is None:
            raise ValueError(": '--{}' must be in YYYYMMdd-HH:mm format, with 'mm' being a 15 min. interval (i.e. 00, 15, 30, or 45)".format(start_time_arg))


        run_in_test_mode = False
        if opt_test_max_loops != None and opt_test_max_loops != "":
            opt_test_max_loops = int(opt_test_max_loops)
            run_in_test_mode = True

        # [Optional - uncomment and modify as needed]
        # Sleep for 2 seconds to allow Splunk to delete the pid
        # helper.log_debug("Ionic: Sleep for 2 seconds before checking for the PID.")
        # time.sleep(2)

        # Check if another process on the tenant is already running
        if opt_check_already_running:
            already_running = helper.get_check_point(key_already_running)
            if already_running:
                raise ValueError(": Another process is already running. Reset other process and try again.")

        try:
            signal.signal(signal.SIGTERM, partial(shutdown_signal_handler, helper, key_already_running))
            signal.signal(signal.SIGINT, partial(shutdown_signal_handler, helper, key_already_running))

            # Set we are running check point
            helper.save_check_point(key_already_running, "true")

            url = helper.get_check_point(key_next_link)
            existing_latest_id = None
            # Configure URL if this is the first run, otherwise set latest existing id
            if url is None:
                url = "https://{}/v2/{}/download?objects={}&start={}".format(opt_api_environment, opt_tenant_id, opt_object_type, opt_start_time)
            else:
                existing_latest_id = helper.get_check_point(key_latest_id)

            s_print(" URL: {}".format(url))
            s_print(" latest_id: {}".format(existing_latest_id))
    
            # Set Authentication header
            api_user_pass = "{}:{}".format(opt_api_user_name, opt_api_password)
            api_user_b64_pass = base64.b64encode(api_user_pass)
            headers = {"Authorization": "Basic {}".format(api_user_b64_pass)}

            loop_count = 0
            while True:
                loop_count += 1
                helper.log_debug("Ionic: Connecting to url {}".format(url))
                try:
                    response = helper.send_http_request(url=url, method="GET", headers=headers, timeout=timeout_sec)
                except:
                    s_print(" Connection timed out to Ionic.")
                    helper.log_warning("Ionic: Connection timed out to {}".format(opt_api_environment))

                    if run_in_test_mode and loop_count > opt_test_max_loops:
                        s_print(" Number of attempted requests exceeded max requests allowed")
                        helper.log_warning("Ionic: Number of attempted requests exceeded max requests allowed")
                        break

                    # Sleep 5 seconds and try again
                    time.sleep(wait_to_retry_sec)
                    continue

                r_status = response.status_code
                if r_status != 200:
                    s_print(" Failed to connect to Ionic to collect log entries with error: {}".format(r_status))
                    helper.log_warning("Ionic: Failed to connect to Ionic to collect log entries with error: {}".format(r_status))

                    if run_in_test_mode and loop_count > opt_test_max_loops:
                        s_print(" Number of attempted requests exceeded max requests allowed")
                        helper.log_warning("Ionic: Number of attempted requests exceeded max requests allowed")
                        break

                    # Sleep 5 seconds and try again
                    time.sleep(wait_to_retry_sec)
                    continue

                # Get the url for the next request via the Link header
                r_next_link_url = get_next_link_url(response)
                if r_next_link_url != None:
                    url = r_next_link_url

                # Get the response body as text and split into lines (one line is one log entry)
                r_text = response.text
                lines = r_text.split('\n')

                # When we do not have an existing_latest_id we set found_id to true to commit every event
                # When we do have an existing_latest_id we commit events after we found the id
                found_id = False
                if existing_latest_id is None:
                    found_id = True
                latest_id = None
    
                # Loop thru all lines and create Splunk event for new entries (found_id == true)
                for line in lines:
                    # Skip empty lines
                    if len(line.strip()) == 0:
                        continue
                    try:
                        line_data = json.loads(line)
                    except:
                        s_print(" Data in log line can not be parsed as json object.")
                        helper.log_warning("Ionic: Data in log line can not be parsed as json object.")
                        continue

                    # Create an event for each new log entry / Skip existing log entries.
                    if found_id:
                        event = helper.new_event(
                            source=helper.get_input_type(),
                            index=helper.get_output_index(), 
                            sourcetype=helper.get_sourcetype(), 
                            data=line
                        )
                        ew.write_event(event)

                    # Keep track of most recent log entry
                    latest_id = line_data.get("_id", latest_id)
                    # On recurring loops check if we reached the latest existing id
                    if not found_id and existing_latest_id == latest_id:
                        found_id = True
    
                # At this point, found_id should always be "True". If it is "False", then existing_latest_id was saved on a previous run but
                # could not be found in the most recent response. This means all events may be brand new and we should attempt.
                if found_id and r_next_link_url is None:
                    # Set check points for possible recurring loops.
                    if latest_id is None:
                        helper.delete_check_point(key_latest_id)
                    else:
                        helper.save_check_point(key_latest_id, latest_id)
                    helper.save_check_point(key_next_link, url)
                    # No next link, break and wait for new execution.
                    break
                else:
                    existing_latest_id = None
                    helper.delete_check_point(key_latest_id)
                    helper.save_check_point(key_next_link, url)

                if run_in_test_mode and loop_count > opt_test_max_loops:
                    break

            # Delete we are running check point.
            helper.delete_check_point(key_already_running)

        except Exception, e:
            s_print(" Unexpected error happend.")
            helper.log_error("Ionic: Unexpected error happend.")
            helper.delete_check_point(key_already_running)
            raise e

        finally:
            # Delete we are running check point just to be sure.
            helper.log_debug("Ionic: Reached the finally block and need to delete the already running check point.")
            helper.delete_check_point(key_already_running)
