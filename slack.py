# These imports are defined for every callback plugin I've seen so far.
# If you don't import `absolute_import` standard library modules may be
# overriden by Ansible python modules with the same name. For example: I use the
# standard library `json` module, but Ansible has a callback plugin with the
# same name. When I excluded `absolute_import` and imported `json` the json
# module I got was Ansible's json module and not the standard library one.
# I'm not sure why `division` and `print_function` need to be imported.
from __future__ import (absolute_import, division, print_function)
from ansible.plugins.callback import CallbackBase


__metaclass__ = type

import json
import urllib3
import sys
import os
http = urllib3.PoolManager()
# Ansible documentation of the module. I'm also not sure why this is required,
# but other plugins add documentation so it seems to be a standard.
DOCUMENTATION = '''
    callback: slack
    options:
      slack_webhook_url:
        required: True
        env:
          - name: SLACK_WEBHOOK_URL
      slack_channel:
        required: False
        env:
          - name: SLACK_CHANNEL
'''

class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_NAME = 'slack'
    CALLBACK_NEEDS_WHITELIST = True

    def __init__(self):
        super(CallbackModule, self).__init__()
    
    

    def set_options(self, task_keys=None, var_options=None, direct=None):
        super(CallbackModule, self).set_options(task_keys=task_keys, var_options=var_options, direct=direct)

        # Read and assign environment variables to memory so that we can use
        # them later.
        self.slack_webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
        self.slack_channel = os.environ.get('SLACK_CHANNEL')

        if self.slack_webhook_url is None:
            self._display.display('Error: The slack callback plugin requires `SLACK_WEBHOOK_URL` to be defined in the environment')
            sys.exit(1)
    
    def v2_playbook_on_play_start(self, name):
        try:
            self.template_name = self.play.vars['tower_job_template_name']
        except (KeyError, AttributeError):
            pass

        # This block sends information about a playbook when it starts
        # The playbook object is not immediately available at
        # playbook_on_start so we grab it via the play
        if not self.printed_playbook:
            self.playbook_name, _ = os.path.splitext(
                os.path.basename(self.play.playbook.filename))
            host_list = self.play.playbook.inventory.host_list
            inventory = os.path.basename(os.path.realpath(host_list))
            self.printed_playbook = True
            subset = self.play.playbook.inventory._subset
            skip_tags = self.play.playbook.skip_tags
            
    def v2_runner_on_failed(self, taskResult, ignore_errors=False):
        self.notify(self.slack_webhook_url, taskResult, self.slack_channel)

    def v2_runner_on_unreachable(self, taskResult):
        self.notify(self.slack_webhook_url, taskResult, self.slack_channel)
    
    def v2_playbook_on_stats(self, stats):
        """Display info about playbook statistics""" 
        hosts = sorted(stats.processed.keys())
        print ("{:<8} {:<15} {:<10} {:<8} {:<8}".format('Host','Ok','Changed', 'Unreachable', 'Failures'))
       

        failures = False
        unreachable = False

        for h in hosts:
            s = stats.summarize(h)

            if s['failures'] > 0:
                failures = True
            if s['unreachable'] > 0:
                unreachable = True

        self.send_msg("%s: Playbook complete" % self.template_name)

        if failures or unreachable:
            color = 'red'
            self.send_msg("%s: Failures detected" % self.playbook_name)
        else:
            color = 'green'

        #self.send_msg("```%s:\n%s```" % (self.playbook_name, t))


    def notify(slack_webhook_url, taskResult, slack_channel=None):
        # Format the Slack message. We'll use message attachments
        # https://api.slack.com/docs/message-attachments
        payload = {
            'username': 'Ansible',
            'attachments': [
                {
                    'title': 'Ansible run has failed. HOST: {} {}'.format(taskResult._host, taskResult._task),
                    'color': '#FF0000',
                    'text': '```{}```'.format(json.dumps(taskResult._result, indent=2))
                }
            ]
        }

        # The webhook has a default url. If one is not configured, we'll use the
        # default
        if slack_channel:
            payload['channel'] = slack_channel
        encoded_msg = json.dumps(payload).encode('utf-8')
        resp = http.request('POST',slack_webhook_url, body=encoded_msg)
        
        
      
    def send_msg(self, msg, notify=False):
        """Method for sending a message to Slack"""

        params = {}
        params['channel'] = self.slack_webhook_url
        params['username'] = 'Ansible'
        params['text'] = msg
        encoded_msg = json.dumps(params).encode('utf-8')
        resp = http.request('POST',slack_webhook_url, body=encoded_msg)
